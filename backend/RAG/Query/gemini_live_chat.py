"""
gemini_live_chat.py — Bridges browser WebSocket ↔ Gemini streaming

Flow:
    Browser sends:  { "question": "..." }
    We:
        1. Load graph.json, strip embeddings
        2. Send full graph structure + question to Gemini
        3. Stream chunks back to browser as:
              { "type": "token",  "text": "..." }
              { "type": "done" }
              { "type": "error",  "text": "..." }
"""

import json
import logging
import os

from google import genai

from backend.RAG.Query.graph_search import load_graph

logger = logging.getLogger(__name__)

GEMINI_KEY = os.getenv('GEMINI_API_KEY')

CHAT_MODELS = [
    'gemma-4-31b-it',
    'gemini-3.1-flash-lite',
    'gemini-2.5-flash',
    'gemini-3.1-flash-lite-preview',
]

SYSTEM_PROMPT = """You are Readar, an intelligent document assistant.
You have been given a hierarchical knowledge graph of a document.
The graph has 4 levels: document → sections → paragraphs → sentences.
Each level has a summary and page references so you understand structure and context.
Answer clearly and concisely based only on this graph.
If the answer isn't in the graph, say so honestly.
Do not make up information."""


def _strip_embeddings(graph: dict) -> dict:
    """Remove embedding arrays from all nodes — they're noise to the model."""
    def clean(nodes):
        return [{k: v for k, v in node.items() if k != 'embedding'} for node in nodes]

    return {
        'document':   {k: v for k, v in graph['document'].items() if k != 'embedding'},
        'sections':   clean(graph.get('sections',   [])),
        'paragraphs': clean(graph.get('paragraphs', [])),
        'sentences':  clean(graph.get('sentences',  [])),
    }


async def handle_question(job_id: int, question: str, send_to_browser) -> None:
    """
    Main entry point called by the chat WS server for each user message.
    send_to_browser: async callable that accepts a dict and sends it to the browser.
    """
    client = genai.Client(api_key=GEMINI_KEY)

    try:
        graph       = load_graph(job_id)
        clean_graph = _strip_embeddings(graph)

        prompt = f"""{SYSTEM_PROMPT}

DOCUMENT KNOWLEDGE GRAPH:
{json.dumps(clean_graph, indent=2)}

QUESTION: {question}"""

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
