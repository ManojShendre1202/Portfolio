"""
doc_retrieval.py — retrieval for curated docs (Python tutorial, etc.),
ported from the tested Readar_dev/RAG/query.py rather than reusing
graph_search.py — that module expects a different, incompatible graph
shape (hierarchical sentences/paragraphs/sections, built by the old
upload pipeline) and no data exists in that shape for these docs.

Everything here — TOP_K/HOP_LIMIT/RERANK_TOP_N, the local nomic embedder,
the cross-encoder reranker — matches the settings already validated across
several stress-testing sessions (see note.md, schema_design.md). The graph
.pkl files were built with these exact embeddings, so retrieval MUST use
the same local model, not the Gemini embed API used elsewhere in this
backend for uploaded documents.
"""

import pickle
from pathlib import Path

import numpy as np
import torch
from django.conf import settings
from sentence_transformers import CrossEncoder, SentenceTransformer

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
}

TOP_K             = 6
HOP_LIMIT         = 2
RERANK_TOP_N      = 15
MAX_CONTEXT_CHARS = 6000

# Loaded once at process start — heavy models, never per-request.
_embedder = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
_reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

_graph_cache: dict[str, tuple[dict, np.ndarray]] = {}


def load_graph(doc_id: str) -> tuple[dict, np.ndarray]:
    if doc_id in _graph_cache:
        return _graph_cache[doc_id]
    path = GRAPH_PATHS[doc_id]
    with open(path, "rb") as f:
        data = pickle.load(f)
    result = (data["graph"], data["embeddings"])
    _graph_cache[doc_id] = result
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


def embed_document(text: str) -> np.ndarray:
    """For embedding things to be searched against later (nomic's asymmetric
    task-prefix scheme — 'document' side, as opposed to embed_query's
    'query' side). Used by session_memory.py to store session summaries."""
    v = _embedder.encode([f"search_document: {text}"])
    return v / np.clip(np.linalg.norm(v), 1e-10, None)


def retrieve_subgraph(q_norm: np.ndarray, graph: dict, embeddings: np.ndarray) -> list[dict]:
    norms  = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normed = embeddings / np.clip(norms, 1e-10, None)
    scores = (normed @ q_norm.T).flatten()

    top_idx = np.argsort(scores)[::-1][:TOP_K]
    nodes   = graph["nodes"]
    adj     = _build_adjacency(graph)

    visited    = set()
    queue      = [(nodes[i]["id"], 0) for i in top_idx]
    result_ids = []

    while queue:
        node_id, hop = queue.pop(0)
        if node_id in visited or hop > HOP_LIMIT:
            continue
        visited.add(node_id)
        result_ids.append(node_id)
        if hop < HOP_LIMIT:
            neighbors = sorted(adj.get(node_id, []), key=lambda x: x[1], reverse=True)
            for neighbor_id, _ in neighbors[:3]:
                if neighbor_id not in visited:
                    queue.append((neighbor_id, hop + 1))

    node_map  = {n["id"]: n for n in nodes}
    score_map = {nodes[i]["id"]: float(scores[i]) for i in range(len(nodes))}
    result    = [node_map[nid] for nid in result_ids if nid in node_map]

    result.sort(key=lambda n: score_map.get(n["id"], 0), reverse=True)
    return result


def rerank_nodes(question: str, nodes: list[dict], top_n: int = RERANK_TOP_N) -> list[dict]:
    if len(nodes) <= top_n:
        return nodes
    pairs  = [(question, n["text"]) for n in nodes]
    scores = _reranker.predict(pairs)
    order  = np.argsort(scores)[::-1][:top_n]
    return [nodes[i] for i in order]


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
    """
    parts     = []
    citations = []
    total     = 0
    n         = 0

    for node in nodes:
        label = _source_label(node)
        entry = f"[{n + 1}] ({label}) {node['text']}"
        if total + len(entry) > MAX_CONTEXT_CHARS:
            break
        n += 1
        parts.append(entry)
        total += len(entry)
        citations.append({
            'n':      n,
            'domIds': node.get('dom_ids', []),
            'chapter': node.get('chapter'),
            'label':  label,
        })

    return "\n\n".join(parts), citations
