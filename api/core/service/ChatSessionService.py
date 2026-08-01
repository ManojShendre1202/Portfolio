from django.db import transaction

from api.core.models import ChatSession, ChatTurn


class ChatSessionService:

    @staticmethod
    def get_or_create(client_id: str, doc_id: str) -> ChatSession:
        """Resume the current active session for this (client, doc), or
        create the first one if none exists yet."""
        session = (
            ChatSession.objects
            .filter(client_id=client_id, doc_id=doc_id, active=True)
            .order_by('-updated_at')
            .first()
        )
        if session:
            return session
        return ChatSession.objects.create(client_id=client_id, doc_id=doc_id, active=True)

    @staticmethod
    @transaction.atomic
    def start_new(client_id: str, doc_id: str) -> ChatSession:
        """Archive any active session(s) for this (client, doc) and start a
        fresh one — old conversations stay in the DB, just no longer active."""
        ChatSession.objects.filter(client_id=client_id, doc_id=doc_id, active=True).update(active=False)
        return ChatSession.objects.create(client_id=client_id, doc_id=doc_id, active=True)

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
        ChatSession.objects.filter(client_id=client_id, doc_id=doc_id, chat_id=chat_id).delete()

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
