"""
chat_ws_server.py — WebSocket server for Readar chat (port 8041)

URL pattern: ws://host/ws/chat/{job_id}

Browser sends:  { "question": "..." }
Server streams: { "type": "token", "text": "..." }
                { "type": "done" }
                { "type": "error", "text": "..." }
"""

import asyncio
import json
import logging
import os

import websockets

from backend.RAG.Query.gemini_live_chat import handle_question

logger  = logging.getLogger(__name__)
WS_PORT = int(os.environ.get('CHAT_WS_PORT', 8041))


def _parse_job_id(path: str) -> int | None:
    path  = path.split('?')[0].rstrip('/')
    parts = path.split('/')
    # Expected: ['', 'ws', 'chat', '{job_id}']
    if len(parts) == 4 and parts[1] == 'ws' and parts[2] == 'chat':
        try:
            return int(parts[3])
        except ValueError:
            pass
    return None


async def _handle(websocket) -> None:
    path   = websocket.request.path
    job_id = _parse_job_id(path)

    if job_id is None:
        await websocket.close(4000, 'Invalid path')
        return

    logger.info('Chat WS connected: job=%s', job_id)

    async def send_to_browser(msg: dict) -> None:
        try:
            await websocket.send(json.dumps(msg))
        except Exception as exc:
            logger.warning('Chat WS send failed: %s', exc)

    try:
        async for raw in websocket:
            try:
                data     = json.loads(raw)
                question = data.get('question', '').strip()
            except Exception:
                await send_to_browser({'type': 'error', 'text': 'Invalid message format'})
                continue

            if not question:
                continue

            logger.info('Chat question for job %s: %s', job_id, question[:80])
            await handle_question(job_id, question, send_to_browser)

    except websockets.ConnectionClosed:
        pass

    logger.info('Chat WS disconnected: job=%s', job_id)


async def _serve() -> None:
    async with websockets.serve(_handle, '0.0.0.0', WS_PORT):
        logger.info('Chat WebSocket server listening on port %d', WS_PORT)
        await asyncio.Future()


def start_chat_ws_server() -> None:
    asyncio.run(_serve())
