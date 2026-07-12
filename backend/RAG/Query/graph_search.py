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


# Phrases that signal the question wants EVERY match, not just the closest
# few — top-k similarity search can never answer these correctly by
# construction, since it only ever returns the closest handful.
_ENUMERATION_PHRASES = (
    'list all', 'list every', 'list each',
    'how many', 'count of', 'total number',
    'enumerate', 'all of the', 'every single',
    'complete list',
)


def is_enumeration_question(question: str) -> bool:
    """Detects list-all / count-all style questions that need full-section
    coverage instead of top-k similarity search."""
    q = question.lower()
    return any(phrase in q for phrase in _ENUMERATION_PHRASES)


def search_full_sections(graph: dict, question_embedding: list[float], top_k_sections: int | None = None) -> dict:
    """
    For enumeration/listing questions: returns EVERY paragraph in the
    document (not just the top-k closest), so the model has full coverage
    to list or count from. Capping by section similarity would defeat the
    point of a "list all X in this document" question, so by default this
    includes every section — pass top_k_sections to narrow scope only when
    the question is clearly about one part of a large document.
    """
    sections   = graph.get('sections',   [])
    paragraphs = graph.get('paragraphs', [])
    document   = graph.get('document',   {})

    scored = []
    for sec in sections:
        emb = sec.get('embedding')
        if not emb:
            continue
        scored.append((_cosine(question_embedding, emb), sec))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_secs = scored if top_k_sections is None else scored[:top_k_sections]

    full_paragraphs = []
    for _, sec in top_secs:
        children = set(sec.get('children', []))
        for p in paragraphs:
            if p['id'] in children:
                full_paragraphs.append({'summary': p['summary'], 'page': p['page']})

    return {
        'document_title':   document.get('title', ''),
        'document_summary': document.get('summary', ''),
        'sections':         [{'title': s['title'], 'summary': s['summary']} for _, s in top_secs],
        'full_paragraphs':  full_paragraphs,
    }


def build_full_section_prompt(result: dict) -> str:
    """Formats a search_full_sections() result into a context string."""
    lines = []

    lines.append(f"Document: {result['document_title']}")
    lines.append(f"Summary: {result['document_summary']}")
    lines.append("")

    if result['sections']:
        lines.append("Matched section(s) — FULL content included below so you can list/count exhaustively:")
        for s in result['sections']:
            lines.append(f"  [{s['title']}] {s['summary']}")
        lines.append("")

    if result['full_paragraphs']:
        lines.append("Every paragraph in the matched section(s):")
        for p in result['full_paragraphs']:
            lines.append(f"  [Page {p['page']}] {p['summary']}")
        lines.append("")

    return "\n".join(lines)


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


def build_context_prompt(search_result: dict) -> str:
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

    return "\n".join(lines)
