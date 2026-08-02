"""Cross-process live stats handoff.

chat_ws_server.py and gemini_rate_guard.py's singleton both live in the
dockyard process — the admin page is served by the separate django process
(different container). There's no shared memory between them, so dockyard
writes its live numbers to a small JSON file on the media_data volume both
containers already mount, and django's admin view just reads it back.
"""

import json
import time
from pathlib import Path

from django.conf import settings

STATS_PATH = Path(settings.MEDIA_ROOT) / 'live_stats.json'


def write_stats(ws_connections: int, rate_limiter=None) -> None:
    data = {
        'ws_connections': ws_connections,
        'updated_at': time.time(),
    }
    if rate_limiter is not None:
        data['gemini'] = {
            'rpm': len(rate_limiter.minute_calls),
            'rpm_limit': 100,
            'tpm': sum(t for _, t in rate_limiter.minute_tokens),
            'tpm_limit': 30_000,
            'rpd': rate_limiter.calls_today,
            'rpd_limit': 1_000,
            'tokens_today': rate_limiter.tokens_today,
        }
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
