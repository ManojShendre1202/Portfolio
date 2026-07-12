"""embeddings.py — single place for the Gemini embedding model + calls.

Shared by graph building (File_graph.py), semantic search, and entity
search so the model name and batching behavior stay in one spot.
"""

import re
import threading
import time
from collections import deque

EMBED_MODEL = 'gemini-embedding-2'

MAX_EMBED_RETRIES  = 5
DEFAULT_RETRY_WAIT = 20  # seconds, used if the API doesn't tell us a delay

_RETRY_DELAY_RE = re.compile(r"retryDelay['\"]?\s*:\s*['\"]?(\d+)")

# The free-tier embed_content quota counts each TEXT embedded, not each API
# call — a single 100-item batch can burn the entire per-minute budget in
# one shot. build_graph makes several embedding calls back-to-back (nodes,
# candidate entities, merged entities), all sharing this same pool, so we
# proactively pace requests here instead of only reacting to 429s after the
# fact. This is process-local (a threading.Lock + shared window), so it
# also protects a live chat question embedding that happens to land while a
# background build is using the same API key.
EMBED_RPM_LIMIT      = 100
RATE_WINDOW_SECONDS  = 60

_rate_lock    = threading.Lock()
_recent_calls = deque()  # (timestamp, item_count)


def _wait_for_rate_budget(item_count: int) -> None:
    with _rate_lock:
        while True:
            now = time.time()
            while _recent_calls and now - _recent_calls[0][0] > RATE_WINDOW_SECONDS:
                _recent_calls.popleft()

            used = sum(count for _, count in _recent_calls)
            if used + item_count <= EMBED_RPM_LIMIT:
                _recent_calls.append((now, item_count))
                return

            sleep_for = RATE_WINDOW_SECONDS - (now - _recent_calls[0][0]) + 0.1
            time.sleep(max(sleep_for, 0.1))


def _retry_delay_seconds(error: Exception) -> float:
    """Pulls the API's suggested retryDelay out of a 429 error, if present."""
    match = _RETRY_DELAY_RE.search(str(error))
    if match:
        return float(match.group(1))
    return DEFAULT_RETRY_WAIT


def embed_texts(client, texts: list[str]) -> list[list[float]]:
    """
    Embed a batch of texts, returns one vector per input text.

    Paces itself to stay under the per-minute item quota proactively, and
    still retries on 429/quota errors (waiting the delay the API suggests)
    as a safety net for quota shared with other concurrent processes.
    """
    last_error = None
    for attempt in range(MAX_EMBED_RETRIES):
        _wait_for_rate_budget(len(texts))
        try:
            result = client.models.embed_content(
                model=EMBED_MODEL,
                contents=texts,
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
            if '429' not in str(e) and 'quota' not in str(e).lower() and 'RESOURCE_EXHAUSTED' not in str(e):
                raise
            last_error = e
            wait = _retry_delay_seconds(e)
            time.sleep(wait)
    raise RuntimeError(f"embed_content exhausted {MAX_EMBED_RETRIES} retries: {last_error}")


def embed_text(client, text: str) -> list[float]:
    """Embed a single text (e.g. a live user question)."""
    return embed_texts(client, [text])[0]
