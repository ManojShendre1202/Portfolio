"""Cross-process live stats handoff.

chat_ws_server.py and readar_chat_engine.py (which owns the Gemini calls)
both live in the dockyard process, sharing this module's memory directly —
the admin page, though, is served by the separate django process (different
container). There's no shared memory between the two containers, so this
module also writes its numbers out to a small JSON file on the media_data
volume both containers already mount, and django's admin view just reads
that file back.

ws_connections and the latency window are updated independently of each
other (a connection can open/close without a Gemini call happening in the
same instant, and vice versa) — each write re-flushes the full current
state, not just whatever changed, so the file is never half-stale.
"""

import json
import time
from collections import deque
from pathlib import Path
from threading import Lock

from django.conf import settings

STATS_PATH = Path(settings.MEDIA_ROOT) / 'live_stats.json'

# Last N completed calls' timing — enough to show "is it slow right now"
# without keeping unbounded history in memory.
_LATENCY_WINDOW = 20

_lock            = Lock()
_ws_connections  = 0
_recent_latencies: deque[dict] = deque(maxlen=_LATENCY_WINDOW)


def connection_opened() -> None:
    global _ws_connections
    with _lock:
        _ws_connections += 1
    _flush()


def connection_closed() -> None:
    global _ws_connections
    with _lock:
        _ws_connections = max(0, _ws_connections - 1)
    _flush()


def record_call(retrieve_sec: float, gemini_sec: float, total_sec: float) -> None:
    """Call once per completed Gemini answer — this is what keeps the
    latency window and Gemini RPM/RPD numbers live between WS connect/
    disconnect events, which used to be the only thing that flushed."""
    with _lock:
        _recent_latencies.append({
            'retrieve': round(retrieve_sec, 2),
            'gemini':   round(gemini_sec, 2),
            'total':    round(total_sec, 2),
            'at':       time.time(),
        })
    _flush()


def _flush() -> None:
    from backend.RAG.Query.gemini_rate_guard import chat_rate_limiter

    with _lock:
        connections = _ws_connections
        latencies   = list(_recent_latencies)

    data = {
        'ws_connections': connections,
        'updated_at': time.time(),
        'gemini': {
            'rpm': len(chat_rate_limiter.minute_calls),
            'rpm_limit': 100,
            'tpm': sum(t for _, t in chat_rate_limiter.minute_tokens),
            'tpm_limit': 30_000,
            'rpd': chat_rate_limiter.calls_today,
            'rpd_limit': 1_000,
            'tokens_today': chat_rate_limiter.tokens_today,
        },
        'recent_calls': latencies,
    }
    if latencies:
        totals = [c['total'] for c in latencies]
        data['avg_latency_sec'] = round(sum(totals) / len(totals), 2)
        data['last_latency_sec'] = totals[-1]

    try:
        STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATS_PATH.write_text(json.dumps(data))
    except OSError:
        pass


def read_stats() -> dict:
    try:
        return json.loads(STATS_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
