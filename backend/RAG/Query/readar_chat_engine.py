"""
readar_chat_engine.py — Bridges browser WebSocket ↔ Gemini streaming, for
curated-doc chat sessions (chat_id-keyed, see schema_design.md).

Flow per question:
    1. Look up the ChatSession's doc_id from chat_id
    2. Embed the question (local nomic model — must match the graph's
       embeddings, see doc_retrieval.py)
    3. Retrieve candidate nodes from the document graph (keyword-seeded,
       graph-hop expansion, per-cluster confidence threshold) — see
       doc_retrieval.py's module docstring for why reranking was removed
    4. Build a numbered context prompt from the retrieved document nodes;
       ask Gemini to cite using [n] markers
    5. Stream the answer back to the browser; once the stream ends, persist
       the turn (ChatTurn)

Concurrency note: chat_ws_server runs one asyncio event loop shared by
every connected user. Every blocking call here (DB lookups, local model
inference, Gemini streaming) runs via asyncio.to_thread or the
producer-thread+queue bridge (_stream_model), so concurrent users'
questions genuinely interleave rather than serializing behind each other.
"""

import asyncio
import logging
import os
import queue as pyqueue
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from asgiref.sync import sync_to_async
from google import genai

from api.core.service.ChatSessionService import ChatSessionService
from backend.RAG.Query import doc_retrieval
from backend.RAG.Query.gemini_rate_guard import chat_rate_limiter, persist_usage, GUARD_MESSAGES, GENERIC_ERROR_MESSAGE
from workflow.engine.ws import live_stats

logger = logging.getLogger(__name__)

GEMINI_KEY = os.getenv('GEMINI_API_KEY')

# Two dedicated pools instead of asyncio's shared default executor
# (min(32, cpu_count+4)) — under concurrent load that single pool was
# starved: every chat needs both a retrieval slot AND a Gemini-stream slot
# held for the whole streaming duration, so 25 concurrent chats could need
# 50 slots against a pool of ~6-8 on this small VM, causing ~7x latency
# (load-tested: 3.2s baseline -> ~20s at 25 concurrent).
#
# retrieval_executor: genuinely CPU-bound (local nomic embedder, no GPU) —
# capped below actual core count so the host OS and other containers
# (nginx, django) always keep a free core rather than this pool saturating
# every CPU on the box.
_CPU_COUNT = os.cpu_count() or 2
RETRIEVAL_WORKERS = max(1, _CPU_COUNT - 1)
retrieval_executor = ThreadPoolExecutor(max_workers=RETRIEVAL_WORKERS, thread_name_prefix="rd-retrieval")

# stream_executor: I/O-bound (blocked on the Gemini network stream, not
# CPU), so it can run far more concurrent threads than there are cores
# without contending with retrieval or starving the OS.
stream_executor = ThreadPoolExecutor(max_workers=64, thread_name_prefix="rd-gemini-stream")

CHAT_MODELS = [
    'gemini-3.1-flash-lite',
    'gemini-2.5-flash',
    'gemini-3.1-flash-lite-preview',
]

SYSTEM_PROMPT = """You are Readar, an intelligent document assistant.
Answer using ONLY the numbered document context entries below (cite these
inline like [1], [2] — every factual sentence should carry at least one
such citation). If the context doesn't contain the answer, say so honestly.
Do not make up information."""


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


