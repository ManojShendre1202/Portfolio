"""
doc_retrieval.py — retrieval for curated docs (Python tutorial, etc.),
ported from the tested Readar_dev/RAG/query.py rather than reusing
graph_search.py — that module expects a different, incompatible graph
shape (hierarchical sentences/paragraphs/sections, built by the old
upload pipeline) and no data exists in that shape for these docs.

Everything here — HOP_LIMIT, the local nomic embedder — matches the
settings already validated across several stress-testing sessions (see
note.md, schema_design.md). The graph .pkl files were built with these
exact embeddings, so retrieval MUST use the same local model, not the
Gemini embed API used elsewhere in this backend for uploaded documents.

Flow: embed_query -> retrieve_subgraph (seed selection, hop expansion,
confidence threshold — see its docstring) -> build_context.

A cross-encoder reranker (rerank_nodes, cross-encoder/ms-marco-MiniLM-L-6-v2,
capped at 15) was tried twice and removed both times. First removal:
measured across 20 real queries, retrieval-only answered all 20 correctly
with candidate pools then running median ~19-20 nodes, and reranking only
added 1-7s of latency for a reordering that wasn't needed. Second attempt
(after MAX_CONTEXT_CHARS was removed and candidate pools grew past 20-30 on
multi-part questions): tested directly on a real 31-candidate query and it
made things WORSE, not better — ms-marco-MiniLM is trained on short
web-search query/snippet relevance, so it rewarded literal keyword overlap
in navigational filler ("Read more about loading data in PyTorch" scores
well against a DataLoader-related question purely on lexical match) and
dropped a substantively important chunk (the optimizer-registration
explanation) to make room for it, while adding ~2.5s latency. A reranker
tuned for technical-doc relevance rather than search snippets might do
better, but the current model actively hurts precision here — not
reinstating without one.
"""

import logging
import pickle
import re
import time
from pathlib import Path

import numpy as np
import spacy
import torch
from django.conf import settings
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Without this, each inference call spawns its own intra-op BLAS/OMP threads
# (defaults to cpu_count), so concurrent requests already parallelized across
# readar_chat_engine's retrieval_executor end up oversubscribing the same
# handful of real cores several times over. Capping to 1 here means our own
# executor's worker count is the only source of parallelism, which is what
# it was sized for.
torch.set_num_threads(1)

DATA_ROOT = Path(settings.BASE_DIR) / 'documents'

GRAPH_PATHS = {
    'python-tutorial': DATA_ROOT / 'graph_output' / 'python_tutorial_all_parsed.pkl',
    'pytorch':         DATA_ROOT / 'graph_output' / 'pytorch_all_parsed.pkl',
    'opencv':          DATA_ROOT / 'graph_output' / 'opencv_all_parsed.pkl',
    'numpy':           DATA_ROOT / 'graph_output' / 'numpy_all_parsed.pkl',
    'langchain':       DATA_ROOT / 'graph_output' / 'langchain_all_parsed.pkl',
    'langgraph':       DATA_ROOT / 'graph_output' / 'langgraph_all_parsed.pkl',
    'docker':          DATA_ROOT / 'graph_output' / 'docker_all_parsed.pkl',
    'git':             DATA_ROOT / 'graph_output' / 'git_all_parsed.pkl',
    'postgresql':      DATA_ROOT / 'graph_output' / 'postgresql_all_parsed.pkl',
    'chroma':          DATA_ROOT / 'graph_output' / 'chroma_all_parsed.pkl',
}

HOP_LIMIT         = 1

# Relative-cutoff ratio used by retrieve_subgraph's per-cluster confidence
# threshold: a hop-expanded neighbor must score >= this fraction of its own
# cluster's seed score to survive. Relative, not absolute, since fused-score
# scale varies per query and per topic.
RELATIVE_SCORE_RATIO = 0.5

# Safety valve, not a target — caps worst-case seed count (and therefore
# hop-expansion cost) for a pathologically long/dense question. Ordinary
# questions produce far fewer seeds than this on their own.
MAX_KEYPHRASES = 12

# Standard RRF damping constant (Cormack et al.) — large enough that rank 1
# vs rank 2 doesn't swing the fused score wildly, so one list's noisy top
# result can't dominate the fusion on its own.
RRF_K = 60

