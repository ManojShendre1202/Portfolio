"""
Standalone Recall@K / MRR eval for the Python-tutorial graph.
Compares: (a) flat cosine-only retrieval, (b) the real retrieve_subgraph
pipeline (keyword seeding + hop expansion + BM25/RRF fusion + confidence
threshold), against a small hand-labeled ground-truth set built by reading
the actual source chapters.

Run: python eval_retrieval.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

import numpy as np
from backend.RAG.Query.doc_retrieval import load_graph, embed_query, retrieve_subgraph

DOC_ID = "python-tutorial"
K = 10

P = "python_tutorial_all_parsed_"
EVAL_SET = [
    {
        "question": "What is the difference between class and instance variables?",
        "relevant": [P + "classes__node_0060", P + "classes__node_0062"],
    },
    {
        "question": "How do generators relate to the iterator protocol?",
        "relevant": [P + "classes__node_0110", P + "classes__node_0120"],
    },
    {
        "question": "What does the yield keyword do inside a generator function?",
        "relevant": [P + "classes__node_0115", P + "classes__node_0119"],
    },
    {
        "question": "Are Python function arguments passed by value or by reference?",
        "relevant": [P + "controlflow__node_0071"],
    },
    {
        "question": "What is a namespace in Python?",
        "relevant": [P + "classes__node_0008"],
    },
    {
        "question": "What is the difference between Python scopes and namespaces?",
        "relevant": [P + "classes__node_0006", P + "classes__node_0007"],
    },
    {
        "question": "What are generator expressions and how are they different from full generators?",
        "relevant": [P + "classes__node_0121"],
    },
    {
        "question": "How do instance objects store their data attributes?",
        "relevant": [P + "classes__node_0048"],
    },
    {
        "question": "What's the idiomatic way to bundle a few named data items together, like a C struct?",
        "relevant": [P + "classes__node_0103"],
    },
]


def eval_query(graph, embeddings, question, relevant_ids, k):
    relevant = set(relevant_ids)
    q_norm = embed_query(question)

    # --- baseline: flat cosine similarity only, no graph/hop/BM25 ---
    normed = embeddings / np.clip(np.linalg.norm(embeddings, axis=1, keepdims=True), 1e-10, None)
    cosine_scores = (normed @ q_norm.T).flatten()
    order = np.argsort(-cosine_scores)
    baseline_ranked_ids = [graph["nodes"][i]["id"] for i in order]

    baseline_topk = set(baseline_ranked_ids[:k])
    baseline_recall = len(baseline_topk & relevant) / len(relevant)
    baseline_rr = next(
        (1.0 / (r + 1) for r, nid in enumerate(baseline_ranked_ids) if nid in relevant), 0.0
    )

    # --- system: full retrieve_subgraph pipeline (seeds + hop + RRF fusion + threshold) ---
    result_nodes = retrieve_subgraph(q_norm, graph, embeddings, question, DOC_ID)
    system_ranked_ids = [n["id"] for n in result_nodes]  # already sorted by fused score
    system_topk = set(system_ranked_ids[:k])
    system_recall = len(system_topk & relevant) / len(relevant)
    system_rr = next(
        (1.0 / (r + 1) for r, nid in enumerate(system_ranked_ids) if nid in relevant), 0.0
    )

    return {
        "baseline_recall": baseline_recall,
        "baseline_rr": baseline_rr,
        "system_recall": system_recall,
        "system_rr": system_rr,
        "system_pool_size": len(system_ranked_ids),
    }


def main():
    graph, embeddings = load_graph(DOC_ID)
    rows = []
    for item in EVAL_SET:
        r = eval_query(graph, embeddings, item["question"], item["relevant"], K)
        rows.append(r)
        print(
            f"{item['question'][:60]:60s} | base_recall={r['baseline_recall']:.2f} "
            f"base_rr={r['baseline_rr']:.2f} | sys_recall={r['system_recall']:.2f} "
            f"sys_rr={r['system_rr']:.2f} pool={r['system_pool_size']}"
        )

    n = len(rows)
    print("\n=== AGGREGATE ===")
    print(f"N questions: {n}")
    print(f"Baseline (flat cosine)  Recall@{K}: {sum(r['baseline_recall'] for r in rows)/n:.3f}   MRR: {sum(r['baseline_rr'] for r in rows)/n:.3f}")
    print(f"System   (graph+hop+RRF) Recall@{K}: {sum(r['system_recall'] for r in rows)/n:.3f}   MRR: {sum(r['system_rr'] for r in rows)/n:.3f}")


if __name__ == "__main__":
    main()