# Serializes retrieval+answer per chat_id — without this, two questions
# fired back-to-back on the same session (double-click, duplicate send, two
# tabs sharing a chat_id) would both write ChatTurn rows in an
# unpredictable interleaved order. Plain dict (not locked itself) is safe
# because get-or-create below never awaits between the check and the set,
# so it can't interleave with another task on this single event loop.
_chat_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def _run_retrieval(doc_id: str, question: str):
    """Blocking (model inference + numpy) — call via asyncio.to_thread.

    Times each retrieval sub-step individually — graph_load only shows real
    cost on a cache miss (see doc_retrieval.load_graph), the rest run on
    every call — so slow questions can be attributed to the right stage
    instead of one opaque 'retrieval' bucket.
    """
    timings = {}

    t = time.perf_counter()
    graph, embeddings = doc_retrieval.load_graph(doc_id)
    timings['graph_load'] = round(time.perf_counter() - t, 3)

    t = time.perf_counter()
    q_norm = doc_retrieval.embed_query(question)
    timings['embed_query'] = round(time.perf_counter() - t, 3)

    t = time.perf_counter()
    candidates = doc_retrieval.retrieve_subgraph(q_norm, graph, embeddings, question=question, doc_id=doc_id)
    timings['subgraph_retrieve'] = round(time.perf_counter() - t, 3)

    t = time.perf_counter()
    doc_context, citations = doc_retrieval.build_context(candidates)
    timings['build_context'] = round(time.perf_counter() - t, 3)

    return doc_context, citations, len(candidates), timings


def _stream_model_sync(client, model: str, prompt: str, chunk_queue: pyqueue.Queue) -> None:
    try:
        response     = client.models.generate_content_stream(model=model, contents=prompt)
        usage_tokens = None
        for chunk in response:
            if chunk.text:
                chunk_queue.put(('token', chunk.text))
            usage = getattr(chunk, 'usage_metadata', None)
            if usage is not None and getattr(usage, 'total_token_count', None):
                usage_tokens = usage.total_token_count
        chunk_queue.put(('done', usage_tokens))
    except Exception as e:
        chunk_queue.put(('error', e))


async def _stream_model(client, model: str, prompt: str, send_to_browser) -> tuple[str, int | None, float | None]:
    """Streams tokens to the browser as they arrive.
    Returns (answer_text, usage_tokens, ttfb) — ttfb is seconds from call start
    to the first token chunk, i.e. Gemini's queueing+prompt-eval latency
    before generation is visibly streaming; None if the stream errored
    before any token arrived."""
    loop        = asyncio.get_event_loop()
    chunk_queue = pyqueue.Queue()
    t_start     = time.perf_counter()
    loop.run_in_executor(stream_executor, _stream_model_sync, client, model, prompt, chunk_queue)

    buffer = ""
    ttfb   = None

    while True:
        kind, payload = await loop.run_in_executor(stream_executor, chunk_queue.get)

        if kind == 'token':
            if ttfb is None:
                ttfb = round(time.perf_counter() - t_start, 3)
            buffer += payload
            await send_to_browser({'type': 'token', 'text': payload})

        elif kind == 'done':
            return buffer, payload, ttfb

        elif kind == 'error':
            raise payload


