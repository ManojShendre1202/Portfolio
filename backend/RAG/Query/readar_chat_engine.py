"""
readar_chat_engine.py — Bridges browser WebSocket ↔ Gemini streaming, for
curated-doc chat sessions (chat_id-keyed, see schema_design.md).

Flow per question:
    1. Look up the ChatSession's doc_id from chat_id
    2. Embed the question (local nomic model — must match the graph's
       embeddings, see doc_retrieval.py)
    3. Retrieve candidate nodes from the document graph (top-k + graph-hop
       expansion, cross-encoder rerank) — the validated pipeline from
       several stress-testing sessions
    4. Also retrieve relevant prior turns from this session's own memory
       graph (session_memory.py) — retrieval-augmented conversation memory,
       not raw resent history
    5. Build a numbered context prompt (document context + memory context);
       ask Gemini to (a) cite using [n] markers and (b) end with a hidden
       one-line memory summary after a delimiter the browser never sees
    6. Stream the visible answer back to the browser; once the stream ends,
       persist both turns (ChatTurn) and embed the hidden summary into the
       session's memory graph — awaited (not fire-and-forget) since it's
       cheap local work and a background task here created a real race
       against a quick next question reading the memory file too early

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

from asgiref.sync import sync_to_async
from google import genai

from api.core.service.ChatSessionService import ChatSessionService
from backend.RAG.Query import doc_retrieval, session_memory
from backend.RAG.Query.gemini_rate_guard import chat_rate_limiter, GUARD_MESSAGES, GENERIC_ERROR_MESSAGE

logger = logging.getLogger(__name__)

GEMINI_KEY = os.getenv('GEMINI_API_KEY')

CHAT_MODELS = [
    'gemini-3.1-flash-lite',
    'gemini-2.5-flash',
    'gemini-3.1-flash-lite-preview',
]

# The browser never sees anything from this marker onward — see _stream_model.
MEMORY_MARKER = "\n###MEMORY_SUMMARY###\n"

SYSTEM_PROMPT = f"""You are Readar, an intelligent document assistant.
Answer using ONLY two sources: the numbered document context entries
below (cite these inline like [1], [2] — every factual sentence should
carry at least one such citation), AND, if present, the "Relevant prior
exchanges" section — that section is valid grounding too, especially for
follow-up questions that refer back to something already established
earlier in this conversation (e.g. "that", "those", "it"). Resolve such
references using the prior exchanges before deciding whether the
document context answers the question. If neither source contains the
answer, say so honestly. Do not make up information.

