"""
File_graph.py — Hierarchical Graph RAG builder + entity/relationship graph

Tree structure (semantic graph, good for "what is this document about"):
    Sentences (leaf)
        ↓
    Paragraphs
        ↓
    Sections
        ↓
    Document (root)

Entity graph (good for "how does X relate to Y", including across distant
pages — e.g. page 2 introduces "Raju eating a chocolate", page 16 says
"the chocolate was given by Maya"):
    - Pages are grouped into content-sized batches (see _make_page_batches)
      and each batch is sent to Gemini in ONE call, so coreference within a
      batch ("he" → "Raju") is resolved naturally — the model sees the real
      surrounding text, not just a list of names.
    - Batches are processed concurrently (no rate-limit-driven reason to
      serialize them, and no cross-batch prompt dependency to preserve).
    - A final resolution pass merges near-duplicate entities across
      DIFFERENT batches (e.g. "Maya" in batch 1 vs "the woman" in batch 3)
      using embedding similarity, so relationships end up attached to one
      canonical entity no matter how many different ways it was referred to.

For a 20-page doc split into batches of ~5 pages this costs:
    - ~4 Gemini calls, run concurrently (batches → sentences + paragraphs + entities + relationships)
    - 1  Gemini call   (full doc → sections + document summary)
    - N  embedding calls (one per node + one per distinct entity, batched)

Output:
    media/processed/{job_id}/graph.json         — hierarchical semantic graph
    media/processed/{job_id}/entity_graph.json  — entities + relationships
"""

import json
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from google import genai
from google.genai import types
from django.conf import settings

from backend.RAG.embeddings import embed_texts

logger = logging.getLogger(__name__)

GEMINI_KEY = os.getenv('GEMINI_API_KEY')

# Fallback models if primary hits 429
GRAPH_MODEL_FALLBACKS = [
    # 'gemma-4-31b-it',
    'gemini-3.1-flash-lite',
    'gemini-2.5-flash',
    'gemini-3.1-flash-lite-preview',
]

# Cosine similarity above which two entities are considered the same
# real-world thing during the resolution pass.
ENTITY_MERGE_THRESHOLD = 0.90

# Batching: group pages by content size (chars, a rough token proxy) rather
# than a fixed page count, so a handful of dense pages don't blow up one
# prompt/response while several near-empty pages don't waste round trips.
BATCH_CHAR_BUDGET   = 12000
MAX_PAGES_PER_BATCH = 10
MAX_CONCURRENT_BATCHES = 8

# Retries for a single malformed/truncated JSON response before giving up
# on a model and moving to the next fallback.
MAX_JSON_PARSE_RETRIES = 1


def _gemini_json(client, prompt: str, log) -> dict | list:
    """
    Call Gemini with JSON output, cycling through fallback models on 429,
    and retrying a couple of times on malformed/truncated JSON before
    giving up on that model.
    """
    last_error = None
    for model in GRAPH_MODEL_FALLBACKS:
        for attempt in range(MAX_JSON_PARSE_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json'
                    ),
                )
                return json.loads(response.text)
            except json.JSONDecodeError as e:
                last_error = e
                log(f"Model {model} returned malformed JSON (attempt {attempt + 1}/{MAX_JSON_PARSE_RETRIES + 1}) — retrying")
                continue
            except Exception as e:
                if '429' in str(e) or 'quota' in str(e).lower():
                    log(f"Model {model} quota hit — trying next model")
                    last_error = e
                    break
                raise
    raise RuntimeError(f"All models exhausted: {last_error}")


