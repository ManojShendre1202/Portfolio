"""
gemini_live_chat.py — Bridges browser WebSocket ↔ Gemini streaming

Flow:
    Browser sends:  { "question": "..." }
    We:
        1. Embed the question
        2. Semantic search: top-k relevant sentences/paragraphs/sections
           from graph.json (graph_search.py)
        3. Entity search: any entities mentioned/related to the question,
           with ALL of their relationships pulled from anywhere in the
           document — not just top-k — so relationships spanning distant
           pages (e.g. an object introduced on page 2, referenced again on
           page 16) aren't missed (entity_search.py)
        4. Combine both into a compact context prompt and send to Gemini
        5. Stream chunks back to browser as:
              { "type": "token",  "text": "..." }
              { "type": "done" }
              { "type": "error",  "text": "..." }
"""

import logging
import os

from google import genai

from backend.RAG.embeddings import embed_text
from backend.RAG.Query.graph_search import (
    load_graph,
    search,
    build_context_prompt,
    is_enumeration_question,
    search_full_sections,
    build_full_section_prompt,
)
from backend.RAG.Query.entity_search import load_entity_graph, search_entities, build_entity_context_prompt

logger = logging.getLogger(__name__)

GEMINI_KEY = os.getenv('GEMINI_API_KEY')

CHAT_MODELS = [
    # 'gemma-4-31b-it',
    'gemini-3.1-flash-lite',
    'gemini-2.5-flash',
    'gemini-3.1-flash-lite-preview',
]

SYSTEM_PROMPT = """You are Readar, an intelligent document assistant.
You have been given retrieved context from a document: the most relevant
sentences/paragraphs/sections for the question, plus any known entities and
their relationships/facts from across the whole document.
Answer clearly and concisely based only on this context.
If the answer isn't in the context, say so honestly.
Do not make up information."""


async def handle_question(job_id: int, question: str, send_to_browser) -> None:
    """
    Main entry point called by the chat WS server for each user message.
    send_to_browser: async callable that accepts a dict and sends it to the browser.
    """
    client = genai.Client(api_key=GEMINI_KEY)

    try:
        graph        = load_graph(job_id)
        entity_graph = load_entity_graph(job_id)

        question_embedding = embed_text(client, question)

        # "List all X" / "how many X" questions need full-section coverage —
        # top-k similarity search can never answer those correctly, since it
        # only ever returns the closest handful of matches by construction.
        if is_enumeration_question(question):
            full_result       = search_full_sections(graph, question_embedding)
            semantic_context  = build_full_section_prompt(full_result)
        else:
            semantic_result   = search(graph, question_embedding)
            semantic_context  = build_context_prompt(semantic_result)

        entity_result  = search_entities(entity_graph, question, question_embedding)
        entity_context = build_entity_context_prompt(entity_result)

        prompt = f"""{SYSTEM_PROMPT}

{semantic_context}
{entity_context}
Question: {question}"""

        last_error = None
        for model in CHAT_MODELS:
            try:
                response = client.models.generate_content_stream(
                    model=model,
                    contents=prompt,
                )
                for chunk in response:
                    if chunk.text:
                        await send_to_browser({'type': 'token', 'text': chunk.text})
                await send_to_browser({'type': 'done'})
                return
            except Exception as e:
                if '429' in str(e) or 'quota' in str(e).lower():
                    logger.warning('Model %s quota hit — trying next', model)
                    last_error = e
                    continue
                raise

        raise RuntimeError(f"All models exhausted: {last_error}")

    except Exception as e:
        logger.error('Chat error for job %s: %s', job_id, e)
        await send_to_browser({'type': 'error', 'text': str(e)})
