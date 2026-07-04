"""
File_graph.py — Hierarchical Graph RAG builder

Tree structure:
    Sentences (leaf)
        ↓
    Paragraphs
        ↓
    Sections
        ↓
    Document (root)

For a 20-page doc this costs:
    - 20 Gemini calls  (one per page  → sentences + paragraphs)
    - 1  Gemini call   (full doc      → sections + document summary)
    - N  embedding calls (one per node, batched)

Output: media/processed/{job_id}/graph.json
"""

import json
import logging
import os
import uuid

from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)

GEMINI_KEY   = os.getenv('GEMINI_API_KEY')
EMBED_MODEL  = 'gemini-embedding-2'
GRAPH_MODEL  = 'gemini-2.5-flash'

# Fallback models if primary hits 429
GRAPH_MODEL_FALLBACKS = [
    'gemini-2.5-flash',
    'gemini-3.1-flash-lite',
    'gemini-3.1-flash-lite-preview',
]


def _gemini_json(client, prompt: str, log) -> dict | list:
    """Call Gemini with JSON output, cycling through fallback models on 429."""
    last_error = None
    for model in GRAPH_MODEL_FALLBACKS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json'
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            if '429' in str(e) or 'quota' in str(e).lower():
                log(f"Model {model} quota hit — trying next")
                last_error = e
                continue
            raise
    raise RuntimeError(f"All models exhausted: {last_error}")


def _embed(client, texts: list[str]) -> list[list[float]]:
    """Embed a list of texts, returns list of vectors."""
    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
    )
    return [e.values for e in result.embeddings]


def _node_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def build_graph(extracted_path: str, job_id: int, log) -> str:
    """
    Reads extracted_text.json, builds hierarchical graph, saves graph.json.
    Returns relative path to graph.json.
    """
    client = genai.Client(api_key=GEMINI_KEY)

    # Load extracted text
    full_extracted = os.path.join(settings.MEDIA_ROOT, extracted_path)
    with open(full_extracted, 'r', encoding='utf-8') as f:
        extracted = json.load(f)

    pages      = extracted['pages']
    total_pages = extracted['total_pages']
    log(f"Building graph for {total_pages} pages")

    sentences  = []   # all sentence nodes
    paragraphs = []   # all paragraph nodes

    # ── Level 1 + 2: per-page Gemini call ────────────────────────────────────
    for page_data in pages:
        page_num = page_data['page']
        text     = page_data['text']

        if not text.strip():
            continue

        log(f"Processing page {page_num}/{total_pages}")

        prompt = f"""
You are analyzing page {page_num} of a document.

PAGE TEXT:
{text}

Extract sentences and group them into logical paragraphs.
Return JSON in exactly this format:
{{
  "paragraphs": [
    {{
      "summary": "one sentence summary of this paragraph",
      "sentences": [
        {{"text": "exact sentence text", "position": 1}},
        {{"text": "exact sentence text", "position": 2}}
      ]
    }}
  ]
}}
Only return the JSON, nothing else.
"""
        result = _gemini_json(client, prompt, log)

        for par_data in result.get('paragraphs', []):
            par_id      = _node_id('par')
            sent_ids    = []

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

    log(f"Extracted {len(sentences)} sentences across {len(paragraphs)} paragraphs")

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
  ]
}}
Only return the JSON, nothing else.
"""
    doc_result = _gemini_json(client, prompt, log)

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

    # ── Embeddings: all nodes ─────────────────────────────────────────────────
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
        vectors = _embed(client, batch)
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

    return rel_path