def _node_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _cosine(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _make_page_batches(pages: list[dict]) -> list[list[dict]]:
    """
    Groups non-empty pages into batches, filling each batch up to
    BATCH_CHAR_BUDGET characters (or MAX_PAGES_PER_BATCH pages, whichever
    comes first) so batch size adapts to how much text each page actually
    has instead of a fixed page count.
    """
    batches: list[list[dict]] = []
    current: list[dict] = []
    current_chars = 0

    for page_data in pages:
        text = page_data['text']
        if not text.strip():
            continue

        would_overflow = current and (
            current_chars + len(text) > BATCH_CHAR_BUDGET
            or len(current) >= MAX_PAGES_PER_BATCH
        )
        if would_overflow:
            batches.append(current)
            current = []
            current_chars = 0

        current.append(page_data)
        current_chars += len(text)

    if current:
        batches.append(current)

    return batches


def _process_batch(client, batch_pages: list[dict], batch_idx: int, log) -> dict:
    """Runs one Gemini call covering multiple pages. Safe to call concurrently."""
    page_nums = [p['page'] for p in batch_pages]
    log(f"Processing batch {batch_idx + 1}: pages {page_nums[0]}-{page_nums[-1]}")

    page_blocks = "\n\n".join(
        f"=== PAGE {p['page']} ===\n{p['text']}" for p in batch_pages
    )

    prompt = f"""
You are analyzing pages {page_nums[0]}-{page_nums[-1]} of a document.

{page_blocks}

Tasks:
1. Extract sentences and group them into logical paragraphs. Each
   paragraph belongs to exactly one page — record that page number.
   IMPORTANT: if the text contains numbered or lettered clauses/sections/
   list items (e.g. "6. Leave", "6.1", "a)", "Article 3"), do NOT merge
   multiple numbered items into one paragraph — each numbered clause or
   list item should generally be its own paragraph, even if that means
   many short paragraphs per page. Only group plain prose sentences
   together when there is no numbering to preserve.
2. Extract entities mentioned across these pages (people, objects,
   organizations, places, etc.). If the same entity is referred to more
   than once in this text — including via pronouns ("he", "she", "it") or
   descriptions ("the boy", "the chocolate") — use ONE consistent name for
   it, and list every page (within this batch) it appears on. Do not list
   the same real-world entity twice under different names.
3. Extract relationships/facts stated in this text as (subject, relation,
   object) triples, using the resolved entity names from step 2. Record
   the page number each relationship was stated on.

If a paragraph starts with a literal numbered/lettered heading (e.g. "6.",
"6.1", "a)", "Article 3"), the summary MUST begin with that exact number
and heading text verbatim (e.g. "6. Leave/Holidays: entitlement to casual
and sick leave"), not a paraphrase that drops the numbering.

Return JSON in exactly this format:
{{
  "paragraphs": [
    {{
      "page": {page_nums[0]},
      "summary": "one sentence summary of this paragraph, starting with the literal clause number/heading if one exists",
      "sentences": [
        {{"text": "exact sentence text", "position": 1}},
        {{"text": "exact sentence text", "position": 2}}
      ]
    }}
  ],
  "entities": [
    {{"name": "Raju", "type": "person", "pages": [{page_nums[0]}]}}
  ],
  "relationships": [
    {{"subject": "Maya", "relation": "gave", "object": "chocolate", "evidence": "Maya gave him the chocolate.", "page": {page_nums[0]}}}
  ]
}}
Only return the JSON, nothing else.
"""
    return _gemini_json(client, prompt, log)


def build_graph(extracted_path: str, job_id: int, log) -> tuple[str, str, list[dict]]:
    """
    Reads extracted_text.json, builds the hierarchical semantic graph and
    the entity/relationship graph, saves both.

    Returns (graph_rel_path, entity_graph_rel_path, suggested_actions).
    """
    client = genai.Client(api_key=GEMINI_KEY)

    # Load extracted text
    full_extracted = os.path.join(settings.MEDIA_ROOT, extracted_path)
    with open(full_extracted, 'r', encoding='utf-8') as f:
        extracted = json.load(f)

    pages       = extracted['pages']
    total_pages = extracted['total_pages']
    log(f"Building graph for {total_pages} pages")

    sentences  = []   # all sentence nodes
    paragraphs = []   # all paragraph nodes

    entity_registry: dict[str, dict] = {}   # norm_name -> {name, type, pages: set}
    raw_relationships: list[dict] = []      # {subject, relation, object, evidence, page}

    # ── Level 1 + 2 + entities/relationships: batched, concurrent Gemini calls ──
    batches = _make_page_batches(pages)
    log(f"Split {total_pages} pages into {len(batches)} batch(es) for extraction")

    batch_results: list[dict | None] = [None] * len(batches)
    max_workers = max(1, min(len(batches), MAX_CONCURRENT_BATCHES))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(_process_batch, client, batch, idx, log): idx
            for idx, batch in enumerate(batches)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            batch_results[idx] = future.result()

    # Merge batch results back in original page order.
    for result in batch_results:
        for par_data in result.get('paragraphs', []):
            par_id   = _node_id('par')
            page_num = par_data.get('page', 0)
            sent_ids = []

            for s in par_data.get('sentences', []):
                sent_id = _node_id('sent')
                sentences.append({
                    'id':       sent_id,
                    'text':     s['text'],
                    'page':     page_num,
                    'position': s.get('position', 0),
                    'parent':   par_id,
                })
                sent_ids.append(sent_id)

            paragraphs.append({
                'id':       par_id,
                'summary':  par_data['summary'],
                'page':     page_num,
                'children': sent_ids,
                'parent':   None,   # filled in section pass
            })

        for ent in result.get('entities', []):
            name = (ent.get('name') or '').strip()
            if not name:
                continue
            norm  = name.lower()
            etype = ent.get('type', 'unknown')
            if norm not in entity_registry:
                entity_registry[norm] = {'name': name, 'type': etype, 'pages': set()}
            entity_registry[norm]['pages'].update(ent.get('pages', []))

        for rel in result.get('relationships', []):
            subject  = (rel.get('subject') or '').strip()
            obj      = (rel.get('object')  or '').strip()
            relation = (rel.get('relation') or '').strip()
            if not subject or not obj or not relation:
                continue
            raw_relationships.append({
                'subject':  subject,
                'relation': relation,
                'object':   obj,
                'evidence': rel.get('evidence', ''),
                'page':     rel.get('page', 0),
            })

    log(f"Extracted {len(sentences)} sentences across {len(paragraphs)} paragraphs")
    log(f"Extracted {len(entity_registry)} candidate entities, {len(raw_relationships)} relationships")

    # ── Level 3 + 4: sections + document summary ─────────────────────────────
    log("Building sections and document summary")

    par_summaries = "\n".join(
        f"[par_id={p['id']} page={p['page']}] {p['summary']}"
        for p in paragraphs
    )

    prompt = f"""
You are analyzing a document with {total_pages} pages.

Below are paragraph summaries with their IDs:
{par_summaries}

Group these paragraphs into logical sections and provide a document summary.
Also suggest 3-6 concrete actions a user could take on this specific
document (e.g. "Extract key deadlines", "Summarize for a non-technical
audience", "List all action items") — base these on what this document
actually contains, not generic suggestions.

Return JSON in exactly this format:
{{
  "document_summary": "2-3 sentence summary of the entire document",
  "document_title": "inferred title or topic",
  "sections": [
    {{
      "title": "section title",
      "summary": "one sentence summary",
      "paragraph_ids": ["par_id1", "par_id2"]
    }}
  ],
  "suggested_actions": [
    {{"title": "short action name", "description": "one sentence on what this action would do"}}
  ]
}}
Only return the JSON, nothing else.
"""
    doc_result = _gemini_json(client, prompt, log)

    suggested_actions = []
    for action in doc_result.get('suggested_actions', []):
        title       = (action.get('title') or '').strip()
        description = (action.get('description') or '').strip()
        if title and description:
            suggested_actions.append({'title': title, 'description': description})

    log(f"Generated {len(suggested_actions)} suggested actions")

    sections = []
    for sec_data in doc_result.get('sections', []):
        sec_id  = _node_id('sec')
        par_ids = sec_data.get('paragraph_ids', [])

        # Link paragraphs back to this section
        for p in paragraphs:
            if p['id'] in par_ids:
                p['parent'] = sec_id

        sections.append({
            'id':       sec_id,
            'title':    sec_data['title'],
            'summary':  sec_data['summary'],
            'children': par_ids,
            'parent':   'doc',
        })

    document = {
        'id':       'doc',
        'title':    doc_result.get('document_title', ''),
        'summary':  doc_result.get('document_summary', ''),
        'children': [s['id'] for s in sections],
    }

    log(f"Built {len(sections)} sections")

    # ── Embeddings: all semantic-graph nodes ──────────────────────────────────
    log("Embedding all nodes")

    all_nodes   = []
    all_texts   = []

    all_nodes.append(('doc', document))
    all_texts.append(f"{document['title']} {document['summary']}")

    for s in sections:
        all_nodes.append(('sec', s))
        all_texts.append(f"{s['title']} {s['summary']}")

    for p in paragraphs:
        all_nodes.append(('par', p))
        all_texts.append(p['summary'])

    for s in sentences:
        all_nodes.append(('sent', s))
        all_texts.append(s['text'])

    # Embed in batches of 100 (API limit)
    BATCH = 100
    all_vectors = []
    for i in range(0, len(all_texts), BATCH):
        batch   = all_texts[i:i + BATCH]
        vectors = embed_texts(client, batch)
        all_vectors.extend(vectors)
        log(f"Embedded {min(i + BATCH, len(all_texts))}/{len(all_texts)} nodes")

    # Attach vectors to nodes
    for i, (_, node) in enumerate(all_nodes):
        node['embedding'] = all_vectors[i]

    # ── Save graph.json ───────────────────────────────────────────────────────
    graph = {
        'document':   document,
        'sections':   sections,
        'paragraphs': paragraphs,
        'sentences':  sentences,
    }

    out_dir  = os.path.join(settings.MEDIA_ROOT, 'processed', str(job_id))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'graph.json')

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    rel_path = os.path.join('processed', str(job_id), 'graph.json')
    log(f"Graph saved — {len(sentences)} sentences, {len(paragraphs)} paragraphs, {len(sections)} sections")

    # ── Entity resolution pass ────────────────────────────────────────────────
    log("Resolving entities")

    candidate_entities = [
        {'name': e['name'], 'type': e['type'], 'pages': sorted(e['pages'])}
        for e in entity_registry.values()
    ]

    if candidate_entities:
        entity_texts = [f"{e['name']} ({e['type']})" for e in candidate_entities]
        entity_vectors = []
        for i in range(0, len(entity_texts), BATCH):
            batch = entity_texts[i:i + BATCH]
            entity_vectors.extend(embed_texts(client, batch))

        merged_entities, norm_name_to_id = _resolve_entities(candidate_entities, entity_vectors)

        # Re-embed the merged, canonical entities so entity_search has a
        # single up-to-date vector per real-world entity.
        merged_texts = [f"{e['name']} ({e['type']})" for e in merged_entities]
        merged_vectors = []
        for i in range(0, len(merged_texts), BATCH):
            batch = merged_texts[i:i + BATCH]
            merged_vectors.extend(embed_texts(client, batch))
        for e, v in zip(merged_entities, merged_vectors):
            e['embedding'] = v
    else:
        merged_entities, norm_name_to_id = [], {}

    log(f"Resolved to {len(merged_entities)} canonical entities")

    # Remap raw relationships onto canonical entity ids
    relationships = []
    for rel in raw_relationships:
        subj_id = norm_name_to_id.get(rel['subject'].strip().lower())
        obj_id  = norm_name_to_id.get(rel['object'].strip().lower())
        if not subj_id or not obj_id:
            continue
        relationships.append({
            'id':           _node_id('rel'),
            'subject_id':   subj_id,
            'subject_name': rel['subject'],
            'relation':     rel['relation'],
            'object_id':    obj_id,
            'object_name':  rel['object'],
            'evidence':     rel['evidence'],
            'page':         rel['page'],
        })

    entity_graph = {
        'entities':      merged_entities,
        'relationships': relationships,
    }

    entity_out_path = os.path.join(out_dir, 'entity_graph.json')
    with open(entity_out_path, 'w', encoding='utf-8') as f:
        json.dump(entity_graph, f, ensure_ascii=False, indent=2)

    entity_rel_path = os.path.join('processed', str(job_id), 'entity_graph.json')
    log(f"Entity graph saved — {len(merged_entities)} entities, {len(relationships)} relationships")

    return rel_path, entity_rel_path, suggested_actions


