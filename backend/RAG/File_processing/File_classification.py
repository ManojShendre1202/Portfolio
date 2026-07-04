import json
import logging
import os

import fitz  # PyMuPDF

from django.conf import settings

logger = logging.getLogger(__name__)


def classify_and_extract(rel_path: str, file_type: str, job_id: int, log) -> str:
    """
    Detects whether PDF is text-based or scanned, extracts text page by page,
    saves to media/processed/{job_id}/extracted_text.json.

    Returns the output file path relative to MEDIA_ROOT.
    """
    full_path = os.path.join(settings.MEDIA_ROOT, rel_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"File not found: {full_path}")

    if 'pdf' not in file_type.lower():
        raise ValueError(f"Unsupported file type for now: {file_type}")

    log("Opening PDF...")
    doc        = fitz.open(full_path)
    page_count = len(doc)
    log(f"Pages: {page_count}")

    sample_text = doc[0].get_text().strip()

    if len(sample_text) > 50:
        log("Text-based PDF — extracting text")
        pages = []
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            pages.append({"page": i + 1, "text": text})
        log(f"Extracted {page_count} pages")
    else:
        log("Scanned PDF detected — OCR required (not implemented yet)")
        doc.close()
        return ""

    doc.close()

    # Save to media/processed/{job_id}/extracted_text.json
    out_dir = os.path.join(settings.MEDIA_ROOT, 'processed', str(job_id))
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, 'extracted_text.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({"total_pages": page_count, "pages": pages}, f, ensure_ascii=False, indent=2)

    rel_out = os.path.join('processed', str(job_id), 'extracted_text.json')
    log(f"Saved to {rel_out}")

    return rel_out
