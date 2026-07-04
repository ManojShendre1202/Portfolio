"""
graph_search.py — Hierarchical cosine similarity search on graph.json

Given a question embedding, searches all node levels (sentence, paragraph,
section, document) and returns the most relevant context to send to Gemini.

Strategy:
- Search sentences for precise matches
- Return matched sentences + their parent paragraph summary for context
- Also return matched section title for broader context
"""

import json
import os

import numpy as np
from django.conf import settings


def _cosine(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def load_graph(job_id: int) -> dict:
    path = os.path.join(settings.MEDIA_ROOT, 'processed', str(job_id), 'graph.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def search(graph: dict, question_embedding: list[float], top_k: int = 5) -> dict:
    """
    Search all node levels for the most relevant context.

    Returns a dict with:
      - matched_sentences: list of {text, page, score}
      - matched_paragraphs: list of {summary, page, score}
      - matched_sections:   list of {title, summary, score}
      - document_summary:   str
    """
    sentences  = graph.get('sentences',  [])
    paragraphs = graph.get('paragraphs', [])
    sections   = graph.get('sections',   [])
    document   = graph.get('document',   {})

    # Score every node at each level
    def top_nodes(nodes, key='text'):
        scored = []
        for node in nodes:
            emb = node.get('embedding')
            if not emb:
                continue
            score = _cosine(question_embedding, emb)
            scored.append((score, node))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    top_sents = top_nodes(sentences)
    top_pars  = top_nodes(paragraphs)
    top_secs  = top_nodes(sections)

    # Build parent lookup maps
    par_by_id  = {p['id']: p for p in paragraphs}
    sec_by_id  = {s['id']: s for s in sections}

    # For each matched sentence, also pull its parent paragraph + section
    seen_pars = set()
    seen_secs = set()
    context_paragraphs = []
    context_sections   = []

    for score, sent in top_sents:
        par_id = sent.get('parent')
        if par_id and par_id not in seen_pars:
            par = par_by_id.get(par_id)
            if par:
                seen_pars.add(par_id)
                context_paragraphs.append({'summary': par['summary'], 'page': par['page'], 'score': score})
                sec_id = par.get('parent')
                if sec_id and sec_id not in seen_secs:
                    sec = sec_by_id.get(sec_id)
                    if sec:
                        seen_secs.add(sec_id)
                        context_sections.append({'title': sec['title'], 'summary': sec['summary'], 'score': score})

    return {
        'matched_sentences':  [{'text': s['text'],     'page': s['page'],    'score': round(sc, 4)} for sc, s in top_sents],
        'matched_paragraphs': context_paragraphs,
        'matched_sections':   context_sections,
        'document_summary':   document.get('summary', ''),
        'document_title':     document.get('title', ''),
    }


def build_context_prompt(search_result: dict, question: str) -> str:
    """
    Formats the search result into a clean context string to send to Gemini.
    """
    lines = []

    lines.append(f"Document: {search_result['document_title']}")
    lines.append(f"Summary: {search_result['document_summary']}")
    lines.append("")

    if search_result['matched_sections']:
        lines.append("Relevant sections:")
        for s in search_result['matched_sections']:
            lines.append(f"  [{s['title']}] {s['summary']}")
        lines.append("")

    if search_result['matched_paragraphs']:
        lines.append("Relevant paragraphs:")
        for p in search_result['matched_paragraphs']:
            lines.append(f"  [Page {p['page']}] {p['summary']}")
        lines.append("")

    if search_result['matched_sentences']:
        lines.append("Most relevant sentences:")
        for s in search_result['matched_sentences']:
            lines.append(f"  [Page {s['page']}] {s['text']}")
        lines.append("")

    lines.append(f"Question: {question}")

    return "\n".join(lines)