# Loaded once at process start — heavy models, never per-request.
logger.info('Loading nomic-embed-text-v1.5 (embedder)...')
_t0 = time.perf_counter()
_embedder = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
logger.info('Embedder loaded in %.1fs', time.perf_counter() - _t0)

# Small (~12MB), fast — used only to POS-tag question tokens for n-gram
# candidate filtering in keyword_seed_candidates (see _ngram_spans).
# parser/NER disabled: POS tags alone are enough for this, and skipping
# the dependency parse keeps per-query tagging cheap (a local generative
# LLM was tried for this step instead and pulled back — genuinely better
# phrase grouping, but ~1-1.5s of added latency per query; see
# conversation).
logger.info('Loading en_core_web_sm (spaCy POS tagger)...')
_t0 = time.perf_counter()
_nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
logger.info('spaCy loaded in %.1fs', time.perf_counter() - _t0)

_graph_cache: dict[str, tuple[dict, np.ndarray]] = {}
_bm25_cache: dict[str, BM25Okapi] = {}


# Pure filler words (articles, pronouns, auxiliary "be") — never meaningful
# as a search term regardless of domain, so stripped both from the BM25
# corpus index and from question tokenization/single-word keyphrase
# candidates. Deliberately does NOT include words that are ordinary English
# function words but load-bearing Python keywords/syntax in this domain
# ('with', 'as', 'in', 'for', 'from', 'if', 'except', ...) — an earlier,
# broader version of this list stripped 'with' and silently broke retrieval
# for "with statement" questions; see conversation.
_STOPWORDS = frozenset("""
    a an the and or but is are was were be been being to of this that
    these those it its s does do did doesn don t how what when where
    which who whom why versus vs your you i we they he she them his
    her their our
""".split())


def _tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9_]+", text.lower()) if w not in _STOPWORDS]


def get_bm25_index(doc_id: str, graph: dict) -> BM25Okapi:
    """Sparse-term index over the same node texts as the cosine embeddings —
    built once per doc_id and cached, same pattern as load_graph."""
    if doc_id in _bm25_cache:
        return _bm25_cache[doc_id]

    t0 = time.perf_counter()
    corpus = [_tokenize(n.get("text", "")) for n in graph["nodes"]]
    index = BM25Okapi(corpus)
    _bm25_cache[doc_id] = index
    logger.info(
        'BM25 index built for doc_id=%s: %d nodes in %.2fs (now cached)',
        doc_id, len(corpus), time.perf_counter() - t0,
    )
    return index


# A span survives only if its last word is one of these (a genuine phrase
# almost always ends on its semantic head — a noun or the verb itself),
# OR it's a 2-word ADP/SCONJ+NOUN span ('with statement', 'except clause',
# 'for loop') — common programming-doc jargon that reads as a prepositional
# phrase grammatically but is a real domain concept. This is what lets
# 'with statement' and 'close a file' both survive while 'is that better'/
# 'using the with'/'how do' (ending on AUX/ADP/SCONJ with no such pattern)
# get rejected at generation time instead of relying on embedding-
# similarity scoring alone to filter them out after the fact.
_CONTENT_POS = frozenset({"NOUN", "PROPN", "VERB", "ADJ"})


