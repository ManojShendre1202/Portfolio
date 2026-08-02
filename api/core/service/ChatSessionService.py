import logging
import random

from django.db import transaction
from django.utils import timezone

from api.core.models import ChatSession, ChatTurn

logger = logging.getLogger(__name__)

# No login means client_id is just a cookie, not a real identity — so we
# don't keep sessions around indefinitely. A week matches the cookie's
# own expiry (views.CLIENT_ID_MAX_AGE); after that a visitor is simply
# treated as new, which is fine for an interview-demo flow. ChatTurn rows
# cascade-delete with their session (see models.py's on_delete=CASCADE).
SESSION_RETENTION_SECONDS = 60 * 60 * 24 * 7

# Purging on every call would mean a DELETE scan on every single request
# for very little benefit at this traffic scale; run it opportunistically
# instead (same trick Django's own clearsessions-adjacent code uses).
_PURGE_PROBABILITY = 0.01


class ChatSessionService:

    @staticmethod
    def purge_expired() -> int:
        from backend.RAG.Query import session_memory  # local import — avoids loading embed models at module import time

        cutoff = timezone.now() - timezone.timedelta(seconds=SESSION_RETENTION_SECONDS)
        expired_ids = list(ChatSession.objects.filter(updated_at__lt=cutoff).values_list('chat_id', flat=True))
        if not expired_ids:
            return 0

        deleted, _ = ChatSession.objects.filter(chat_id__in=expired_ids).delete()
        for chat_id in expired_ids:
            session_memory.delete(chat_id)
        logger.info('Purged %d expired session(s)', deleted)
        return deleted

    @staticmethod
    def get_or_create(client_id: str, doc_id: str) -> ChatSession:
        """Resume the current active session for this (client, doc), or
        create the first one if none exists yet."""
        if random.random() < _PURGE_PROBABILITY:
            ChatSessionService.purge_expired()

        session = (
            ChatSession.objects
            .filter(client_id=client_id, doc_id=doc_id, active=True)
            .order_by('-updated_at')
            .first()
        )
        if session:
            return session
        session = ChatSession.objects.create(client_id=client_id, doc_id=doc_id, active=True)
        logger.info('New session created: chat_id=%s doc_id=%s', session.chat_id, doc_id)
        return session

    @staticmethod
    @transaction.atomic
    def start_new(client_id: str, doc_id: str) -> ChatSession:
        """Archive any active session(s) for this (client, doc) and start a
        fresh one — old conversations stay in the DB, just no longer active."""
        ChatSession.objects.filter(client_id=client_id, doc_id=doc_id, active=True).update(active=False)
        session = ChatSession.objects.create(client_id=client_id, doc_id=doc_id, active=True)
        logger.info('Session archived, new one started: chat_id=%s doc_id=%s', session.chat_id, doc_id)
        return session

    @staticmethod
    def get_by_chat_id(chat_id) -> ChatSession:
        return ChatSession.objects.get(chat_id=chat_id)

    @staticmethod
    def get_turns(chat_id) -> list[ChatTurn]:
        return list(
            ChatSession.objects.get(chat_id=chat_id).turns.all()
        )

    @staticmethod
    def add_turn(chat_id, role: str, text: str, bullets=None, citations=None, trace=None) -> ChatTurn:
        session = ChatSession.objects.get(chat_id=chat_id)
        turn = ChatTurn.objects.create(
            session=session,
            role=role,
            text=text,
            bullets=bullets or [],
            citations=citations or [],
            trace=trace,
        )
        session.save(update_fields=['updated_at'])  # bump via auto_now
        return turn

    @staticmethod
    def set_active(chat_id, active: bool) -> None:
        ChatSession.objects.filter(chat_id=chat_id).update(active=active)

    @staticmethod
    def list_sessions(client_id: str, doc_id: str) -> list[ChatSession]:
        """All sessions (active + archived) for this (client, doc), newest first —
        each with its turn count and first user question for display."""
        return list(
            ChatSession.objects
            .filter(client_id=client_id, doc_id=doc_id)
            .order_by('-updated_at')
            .prefetch_related('turns')
        )

    @staticmethod
    def delete_session(client_id: str, doc_id: str, chat_id) -> None:
        """Permanently removes a session and its turns. If it was the active
        session, the next getOrCreateSession call for this (client, doc)
        will simply start a fresh one — no session is left dangling."""
        from backend.RAG.Query import session_memory  # local import — avoids loading embed models at module import time

        ChatSession.objects.filter(client_id=client_id, doc_id=doc_id, chat_id=chat_id).delete()
        session_memory.delete(chat_id)
        logger.info('Session deleted: chat_id=%s doc_id=%s', chat_id, doc_id)

    @staticmethod
    @transaction.atomic
    def switch_to(client_id: str, doc_id: str, chat_id) -> ChatSession:
        """Make an archived session the active one again — archives whatever
        is currently active for this (client, doc) first."""
        ChatSession.objects.filter(client_id=client_id, doc_id=doc_id, active=True).update(active=False)
        session = ChatSession.objects.get(chat_id=chat_id, client_id=client_id, doc_id=doc_id)
        session.active = True
        session.save(update_fields=['active'])
        return session
