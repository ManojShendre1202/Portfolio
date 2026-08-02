"""
session_memory.py — per-session conversation memory, retrieval-augmented
rather than raw-history-resent. See schema_design.md §1a/§0 for the design.

Each session gets its own small .pkl (one embedded node per turn — the
Gemini-generated hidden summary, NOT the raw full answer text, per the
2026-07-29 decision to keep memory nodes cheap to store/retrieve). On each
new question, only the few most-relevant prior turns are pulled in — cost
stays roughly flat regardless of session length, unlike resending full
history every turn.
"""

import os
import pickle
from pathlib import Path

import numpy as np
from django.conf import settings

from backend.RAG.Query.doc_retrieval import embed_document

MEMORY_DIR = Path(settings.BASE_DIR) / 'media' / 'sessions'
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

TOP_K = 3


def _path(chat_id) -> Path:
    return MEMORY_DIR / f"{chat_id}.pkl"


def load(chat_id) -> tuple[list[dict], np.ndarray]:
    path = _path(chat_id)
    if not path.exists():
        return [], np.empty((0, 0))
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data["nodes"], data["embeddings"]


def delete(chat_id) -> None:
    """Best-effort — called when a ChatSession row is deleted/purged so its
    memory file doesn't outlive the session it belongs to."""
    _path(chat_id).unlink(missing_ok=True)


def save(chat_id, nodes: list[dict], embeddings: np.ndarray) -> str:
    """Writes via a temp file + atomic rename so a crash mid-write can't
    leave a truncated/corrupt .pkl behind — the old file (or none) stays
    readable until the new one is fully written."""
    path = _path(chat_id)
    tmp_path = path.with_suffix(path.suffix + f'.tmp{os.getpid()}')
    with open(tmp_path, "wb") as f:
        pickle.dump({"nodes": nodes, "embeddings": embeddings}, f)
    os.replace(tmp_path, path)
    return str(path)


def retrieve(chat_id, q_norm: np.ndarray, top_k: int = TOP_K) -> list[dict]:
    """Returns the top-k most relevant prior turns (by summary similarity
    to the current question), or [] if this session has no memory yet."""
    nodes, embeddings = load(chat_id)
    if not nodes:
        return []

    norms  = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normed = embeddings / np.clip(norms, 1e-10, None)
    scores = (normed @ q_norm.T).flatten()

    top_idx = np.argsort(scores)[::-1][:top_k]
    return [nodes[i] for i in top_idx]


def append_turn(chat_id, question: str, summary: str) -> str:
    """Embeds and stores this turn's hidden summary. Blocking (local model
    inference) — call via asyncio.to_thread, and fire-and-forget from the
    caller's perspective (background task, doesn't block the response)."""
    nodes, embeddings = load(chat_id)

    new_vec = embed_document(summary)
    new_node = {"question": question, "summary": summary}

    if embeddings.size == 0:
        embeddings = new_vec
    else:
        embeddings = np.vstack([embeddings, new_vec])
    nodes.append(new_node)

    return save(chat_id, nodes, embeddings)


def build_memory_prompt(memory_turns: list[dict]) -> str:
    if not memory_turns:
        return ""
    lines = ["Relevant prior exchanges in this conversation (for context only):"]
    for t in memory_turns:
        lines.append(f"  - Q: {t['question']}  →  {t['summary']}")
    lines.append("")
    return "\n".join(lines)
