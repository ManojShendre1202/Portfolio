"""
entity_search.py — Entity-graph lookup for relationship-tracing questions.

graph_search.search() does top-k semantic similarity: it can miss a
relationship that spans distant pages if the two mentions don't happen to
both land in the top-k for a given question.

This module is deterministic instead: once a question is matched to an
entity (by name mention or embedding similarity), every relationship and
page mention for that entity ANYWHERE in the document is returned — so
"Raju ate chocolate" on page 2 and "Maya gave the chocolate" on page 16
show up together regardless of how far apart they are.
"""

import json
import os

import numpy as np
from django.conf import settings

DEFAULT_TOP_K    = 5
DEFAULT_THRESHOLD = 0.55


def load_entity_graph(job_id: int) -> dict:
    path = os.path.join(settings.MEDIA_ROOT, 'processed', str(job_id), 'entity_graph.json')
    if not os.path.exists(path):
        return {'entities': [], 'relationships': []}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _cosine(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def search_entities(
    entity_graph: dict,
    question: str,
    question_embedding: list[float],
    top_k: int = DEFAULT_TOP_K,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict:
    """
    Find entities relevant to the question, then pull ALL of their
    relationships/mentions from across the whole document (not top-k).

    Returns a dict with:
      - matched_entities:      list of {name, type, pages, score}
      - matched_relationships: list of {subject, relation, object, evidence, page}
    """
    entities      = entity_graph.get('entities', [])
    relationships = entity_graph.get('relationships', [])
    q_lower = question.lower()

    scored = []
    for ent in entities:
        names = [ent['name']] + ent.get('aliases', [])
        name_hit = any(n.lower() in q_lower for n in names if n)

        emb = ent.get('embedding')
        score = _cosine(question_embedding, emb) if emb else 0.0
        if name_hit:
            score = max(score, 1.0)  # exact name mentions always surface

        if name_hit or score >= threshold:
            scored.append((score, ent))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_entities = scored[:top_k]
    matched_ids  = {ent['id'] for _, ent in top_entities}

    matched_relationships = [
        r for r in relationships
        if r.get('subject_id') in matched_ids or r.get('object_id') in matched_ids
    ]
    matched_relationships.sort(key=lambda r: r.get('page', 0))

    return {
        'matched_entities': [
            {
                'name':  e['name'],
                'type':  e.get('type', ''),
                'pages': e.get('pages', []),
                'score': round(sc, 4),
            }
            for sc, e in top_entities
        ],
        'matched_relationships': [
            {
                'subject':  r['subject_name'],
                'relation': r['relation'],
                'object':   r['object_name'],
                'evidence': r.get('evidence', ''),
                'page':     r.get('page'),
            }
            for r in matched_relationships
        ],
    }


def build_entity_context_prompt(entity_result: dict) -> str:
    """Formats the entity search result into a context string for Gemini."""
    lines = []

    if entity_result['matched_entities']:
        lines.append("Relevant entities:")
        for e in entity_result['matched_entities']:
            pages = ', '.join(str(p) for p in e['pages'])
            lines.append(f"  {e['name']} ({e['type']}) — appears on pages {pages}")
        lines.append("")

    if entity_result['matched_relationships']:
        lines.append("Known facts/relationships about these entities across the whole document:")
        for r in entity_result['matched_relationships']:
            lines.append(f"  [Page {r['page']}] {r['subject']} {r['relation']} {r['object']} — \"{r['evidence']}\"")
        lines.append("")

    return "\n".join(lines)