def _ngram_spans(question: str, max_n: int = 3) -> list[tuple[int, int, str]]:
    """Every 1..max_n word span of the question as (start_word_idx,
    end_word_idx, phrase text), POS-filtered (see _CONTENT_POS) and deduped
    by phrase (first occurrence's span wins).

    Combines spaCy's POS tagger (to know which spans are real content, not
    a hardcoded stopword list) with a blind n-gram window (to still catch
    verb-anchored phrases like 'close a file', which a noun_chunks-only
    parse excludes since it isn't a noun phrase — see conversation). Known
    gap: a boundary-POS rule can't catch every case (e.g. 'try/except',
    where the head-final pattern is reversed) — not fixed here.
    """
    doc = _nlp(question)
    # Strip symbol characters (e.g. the '@' in '@dataclass') rather than
    # rejecting the whole token when it isn't purely alphanumeric — an
    # earlier version used re.fullmatch here, which silently dropped
    # '@dataclass' entirely (spaCy tokenizes it as one token, correctly
    # tagged PROPN, but the raw text '@dataclass' never matched a strict
    # alnum-only regex) so 'dataclass' could never become a candidate at
    # all — not a matching/embedding problem, a token-cleaning one; see
    # conversation.
    words = []
    for tok in doc:
        cleaned = re.sub(r"[^a-z0-9_]", "", tok.text.lower())
        if cleaned:
            words.append((tok, cleaned))

    seen: dict[str, tuple[int, int]] = {}
    for n in range(1, max_n + 1):
        for i in range(len(words) - n + 1):
            span = words[i:i + n]
            first_tok, _ = span[0]
            last_tok, _  = span[-1]
            if n == 1:
                keep = first_tok.pos_ in _CONTENT_POS
            else:
                keep = (last_tok.pos_ in _CONTENT_POS) or (
                    first_tok.pos_ in ("ADP", "SCONJ") and last_tok.pos_ in ("NOUN", "PROPN")
                )
            if not keep:
                continue
            phrase = " ".join(cleaned for _, cleaned in span)
            if phrase not in seen:
                seen[phrase] = (i, i + n - 1)

    return [(start, end, phrase) for phrase, (start, end) in seen.items()]


def keyword_seed_candidates(question: str, graph: dict, embeddings: np.ndarray, doc_id: str) -> list[dict]:
    """Embedding-scored keyphrase extraction, then embedding-scored
    phrase-to-chunk matching — the same "judge by meaning" tool used
    consistently at both steps, rather than switching to bag-of-words BM25
    for the second one (an earlier version did that, and it broke: BM25
    has no concept of phrase adjacency, so a chunk merely containing a
    phrase's words scattered in unrelated sentences could "match" a phrase
    like 'the with statement' even when totally unrelated — see
    conversation).

    1. Generate POS-filtered word spans of the question as candidate
       phrases (_ngram_spans).
    2. Embed the question and all candidates (same local nomic embedder
       used everywhere else in this file — no extra model, no network
       call).
    3. Score each candidate by cosine similarity to the whole question —
       "how central is this phrase to what's being asked."
    4. Greedily keep multi-word candidates highest-similarity-first,
       skipping any that overlaps the word span of an already-kept
       multi-word candidate (so 'floating point' being kept means a
       weaker overlapping 'floating point arithmetic' doesn't also get
       kept as a redundant duplicate). Standalone single-word candidates
       are exempt from this overlap rule and always survive independently
       -- a multi-word phrase can still outscore and get selected first,
       but it no longer silently evicts the single words it contains.
       This matters because a long phrase's own meaning-to-question score
       can be high (it captures more of the sentence) while its own
       corpus match is bad -- the exact wording rarely appears verbatim in
       real text, so hybrid matching (step 5) settles for whatever's
       vaguely nearby. E.g. 'decorators use closures' outscored standalone
       'decorators'/'closures' and evicted both, then matched a PEP8
       style-guide chunk instead of any real decorator content -- with
       standalone words kept, 'decorators' still gets its own chance at a
       correct match even when the glued-together phrase's match fails
       (see conversation). Selection still stops once a candidate's
       similarity falls below RELATIVE_SCORE_RATIO of the top candidate's,
       or once MAX_KEYPHRASES is hit.
    5. Match each surviving phrase to its own best-matching corpus chunk by
       cosine similarity alone -- NOT the hybrid cosine+BM25 fusion
       retrieve_subgraph uses for the whole question. BM25 was tried here
       and measured worse: candidate phrases are already short, clean,
       specific text (not the raw multi-topic question), so cosine alone
       already finds the right chunk for exact-term cases like `KeyError`
       (the case BM25 was originally added for) with no help needed. Where
       BM25 changed the winner at all, it was worse every time tested --
       generic words that happen to appear in many unrelated section
       titles ("statement", "index") won it false exact-term credit over
       genuine semantic relevance, e.g. 'with statement' losing to an
       unrelated 'pass Statements' chunk. See conversation for the
       side-by-side comparison. A phrase is skipped only if its best
       cosine match is <= 0.
    """
    nodes = graph["nodes"]

    spans = _ngram_spans(question)
    if not spans:
        return []

    phrases      = [s[2] for s in spans]
    question_vec = _embedder.encode([question])
    phrase_vecs  = _embedder.encode(phrases)
    q_normed     = question_vec / np.clip(np.linalg.norm(question_vec, axis=1, keepdims=True), 1e-10, None)
    p_normed     = phrase_vecs / np.clip(np.linalg.norm(phrase_vecs, axis=1, keepdims=True), 1e-10, None)
    similarities = (p_normed @ q_normed.T).flatten()

    order      = np.argsort(similarities)[::-1]
    top_sim    = float(similarities[order[0]])
    sim_cutoff = top_sim * RELATIVE_SCORE_RATIO

    selected      = []   # (phrase, similarity, normalized phrase vector)
    used_word_pos = set()
    for idx in order:
        if len(selected) >= MAX_KEYPHRASES:
            break
        sim = float(similarities[idx])
        if sim < sim_cutoff:
            break  # order is descending, so nothing further clears the bar either
        start, end, phrase = spans[idx]
        word_pos = set(range(start, end + 1))
        is_standalone = start == end
        if not is_standalone and (word_pos & used_word_pos):
            continue  # multi-word candidate overlaps a higher-scoring one already kept
        used_word_pos |= word_pos
        selected.append((phrase, sim, p_normed[idx]))

    if not selected:
        return []

    corpus_normed = embeddings / np.clip(np.linalg.norm(embeddings, axis=1, keepdims=True), 1e-10, None)

    results = []
    for phrase, sim, phrase_vec in selected:
        chunk_cosine = (corpus_normed @ phrase_vec.reshape(-1, 1)).flatten()

        best_idx = int(np.argmax(chunk_cosine))
        if chunk_cosine[best_idx] <= 0.0:
            logger.debug('  phrase=%-20s SKIPPED (no signal anywhere in corpus)', phrase)
            continue

        results.append({
            'keyword':    phrase,
            'similarity': sim,
            'node_id':    nodes[best_idx]['id'],
            'cosine':     float(chunk_cosine[best_idx]),
            'text':       nodes[best_idx].get('text', '')[:80],
        })

    unique_nodes = {r['node_id'] for r in results}
    logger.info(
        'keyword_seed_candidates question=%r candidates=%d selected=%d kept=%d unique_nodes=%d',
        question[:120], len(spans), len(selected), len(results), len(unique_nodes),
    )
    for r in results:
        logger.debug(
            '  phrase=%-20s similarity=%.4f cosine=%.4f node_id=%s text=%r',
            r['keyword'], r['similarity'], r['cosine'], r['node_id'], r['text'],
        )

    return results


