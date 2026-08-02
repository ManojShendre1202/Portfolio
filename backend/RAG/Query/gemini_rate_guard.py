"""
gemini_rate_guard.py — proactive RPM/TPM/RPD/TPD guard for Gemini chat generation.

Guards generate_content_stream calls specifically (a separate quota pool from
Gemini's embed_content API, which this project doesn't use anyway — retrieval
here runs on the local nomic embedder, not a Gemini embedding call). Ported
from the tested RateLimiter in Readar_dev/RAG/query.py,
but upgraded from record-only to a pre-call guard: handle_question checks
can_proceed() BEFORE calling Gemini, so a call we already know will 429
never goes out — the interviewer sees an instant, friendly "busy" message
instead of a multi-second timeout/error round-trip.

Thread-safe (threading.Lock) since generation runs in a worker thread
(see readar_chat_engine.py's use of asyncio.to_thread / run_in_executor) and
this is a single process-wide singleton shared across all concurrent chat
connections.

NOTE: RPM=100 / TPM=30000 / RPD=1000 match the free-tier figures already
validated in the Readar_dev session logs for gemini-3.1-flash-lite. TPD
(tokens per day) is NOT a figure that session ever measured — verify the
actual per-day token cap in the Gemini API console before relying on it;
until then this is a conservative placeholder, not a confirmed quota.
"""

import logging
import threading
import time
from collections import deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

RPM_LIMIT = 100
TPM_LIMIT = 30_000
RPD_LIMIT = 1_000
TPD_LIMIT = 1_000_000  # placeholder — verify real per-day token cap, see note above

# Leave headroom so the guard trips before the real API limit, not exactly at it —
# avoids a race where several proactive checks pass right before a shared limit trips.
SAFETY_MARGIN = 0.9


class RateLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        self.calls_today  = 0
        self.tokens_today = 0
        self.minute_calls  = deque()   # timestamps
        self.minute_tokens = deque()   # (timestamp, tokens)
        self.day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    def _reset_if_new_day(self):
        now = datetime.now()
        if now >= self.day_start + timedelta(days=1):
            self.calls_today  = 0
            self.tokens_today = 0
            self.day_start    = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def _clean_minute_window(self):
        cutoff = time.time() - 60
        while self.minute_calls and self.minute_calls[0] < cutoff:
            self.minute_calls.popleft()
        while self.minute_tokens and self.minute_tokens[0][0] < cutoff:
            self.minute_tokens.popleft()

    def can_proceed(self, estimated_tokens: int) -> tuple[bool, str | None]:
        """
        Pre-call guard. Returns (True, None) if it's safe to call Gemini now,
        or (False, reason) if a limit would be breached — caller should skip
        the API call entirely and show a friendly message instead.
        """
        with self._lock:
            self._reset_if_new_day()
            self._clean_minute_window()

            if len(self.minute_calls) + 1 > RPM_LIMIT * SAFETY_MARGIN:
                return False, 'rpm out of limit'
            projected_tpm = sum(t for _, t in self.minute_tokens) + estimated_tokens
            if projected_tpm > TPM_LIMIT * SAFETY_MARGIN:
                return False, 'tpm'
            if self.calls_today + 1 > RPD_LIMIT * SAFETY_MARGIN:
                return False, 'rpd'
            if self.tokens_today + estimated_tokens > TPD_LIMIT * SAFETY_MARGIN:
                return False, 'tpd'
            return True, None

    def record(self, token_count: int) -> None:
        with self._lock:
            self._reset_if_new_day()
            self._clean_minute_window()
            now = time.time()
            self.calls_today  += 1
            self.tokens_today += token_count
            self.minute_calls.append(now)
            self.minute_tokens.append((now, token_count))

    def summary(self) -> str:
        with self._lock:
            self._reset_if_new_day()
            self._clean_minute_window()
            rpm = len(self.minute_calls)
            tpm = sum(t for _, t in self.minute_tokens)
            return (
                f"RPM: {rpm}/{RPM_LIMIT}  |  TPM: {tpm}/{TPM_LIMIT}  |  "
                f"RPD: {self.calls_today}/{RPD_LIMIT}  |  Tokens today: {self.tokens_today}"
            )


# Module-level singleton — one process-wide budget shared across all
# concurrent chat connections, since the Gemini API key's limits are
# account-wide, not per-connection.
chat_rate_limiter = RateLimiter()


def hydrate_from_db() -> None:
    """Load today's persisted calls/tokens into the in-memory limiter.
    Call once at dockyard startup (after django.setup()) — without this,
    a restart mid-day would reset the guard's (and the admin dashboard's)
    idea of 'calls today' back to zero, even though GeminiUsage still has
    the real count from before the restart."""
    from datetime import date
    from api.core.models import GeminiUsage

    row = GeminiUsage.objects.filter(date=date.today()).first()
    if row:
        with chat_rate_limiter._lock:
            chat_rate_limiter.calls_today  = row.calls
            chat_rate_limiter.tokens_today = row.tokens
        logger.info('Hydrated Gemini usage from DB: %d calls, %d tokens today', row.calls, row.tokens)
    else:
        logger.info('No persisted Gemini usage for today yet — starting at 0')


def persist_usage(calls_delta: int, tokens_delta: int) -> None:
    """Adds this call's usage to today's DB row (creating it if this is the
    first call today). Call after every successful chat_rate_limiter.record()
    — see hydrate_from_db for why this needs to survive process restarts."""
    from datetime import date
    from django.db.models import F
    from api.core.models import GeminiUsage

    today = date.today()
    obj, _ = GeminiUsage.objects.get_or_create(date=today)
    GeminiUsage.objects.filter(pk=obj.pk).update(
        calls=F('calls') + calls_delta,
        tokens=F('tokens') + tokens_delta,
    )


GUARD_MESSAGES = {
    'rpm': "Readar is getting more love than the free tier expected. Give it about 10 seconds and try again.",
    'tpm': "The free tier is doing its best. Give it about 10 seconds and try again.",
    'rpd': "The budget has entered its 'that's enough for today' era. Please try again tomorrow, or feel free to reach out directly.",
    'tpd': "The free-tier accountant has closed the books for today. Please try again tomorrow, or feel free to reach out directly.",
}

GENERIC_ERROR_MESSAGE = "Something went wrong answering that — please try rephrasing your question or try again in a moment."
