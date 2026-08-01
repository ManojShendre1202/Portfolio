import asyncio
import json
import logging
import os
import re
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import websockets

from backend.RAG.Query.readar_chat_engine import handle_question

logger  = logging.getLogger(__name__)
WS_PORT = int(os.environ.get('CHAT_WS_PORT', 8041))

_UUID_RE = re.compile(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
)

MAX_QUESTION_CHARS = 2000

# Per-IP sliding-window guard, separate from gemini_rate_guard's process-wide
# Gemini budget — this exists so one abusive client can't burn through that
# shared daily/per-minute budget alone and starve every other visitor.
# Plain dict/deque, no lock: the WS server runs a single event loop and this
# state is only ever touched between awaits (never mutated across one), so
# there's no interleaving hazard even with many concurrent connections.
IP_RPM_LIMIT     = 15
_ip_call_times: dict[str, deque] = {}


def _ip_rate_limited(ip: str) -> bool:
    now   = time.time()
    calls = _ip_call_times.setdefault(ip, deque())
    while calls and calls[0] < now - 60:
        calls.popleft()
    if len(calls) >= IP_RPM_LIMIT:
        return True
    calls.append(now)
    return False


def _parse_chat_id(path: str) -> str | None:
    path  = path.split('?')[0].rstrip('/')
    parts = path.split('/')
    # Expected: ['', 'ws', 'readar-chat', '{chat_id}']
    if len(parts) == 4 and parts[1] == 'ws' and parts[2] == 'readar-chat':
        candidate = parts[3]
        if _UUID_RE.match(candidate):
            return candidate
    return None


async def _handle(websocket) -> None:
    path    = websocket.request.path
    chat_id = _parse_chat_id(path)

    if chat_id is None:
        await websocket.close(4000, 'Invalid path')
        return

    ip = websocket.remote_address[0] if websocket.remote_address else 'unknown'
    logger.info('Chat WS connected: session=%s ip=%s', chat_id, ip)

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

            if len(question) > MAX_QUESTION_CHARS:
                await send_to_browser({'type': 'error', 'text': 'That question is too long — please shorten it.'})
                continue

            if _ip_rate_limited(ip):
                logger.warning('Chat WS rate limit hit: ip=%s session=%s', ip, chat_id)
                await send_to_browser({'type': 'error', 'text': "Slow down a little — you're sending messages faster than Readar can keep up."})
                continue

            logger.info('Chat question for session %s: %s', chat_id, question[:80])
            await handle_question(chat_id, question, send_to_browser)

    except websockets.ConnectionClosed:
        pass

    logger.info('Chat WS disconnected: session=%s', chat_id)


async def _serve() -> None:
    # asyncio.to_thread() calls inside readar_chat_engine.py (embed, rerank, sync
    # Django ORM writes) run on this loop's default executor. Sized generously
    # above cpu_count since this workload is I/O-bound (waiting on Gemini's
    # network round-trip dominates total latency) rather than CPU-bound, so
    # threads mostly sit blocked on I/O rather than contending for the GIL.
    asyncio.get_event_loop().set_default_executor(ThreadPoolExecutor(max_workers=16))

    async with websockets.serve(_handle, '0.0.0.0', WS_PORT):
        logger.info('Chat WebSocket server listening on port %d', WS_PORT)
        await asyncio.Future()


def start_chat_ws_server() -> None:
    asyncio.run(_serve())