def load_graph(doc_id: str) -> tuple[dict, np.ndarray]:
    if doc_id in _graph_cache:
        return _graph_cache[doc_id]

    path = GRAPH_PATHS.get(doc_id)
    if path is None:
        logger.error('load_graph: unknown doc_id=%s (no graph path configured)', doc_id)
        raise KeyError(doc_id)

    t0 = time.perf_counter()
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
    except FileNotFoundError:
        logger.error('load_graph: graph .pkl missing on disk for doc_id=%s path=%s', doc_id, path)
        raise
    result = (data["graph"], data["embeddings"])
    _graph_cache[doc_id] = result
    logger.info(
        'Graph loaded for doc_id=%s: %d nodes in %.2fs (now cached)',
        doc_id, len(data["graph"].get("nodes", [])), time.perf_counter() - t0,
    )
    return result


def _build_adjacency(graph: dict) -> dict[str, list[tuple[str, float]]]:
    adj = {n["id"]: [] for n in graph["nodes"]}
    for edge in graph["edges"]:
        adj[edge["source"]].append((edge["target"], edge["weight"]))
        adj[edge["target"]].append((edge["source"], edge["weight"]))
    return adj


def embed_query(question: str) -> np.ndarray:
    q_vec = _embedder.encode([f"search_query: {question}"])
    return q_vec / np.clip(np.linalg.norm(q_vec), 1e-10, None)


