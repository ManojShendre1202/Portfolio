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
# embedder/reranker models) logs every request at INFO — noisy, not useful here.
logging.getLogger('httpx').setLevel(logging.WARNING)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

logger = logging.getLogger(__name__)


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

    logger.info("Dockyard ready")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Dockyard shutting down")


if __name__ == "__main__":
    main()
