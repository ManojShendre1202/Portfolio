from backend.RAG.File_processing_worker import run as fileprocessing

# ── Queues ────────────────────────────────────────────────────────────────────
QUEUES: list[str] = [
    'DOCUMENT_PREPROCESSOR',
]

QUEUE_CONCURRENCY: dict[str, int] = {
    'DOCUMENT_PREPROCESSOR': 1,
}

# ── Pipeline ──────────────────────────────────────────────────────────────────
PIPELINE: dict[str, dict] = {
    'File_processing': {
        'queue': 'DOCUMENT_PREPROCESSOR',
        'fn':    fileprocessing,
        # 'next':  'Document  ',
    },
}

# ── Entry point ───────────────────────────────────────────────────────────────
ENTRY_STAGE: str = 'File_processing'