def retrieve_subgraph(
    q_norm: np.ndarray, graph: dict, embeddings: np.ndarray, question: str = "", doc_id: str = "",
) -> list[dict]:
    """Multi-source BFS over the document graph: seed selection, hop
    expansion, then a confidence threshold on the expanded candidates.

    Seeds come from keyword_seed_candidates — one guaranteed slot per
    distinct keyword in the question, not a fixed top-N of the fused
    cosine+BM25 ranking below. A single blended whole-question score can
    bury or entirely miss one sub-topic of a multi-part question (e.g.
    `KeyError` got buried under `list`/`dictionary` content when asked
    about in the same sentence); per-keyword seeding guarantees each topic
    a slot instead of leaving coverage to chance.

    Hop-expanded (non-seed) neighbors are then kept only if their fused
    score is >= a fraction (RELATIVE_SCORE_RATIO) of their OWN originating
    seed's score — not one global top score, and never applied to seeds
    themselves. Both of those simplifications were tried first and found,
    via live testing, to let a strong topic's magnitude silently crowd out
    a weaker-but-legitimate topic's seed or its supporting neighbors.
    """
    norms  = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normed = embeddings / np.clip(norms, 1e-10, None)
    cosine_scores = (normed @ q_norm.T).flatten()

    bm25       = get_bm25_index(doc_id, graph)
    bm25_scores = np.asarray(bm25.get_scores(_tokenize(question)))

    # Rank position, not raw score — cosine and BM25 aren't on comparable scales.
    cosine_rank = np.argsort(np.argsort(-cosine_scores))
    bm25_rank   = np.argsort(np.argsort(-bm25_scores))
    fused_scores = 1.0 / (RRF_K + cosine_rank + 1) + 1.0 / (RRF_K + bm25_rank + 1)

    nodes   = graph["nodes"]
    adj     = _build_adjacency(graph)

    node_id_to_idx = {n["id"]: i for i, n in enumerate(nodes)}
    keyword_results = keyword_seed_candidates(question, graph, embeddings, doc_id)
    top_idx = [node_id_to_idx[r["node_id"]] for r in keyword_results if r["node_id"] in node_id_to_idx]
    seed_keyword_map = {r["node_id"]: r["keyword"] for r in keyword_results}  # for readable cluster labels below

    # The actual starting points for the multi-source BFS below — however
    # many keyword-driven seeds came out, chosen before any graph edge is
    # touched.
    logger.info('retrieve_subgraph STARTING NODES (seeds) question=%r seed_count=%d (keyword-driven)',
                 question[:120], len(top_idx))
    for rank, i in enumerate(top_idx, start=1):
        n = nodes[i]
        logger.debug(
            '  seed[%d] fused=%.5f cosine=%.4f bm25=%.4f id=%s text=%r',
            rank, float(fused_scores[i]), float(cosine_scores[i]), float(bm25_scores[i]),
            n["id"], n.get("text", "")[:80],
        )

    visited    = set()
    hop_map    = {}   # node_id -> hop distance from nearest seed, for debug logging below
    origin_map = {}   # node_id -> id of the SEED whose expansion first reached it (its "cluster")
    queue      = [(nodes[i]["id"], 0, nodes[i]["id"]) for i in top_idx]  # (node_id, hop, origin_seed_id)
    result_ids = []

    while queue:
        node_id, hop, origin_id = queue.pop(0)
        if node_id in visited or hop > HOP_LIMIT:
            continue
        visited.add(node_id)
        hop_map[node_id]    = hop
        origin_map[node_id] = origin_id
        result_ids.append(node_id)
        if hop < HOP_LIMIT:
            neighbors = sorted(adj.get(node_id, []), key=lambda x: x[1], reverse=True)
            for neighbor_id, _ in neighbors[:3]:
                if neighbor_id not in visited:
                    queue.append((neighbor_id, hop + 1, origin_id))

    node_map        = {n["id"]: n for n in nodes}
    cosine_score_map = {nodes[i]["id"]: float(cosine_scores[i]) for i in range(len(nodes))}
    bm25_score_map   = {nodes[i]["id"]: float(bm25_scores[i]) for i in range(len(nodes))}
    fused_score_map  = {nodes[i]["id"]: float(fused_scores[i]) for i in range(len(nodes))}
    result          = [node_map[nid] for nid in result_ids if nid in node_map]

    result.sort(key=lambda n: fused_score_map.get(n["id"], 0), reverse=True)

    # Debug visibility into what's actually getting pulled in per query —
    # cosine score, BM25 score, fused rank, hop distance (0 = direct seed,
    # >0 = pulled in via graph-hop expansion only) and chunk char length,
    # to see whether low-relevance or oversized chunks are bloating the
    # context window, and whether BM25 is catching something cosine missed.
    logger.info('retrieve_subgraph question=%r seeds=%d hop_limit=%d candidates=%d',
                 question[:120], len(top_idx), HOP_LIMIT, len(result))
    for rank, node in enumerate(result, start=1):
        origin_id  = origin_map.get(node["id"], node["id"])
        cluster    = seed_keyword_map.get(origin_id, origin_id)
        logger.debug(
            '  [%2d] fused=%.5f cosine=%.4f bm25=%.4f hop=%d cluster=%-12s chars=%d id=%s text=%r',
            rank, fused_score_map.get(node["id"], 0.0), cosine_score_map.get(node["id"], 0.0),
            bm25_score_map.get(node["id"], 0.0), hop_map.get(node["id"], -1), cluster,
            len(node.get("text", "")), node["id"], node.get("text", "")[:80],
        )

    if result:
        thresholded = []
        cluster_cutoffs = {}  # origin_seed_id -> cutoff, for the log line below
        for n in result:
            nid = n["id"]
            if hop_map.get(nid, 0) == 0:
                thresholded.append(n)  # seed — exempt, always kept
                continue
            origin_id     = origin_map.get(nid, nid)
            cluster_score = fused_score_map.get(origin_id, 0.0)
            cutoff        = cluster_score * RELATIVE_SCORE_RATIO
            cluster_cutoffs[origin_id] = cutoff
            if fused_score_map.get(nid, 0.0) >= cutoff:
                thresholded.append(n)

        logger.info(
            'retrieve_subgraph CONFIDENCE THRESHOLD ratio=%.2f (per-cluster, seeds exempt): '
            '%d -> %d candidates',
            RELATIVE_SCORE_RATIO, len(result), len(thresholded),
        )
        for origin_id, cutoff in cluster_cutoffs.items():
            logger.debug(
                '  cluster keyword=%-12s cluster_score=%.5f cutoff=%.5f origin_id=%s',
                seed_keyword_map.get(origin_id, origin_id), fused_score_map.get(origin_id, 0.0),
                cutoff, origin_id,
            )
        result = thresholded

    return result