def _resolve_entities(entities: list[dict], vectors: list[list[float]]) -> tuple[list[dict], dict]:
    """
    Greedy union-find merge of entities whose name+type embeddings are
    near-duplicates (catches cases missed within a batch, or duplicates
    spread across different batches — e.g. "Maya" in batch 1 vs "the woman"
    in batch 3).

    Returns (merged_entities, norm_name_to_canonical_id) where the mapping
    covers every *original* entity name seen, pointing at the id of the
    entity it was merged into.
    """
    n = len(entities)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            if entities[i]['type'] != entities[j]['type']:
                continue
            if _cosine(vectors[i], vectors[j]) >= ENTITY_MERGE_THRESHOLD:
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    merged_entities = []
    norm_name_to_id = {}

    for member_idxs in groups.values():
        members = [entities[i] for i in member_idxs]
        # Canonical = the one with the most page mentions (most established name)
        canonical = max(members, key=lambda e: len(e['pages']))
        ent_id    = _node_id('ent')

        all_pages   = sorted({p for m in members for p in m['pages']})
        all_aliases = sorted({m['name'] for m in members if m['name'] != canonical['name']})

        merged_entities.append({
            'id':      ent_id,
            'name':    canonical['name'],
            'type':    canonical['type'],
            'aliases': all_aliases,
            'pages':   all_pages,
        })

        for m in members:
            norm_name_to_id[m['name'].strip().lower()] = ent_id

    return merged_entities, norm_name_to_id
