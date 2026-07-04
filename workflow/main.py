"""
Dockyard processor entry point.

Wires scripts (pipeline config + executor functions) into the engine and
starts all three permanent threads:
    Thread A - TCP signal listener (signal_listener.py)
    Thread B - Dispatcher loop     (dispatcher.py)
    Thread C - WebSocket server    (ws_server.py)

Usage:
    cd backend
    python -m dockyard.main
"""

import logging
import os
import sys
import threading
import time
from multiprocessing import Manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from workflow.engine.dispatcher import Dispatcher
from workflow.engine.queues.registry import registry
from workflow.engine.recovery import run_recovery
from workflow.engine.signal_listener import start_signal_listener
from workflow.engine.ws.ws_broadcaster import broadcaster
from workflow.engine.ws.ws_server import start_ws_server
from workflow.engine.ws.chat_ws_server import start_chat_ws_server
from workflow.pipeline_config import ENTRY_STAGE, PIPELINE, QUEUE_CONCURRENCY, QUEUES

logger = logging.getLogger(__name__)


def _queue_forwarder(update_queue) -> None:
    """
    Thread D — reads (revision_id, stage_name, text) tuples from the
    multiprocessing.Queue and forwards them to the broadcaster.
    Needed because ProcessPoolExecutor workers are separate processes and
    cannot access the broadcaster's memory directly.
    """
    while True:
        try:
            revision_id, stage_name, value = update_queue.get()
            broadcaster.send(revision_id, {
                'type':  'log',
                'stage': stage_name,
                'text':  value,
            })
        except Exception as exc:
            logger.error('Queue forwarder error: %s', exc)


def main() -> None:
    logger.info("Dockyard starting up")

    # 1. Register all queues from the pipeline config
    registry.setup(QUEUES)
    logger.info("Queues registered: %s", QUEUES)

    # 2. Recovery - re-enqueue any stuck 'processing' revisions
    # run_recovery(PIPELINE, ENTRY_STAGE)

    # 3. Thread A - TCP signal listener
    start_signal_listener()
    logger.info("Thread A (signal listener) started")

    # 4. Thread C - WebSocket server for pipeline updates (port 8040)
    ws_thread = threading.Thread(
        target=start_ws_server,
        name="WebSocketServer",
        daemon=True,
    )
    ws_thread.start()
    logger.info("Thread C (WebSocket server) started")

    # 4b. Thread E - Chat WebSocket server (port 8041)
    chat_ws_thread = threading.Thread(
        target=start_chat_ws_server,
        name="ChatWebSocketServer",
        daemon=True,
    )
    chat_ws_thread.start()
    logger.info("Thread E (chat WebSocket server) started")

    # 5. Thread D - Queue forwarder (bridges ProcessPoolExecutor workers → broadcaster)
    manager = Manager()
    update_queue = manager.Queue()
    forwarder_thread = threading.Thread(
        target=_queue_forwarder,
        args=(update_queue,),
        name="QueueForwarder",
        daemon=True,
    )
    forwarder_thread.start()
    logger.info("Thread D (queue forwarder) started")

    # 6. Thread B - Dispatcher (blocking loop) runs after a short delay
    #    so Thread C can bind its port first.
    time.sleep(0.5)
    dispatcher = Dispatcher(
        pipeline=PIPELINE,
        entry_stage=ENTRY_STAGE,
        queue_concurrency=QUEUE_CONCURRENCY,
        update_queue=update_queue,
    )
    dispatcher_thread = threading.Thread(
        target=dispatcher.start,
        name="Dispatcher",
        daemon=True,
    )
    dispatcher_thread.start()
    logger.info("Thread B (dispatcher) started")

    logger.info("Dockyard ready")

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Dockyard shutting down")


if __name__ == "__main__":
    main()