def _source_label(node: dict) -> str:
    if "spans" in node:
        pages = sorted({s["page"] for s in node["spans"]})
        loc = str(pages[0]) if len(pages) == 1 else f"{pages[0]}-{pages[-1]}"
        return f"Page {loc}"
    if "chapter" in node:
        return f"Chapter {node['chapter']}"
    return "Source"


def build_context(nodes: list[dict]) -> tuple[str, list[dict]]:
    """
    Returns (numbered_context_text, citations) where citations is
    [{n, domIds, chapter, label}] in the same order/numbering used in the
    context text — the prompt asks Gemini to cite using these [n] markers,
    and the frontend uses this same list to make [n] clickable/highlightable.

    Every node retrieve_subgraph's confidence threshold already kept goes into
    context — no separate char budget/cutoff here. That threshold (see
    RELATIVE_SCORE_RATIO) is the actual relevance gate; a second cap on top of
    it was silently dropping already-confidence-passed nodes (confirmed: for a
    3-part question, only 10 of 34 legitimately relevant nodes made it past
    the old 6000-char limit before Gemini ever saw the rest).

    node["code_blocks"] (see ingest.py's merge_code_into_anchor) is
    deliberately excluded from the embedded text but IS appended here —
    the LLM still needs to see a chunk's code to answer with it, even
    though retrieval ranking never saw it.
    """
    parts     = []
    citations = []
    n         = 0

    for node in nodes:
        label = _source_label(node)
        body  = node['text']
        code_blocks = node.get('code_blocks')
        if code_blocks:
            body = body + "\n\n" + "\n\n".join(code_blocks)
        n += 1
        parts.append(f"[{n}] ({label}) {body}")
        citations.append({
            'n':      n,
            'domIds': node.get('dom_ids', []),
            'chapter': node.get('chapter'),
            'label':  label,
        })

    return "\n\n".join(parts), citations
