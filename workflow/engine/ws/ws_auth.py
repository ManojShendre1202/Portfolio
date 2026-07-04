"""
ws_auth.py — No authentication for Readar (public, anonymous access).
All WebSocket connections are allowed.
"""


def validate_connection(websocket, revision_id: int) -> str:
    return 'anonymous'
