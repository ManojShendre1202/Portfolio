import json
import uuid

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from api.core.service.ChatSessionService import ChatSessionService

# The server is the sole issuer of client_id, via this cookie — nothing
# read from a request body/query string is ever trusted as identity.
# Without this, any visitor could pass any client_id string and read,
# switch, or delete another visitor's sessions (IDOR). A random UUID
# handed out here and echoed back by the browser on every request is
# enough to keep sessions private per-browser without requiring signup.
CLIENT_ID_COOKIE   = 'readar_cid'
CLIENT_ID_MAX_AGE  = 60 * 60 * 24 * 7  # 1 week — matches ChatSessionService's DB retention


def _client_id(request) -> tuple[str, bool]:
    cid = request.COOKIES.get(CLIENT_ID_COOKIE)
    if cid:
        return cid, False
    return str(uuid.uuid4()), True


def _with_client_cookie(response, client_id: str, is_new: bool):
    if is_new:
        response.set_cookie(
            CLIENT_ID_COOKIE, client_id,
            max_age=CLIENT_ID_MAX_AGE,
            httponly=True,
            samesite='Lax',
            secure=True,
        )
    return response


@csrf_exempt
@require_POST
def getOrCreateSession(request):
    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid JSON body'}, status=400)

    doc_id = (body.get('doc_id') or '').strip()
    if not doc_id:
        return JsonResponse({'error': 'doc_id required'}, status=400)

    client_id, is_new = _client_id(request)
    session = ChatSessionService.get_or_create(client_id, doc_id)
    response = JsonResponse({
        'chat_id': str(session.chat_id),
        'doc_id':  session.doc_id,
        'active':  session.active,
    })
    return _with_client_cookie(response, client_id, is_new)


@csrf_exempt
@require_POST
def startNewSession(request):
    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid JSON body'}, status=400)

    doc_id = (body.get('doc_id') or '').strip()
    if not doc_id:
        return JsonResponse({'error': 'doc_id required'}, status=400)

    client_id, is_new = _client_id(request)
    session = ChatSessionService.start_new(client_id, doc_id)
    response = JsonResponse({
        'chat_id': str(session.chat_id),
        'doc_id':  session.doc_id,
        'active':  session.active,
    })
    return _with_client_cookie(response, client_id, is_new)


@require_GET
def getSessionTurns(request, chat_id):
    try:
        turns = ChatSessionService.get_turns(chat_id)
    except Exception:
        return JsonResponse({'error': 'not found'}, status=404)

    result = [{
        'role':       t.role,
        'text':       t.text,
        'bullets':    t.bullets,
        'citations':  t.citations,
        'trace':      t.trace,
        'created_at': t.created_at.isoformat(),
    } for t in turns]

    return JsonResponse({'turns': result})


@require_GET
def listSessions(request):
    doc_id = (request.GET.get('doc_id') or '').strip()
    if not doc_id:
        return JsonResponse({'error': 'doc_id required'}, status=400)

    client_id, is_new = _client_id(request)
    sessions = ChatSessionService.list_sessions(client_id, doc_id)

    result = []
    for s in sessions:
        turns = list(s.turns.all())
        first_question = next((t.text for t in turns if t.role == 'user'), None)
        result.append({
            'chat_id':        str(s.chat_id),
            'active':         s.active,
            'turn_count':     len(turns),
            'first_question': first_question,
            'updated_at':     s.updated_at.isoformat(),
        })

    response = JsonResponse({'sessions': result})
    return _with_client_cookie(response, client_id, is_new)


@csrf_exempt
@require_http_methods(['DELETE'])
def deleteSession(request, chat_id):
    doc_id = (request.GET.get('doc_id') or '').strip()
    if not doc_id:
        return JsonResponse({'error': 'doc_id required'}, status=400)

    client_id, is_new = _client_id(request)
    ChatSessionService.delete_session(client_id, doc_id, chat_id)
    response = JsonResponse({'deleted': True})
    return _with_client_cookie(response, client_id, is_new)


@csrf_exempt
@require_POST
def switchSession(request, chat_id):
    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid JSON body'}, status=400)

    doc_id = (body.get('doc_id') or '').strip()
    if not doc_id:
        return JsonResponse({'error': 'doc_id required'}, status=400)

    client_id, is_new = _client_id(request)
    try:
        session = ChatSessionService.switch_to(client_id, doc_id, chat_id)
    except Exception:
        return JsonResponse({'error': 'not found'}, status=404)

    response = JsonResponse({
        'chat_id': str(session.chat_id),
        'doc_id':  session.doc_id,
        'active':  session.active,
    })
    return _with_client_cookie(response, client_id, is_new)