After your complete answer, output the exact line "{MEMORY_MARKER.strip()}"
on its own, then on the next line write ONE short sentence summarizing
this question and answer for future conversation memory — this part is
never shown to the user, so be terse and information-dense, not
conversational."""


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


# Serializes retrieval+answer+memory-append per chat_id — without this, two
# questions fired back-to-back on the same session (double-click, duplicate
# send, two tabs sharing a chat_id) would both read session_memory before
# either writes, and the second append_turn silently clobbers the first
# turn's summary (lost-update race on the per-session pickle file). Plain
# dict (not locked itself) is safe because get-or-create below never awaits
# between the check and the set, so it can't interleave with another task
# on this single event loop.
_chat_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def _run_retrieval(doc_id: str, chat_id: str, question: str):
    """Blocking (model inference + numpy) — call via asyncio.to_thread."""
    graph, embeddings = doc_retrieval.load_graph(doc_id)
    q_norm             = doc_retrieval.embed_query(question)

    subgraph  = doc_retrieval.retrieve_subgraph(q_norm, graph, embeddings)
    reranked  = doc_retrieval.rerank_nodes(question, subgraph)
    doc_context, citations = doc_retrieval.build_context(reranked)

    memory_turns  = session_memory.retrieve(chat_id, q_norm)
    memory_context = session_memory.build_memory_prompt(memory_turns)

    return doc_context, citations, memory_context, len(subgraph), len(reranked)


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


async def _stream_model(client, model: str, prompt: str, send_to_browser) -> tuple[str, str | None, int | None]:
    """
    Streams tokens to the browser, but holds back anything from
    MEMORY_MARKER onward — that part is the hidden summary, never sent.
    Returns (visible_answer_text, hidden_summary_or_None, usage_tokens).

    Buffers the tail of what's been received (up to len(MEMORY_MARKER)-1
    chars) before forwarding, since a chunk boundary could split the
    marker across two chunks — only text we're sure isn't a partial
    marker match gets sent immediately.
    """
    loop        = asyncio.get_event_loop()
    chunk_queue = pyqueue.Queue()
    loop.run_in_executor(None, _stream_model_sync, client, model, prompt, chunk_queue)

    buffer     = ""
    sent_len   = 0
    marker_idx = -1

    while True:
        kind, payload = await loop.run_in_executor(None, chunk_queue.get)

        if kind == 'token':
            buffer += payload
            if marker_idx == -1:
                idx = buffer.find(MEMORY_MARKER)
                if idx != -1:
                    marker_idx = idx
                    visible = buffer[sent_len:marker_idx]
                    if visible:
                        await send_to_browser({'type': 'token', 'text': visible})
                    sent_len = marker_idx
                else:
                    safe_len = max(sent_len, len(buffer) - (len(MEMORY_MARKER) - 1))
                    if safe_len > sent_len:
                        await send_to_browser({'type': 'token', 'text': buffer[sent_len:safe_len]})
                        sent_len = safe_len
            # once marker_idx is set, everything further is hidden-summary text — never forwarded

        elif kind == 'done':
            if marker_idx == -1:
                # marker never showed up — fall back to showing everything (no summary this turn)
                if len(buffer) > sent_len:
                    await send_to_browser({'type': 'token', 'text': buffer[sent_len:]})
                return buffer, None, payload
            visible_text = buffer[:marker_idx]
            summary_text = buffer[marker_idx + len(MEMORY_MARKER):].strip() or None
            return visible_text, summary_text, payload

        elif kind == 'error':
            raise payload


async def handle_question(chat_id: str, question: str, send_to_browser) -> None:
    client = genai.Client(api_key=GEMINI_KEY)

    try:
        # Serializes this whole retrieval -> answer -> memory-append sequence
        # per chat_id — see _chat_locks comment for why this matters.
        async with _chat_locks[chat_id]:
            session = await sync_to_async(ChatSessionService.get_by_chat_id)(chat_id)
            doc_id  = session.doc_id

            await sync_to_async(ChatSessionService.add_turn)(chat_id, role='user', text=question)

            t0 = time.perf_counter()
            doc_context, citations, memory_context, n_retrieved, n_reranked = await asyncio.to_thread(
                _run_retrieval, doc_id, chat_id, question
            )
            t_retrieval = time.perf_counter() - t0

            prompt = f"""{SYSTEM_PROMPT}

{memory_context}Document context:
{doc_context}

Question: {question}

Answer:"""

            estimated_tokens = _estimate_tokens(prompt)
            ok, reason = chat_rate_limiter.can_proceed(estimated_tokens)
            if not ok:
                logger.warning('Chat request for session %s blocked by rate guard: %s', chat_id, reason)
                await send_to_browser({'type': 'error', 'text': GUARD_MESSAGES[reason]})
                return

            last_error = None
            for model in CHAT_MODELS:
                try:
                    t1 = time.perf_counter()
                    answer_text, summary_text, usage_tokens = await _stream_model(
                        client, model, prompt, send_to_browser
                    )
                    t_gemini = time.perf_counter() - t1

                    token_count = usage_tokens or estimated_tokens
                    chat_rate_limiter.record(token_count)

                    trace = {
                        'total':     round(t_retrieval + t_gemini, 2),
                        'retrieve':  round(t_retrieval, 2),
                        'gemini':    round(t_gemini, 2),
                        'tokens':    token_count,
                        'retrieved': n_retrieved,
                        'reranked':  n_reranked,
                        'used':      len(citations),
                    }

                    await sync_to_async(ChatSessionService.add_turn)(
                        chat_id, role='ai', text=answer_text, citations=citations, trace=trace,
                    )

                    if summary_text:
                        # Awaited (not fire-and-forget) — this is cheap (local embed + tiny
                        # pickle write, no network call), and a background task here created
                        # a real race: a quick follow-up question could read the memory file
                        # before this write landed, silently seeing no prior-turn context.
                        # asyncio.to_thread still keeps it off the event loop, so other
                        # connected users aren't blocked by it.
                        await asyncio.to_thread(session_memory.append_turn, chat_id, question, summary_text)
                    else:
                        logger.warning('No memory summary parsed for session %s — marker missing from response', chat_id)

                    await send_to_browser({'type': 'done', 'citations': citations, 'trace': trace})
                    return
                except Exception as e:
                    if '429' in str(e) or 'quota' in str(e).lower():
                        logger.warning('Model %s quota hit — trying next', model)
                        last_error = e
                        continue
                    raise

            logger.error('All chat models exhausted for session %s: %s', chat_id, last_error)
            await send_to_browser({'type': 'error', 'text': GUARD_MESSAGES['rpm']})

    except Exception:
        logger.exception('Chat error for session %s', chat_id)
        await send_to_browser({'type': 'error', 'text': GENERIC_ERROR_MESSAGE})
