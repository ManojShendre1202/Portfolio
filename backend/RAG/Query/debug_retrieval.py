"""
debug_retrieval.py — retrieval debug REPL, isolated from Gemini/DB/WebSocket.

Loads the embedder plus the graph and BM25 index, then lets you type
questions and see retrieve_subgraph's seed-selection + hop-expansion output
(cosine/bm25/fused scores, hop distance) — nothing past that: no
build_context, no Gemini, no WebSocket, no DB, no rate guard. This is the
same retrieval pipeline production uses (see doc_retrieval.py's module
docstring for the reranker's history — tried twice, removed both times) —
this script just stops one step earlier, before build_context, to inspect
raw candidates.

Run from the Portfolio/ directory (or anywhere — this fixes sys.path itself):
    python backend/RAG/Query/debug_retrieval.py
"""
import logging
import os
import sys
from pathlib import Path

# Model files are already cached locally from prior runs — this stops
# sentence_transformers from making HEAD requests to Hugging Face Hub just
# to check cache freshness, which is where the noisy httpx/HEAD log spam
# and the "unauthenticated requests" warning were coming from.
os.environ.setdefault('HF_HUB_OFFLINE', '1')

# Portfolio/ (parent of backend/) — must be on sys.path for `import backend...`
# to resolve regardless of which directory this script is launched from.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Silence the chatty third-party loggers (httpx HEAD requests, huggingface_hub
# warnings) — none of that is useful for this debug session, only our own
# doc_retrieval.* logging is.
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('huggingface_hub').setLevel(logging.WARNING)
logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
logging.getLogger('transformers_modules').setLevel(logging.ERROR)

from backend.RAG.Query import doc_retrieval

DOC_ID = 'python-tutorial'


def main():
    graph, embeddings = doc_retrieval.load_graph(DOC_ID)
    doc_retrieval.get_bm25_index(DOC_ID, graph)

    print()
    print("Retrieval debug REPL (no Gemini). Type a question, or 'quit'.")
    while True:
        question = input('\n> ').strip()
        if not question or question.lower() in ('quit', 'exit'):
            break

        q_norm = doc_retrieval.embed_query(question)
        candidates = doc_retrieval.retrieve_subgraph(
            q_norm, graph, embeddings, question=question, doc_id=DOC_ID,
        )
        print(f"\n--- {len(candidates)} candidates after confidence threshold ---")


if __name__ == '__main__':
    main()
