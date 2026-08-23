import logging
import os
import sys
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
# httpx (used by huggingface_hub's connectivity checks when loading the local
# embedder model) logs every request at INFO — noisy, not useful here.
logging.getLogger('httpx').setLevel(logging.WARNING)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

logger = logging.getLogger(__name__)

# Supabase free-tier projects pause after a stretch of zero DB activity.
# A trivial query every few hours keeps the project awake without costing
# anything meaningful — each ping opens a fresh connection and closes it
# right after, so it doesn't hold an idle connection open against the pooler.
DB_KEEPALIVE_INTERVAL_SECONDS = 5 * 60 * 60  # 5 hours


def _db_keepalive_loop(interval_seconds: int = DB_KEEPALIVE_INTERVAL_SECONDS) -> None:
    from django.db import close_old_connections, connection

    while True:
        time.sleep(interval_seconds)
        try:
            close_old_connections()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            logger.info("DB keepalive ping sent")
        except Exception:
            logger.exception("DB keepalive ping failed")
        finally:
            connection.close()


def main() -> None:
    import django
    django.setup()

    from backend.RAG.Query.gemini_rate_guard import hydrate_from_db
    from workflow.engine.ws.chat_ws_server import start_chat_ws_server

    logger.info("Dockyard starting up")
    hydrate_from_db()

    chat_ws_thread = threading.Thread(
        target=start_chat_ws_server,
        name="ChatWebSocketServer",
        daemon=True,
    )
    chat_ws_thread.start()
    logger.info("Chat WebSocket server thread started")

    db_keepalive_thread = threading.Thread(
        target=_db_keepalive_loop,
        name="DBKeepAlive",
        daemon=True,
    )
    db_keepalive_thread.start()
    logger.info("DB keep-alive thread started (pings every 5h)")

    logger.info("Dockyard ready")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Dockyard shutting down")


if __name__ == "__main__":
    main()
