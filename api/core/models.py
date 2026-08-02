import uuid

from django.db import models


class ChatSession(models.Model):
    """A resumable chat session for a (client, curated doc) pair.
    See schema_design.md §2/§0 for the full flow this backs.

    A client can have multiple sessions per doc over time (see the
    2026-07-29 "New chat" decision) — at most one is `active` per
    (client_id, doc_id) at a given moment; starting a new chat archives
    the previous one (active=False) rather than deleting it, so old
    conversations stay around. No longer unique on (client_id, doc_id)."""
    client_id         = models.CharField(max_length=64, db_index=True)
    doc_id             = models.CharField(max_length=64, db_index=True)
    chat_id            = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    active             = models.BooleanField(default=True)
    memory_graph_path  = models.CharField(max_length=500, blank=True, default='')
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'readar_chat_sessions'
        indexes = [
            models.Index(fields=['client_id', 'doc_id', 'active']),
        ]


class GeminiUsage(models.Model):
    """One row per calendar date — daily Gemini call/token counts, persisted
    so a dockyard restart mid-day doesn't silently forget usage that already
    happened (the in-memory RateLimiter alone resets to 0 on every restart).
    Old rows are never deleted, so historical daily usage stays queryable."""
    date   = models.DateField(unique=True)
    calls  = models.IntegerField(default=0)
    tokens = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'readar_gemini_usage'


class ChatTurn(models.Model):
    """The UI transcript — distinct from the session's memory-graph .pkl.
    See schema_design.md §1."""
    ROLE_CHOICES = [('user', 'user'), ('ai', 'ai')]

    session    = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='turns')
    role       = models.CharField(max_length=10, choices=ROLE_CHOICES)
    text       = models.TextField()
    bullets    = models.JSONField(default=list, blank=True)
    citations  = models.JSONField(default=list, blank=True)
    trace      = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'readar_chat_turns'
        ordering = ['created_at']