async def handle_question(chat_id: str, question: str, send_to_browser) -> None:
    client = genai.Client(api_key=GEMINI_KEY)

    # t_wall_start is wall-clock from the moment this coroutine was scheduled,
    # so 'lock_wait' below captures time genuinely lost to another question on
    # the same chat_id (see _chat_locks) rather than being folded into
    # whatever segment happens to run after the lock is acquired.
    t_wall_start = time.perf_counter()

    try:
        async with _chat_locks[chat_id]:
            t_lock_acquired = time.perf_counter()
            lock_wait = round(t_lock_acquired - t_wall_start, 3)

            t = time.perf_counter()
            session = await sync_to_async(ChatSessionService.get_by_chat_id)(chat_id)
            doc_id  = session.doc_id
            t_db_get_session = round(time.perf_counter() - t, 3)
            logger.info('handle_question start: chat_id=%s doc_id=%s question=%r', chat_id, doc_id, question[:120])

            t = time.perf_counter()
            await sync_to_async(ChatSessionService.add_turn)(chat_id, role='user', text=question)
            t_db_add_user_turn = round(time.perf_counter() - t, 3)

            t0 = time.perf_counter()
            loop = asyncio.get_event_loop()
            doc_context, citations, n_retrieved, retrieval_timings = await loop.run_in_executor(
                retrieval_executor, _run_retrieval, doc_id, question
            )
            t_retrieval = time.perf_counter() - t0

            prompt = f"""{SYSTEM_PROMPT}

Document context:
{doc_context}

Question: {question}

Answer:"""

            estimated_tokens = _estimate_tokens(prompt)
            t = time.perf_counter()
            ok, reason = chat_rate_limiter.can_proceed(estimated_tokens)
            t_rate_check = round(time.perf_counter() - t, 3)
            if not ok:
                logger.warning('Chat request for session %s blocked by rate guard: %s', chat_id, reason)
                await send_to_browser({'type': 'error', 'text': GUARD_MESSAGES[reason]})
                return

            last_error = None
            for model in CHAT_MODELS:
                try:
                    t1 = time.perf_counter()
                    answer_text, usage_tokens, ttfb = await _stream_model(
                        client, model, prompt, send_to_browser
                    )
                    t_gemini = time.perf_counter() - t1

                    token_count = usage_tokens or estimated_tokens
                    chat_rate_limiter.record(token_count)
                    await sync_to_async(persist_usage)(1, token_count)

                    # db_add_ai_turn (the time the DB write itself takes) genuinely
                    # can't be known before making that write, so it's left out of
                    # the persisted trace. 'total' doesn't have that problem — it's
                    # approximated here (everything up to just before the write) so
                    # a turn reloaded from history still shows a time instead of a
                    # blank one; the browser gets the fully-accurate version below,
                    # computed after the write completes.
                    trace = {
                        'lock_wait':        lock_wait,
                        'db_get_session':   t_db_get_session,
                        'db_add_user_turn': t_db_add_user_turn,
                        'retrieve':         round(t_retrieval, 2),
                        'retrieve_detail':  retrieval_timings,
                        'rate_check':       t_rate_check,
                        'gemini':           round(t_gemini, 2),
                        'gemini_ttfb':      ttfb,
                        'tokens':           token_count,
                        'retrieved':        n_retrieved,
                        'used':             len(citations),
                        'total':            round(time.perf_counter() - t_wall_start, 2),
                    }

                    t = time.perf_counter()
                    await sync_to_async(ChatSessionService.add_turn)(
                        chat_id, role='ai', text=answer_text, citations=citations, trace=trace,
                    )
                    t_db_add_ai_turn = round(time.perf_counter() - t, 3)

                    trace['db_add_ai_turn'] = t_db_add_ai_turn
                    trace['total'] = round(time.perf_counter() - t_wall_start, 2)

                    live_stats.record_call(t_retrieval, t_gemini, t_retrieval + t_gemini)

                    await send_to_browser({'type': 'done', 'citations': citations, 'trace': trace})
                    logger.info(
                        'handle_question done: chat_id=%s model=%s total=%.2fs '
                        'lock_wait=%.3fs db_get_session=%.3fs db_add_user_turn=%.3fs '
                        'retrieve=%.2fs %s rate_check=%.3fs gemini=%.2fs gemini_ttfb=%s '
                        'db_add_ai_turn=%.3fs tokens=%d retrieved=%d cited=%d',
                        chat_id, model, trace['total'],
                        lock_wait, t_db_get_session, t_db_add_user_turn,
                        trace['retrieve'], retrieval_timings, t_rate_check, trace['gemini'], ttfb,
                        t_db_add_ai_turn, trace['tokens'], trace['retrieved'], trace['used'],
                    )
                    return
                except Exception as e:
                    if '429' in str(e) or 'quota' in str(e).lower():
                        logger.warning('Model %s quota hit for chat_id=%s — trying next', model, chat_id)
                        last_error = e
                        continue
                    raise

            logger.error('All chat models exhausted for session %s: %s', chat_id, last_error)
            await send_to_browser({'type': 'error', 'text': GUARD_MESSAGES['rpm']})

    except Exception:
        logger.exception('Chat error for session %s', chat_id)
        await send_to_browser({'type': 'error', 'text': GENERIC_ERROR_MESSAGE})
