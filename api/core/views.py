import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from api.core.service.ChatSessionService import ChatSessionService


@csrf_exempt
@require_POST
def getOrCreateSession(request):
    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid JSON body'}, status=400)

    client_id = (body.get('client_id') or '').strip()
    doc_id    = (body.get('doc_id') or '').strip()
    if not client_id or not doc_id:
        return JsonResponse({'error': 'client_id and doc_id required'}, status=400)

    session = ChatSessionService.get_or_create(client_id, doc_id)
    return JsonResponse({
        'chat_id': str(session.chat_id),
        'doc_id':  session.doc_id,
        'active':  session.active,
    })


@csrf_exempt
@require_POST
def startNewSession(request):
    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid JSON body'}, status=400)

    client_id = (body.get('client_id') or '').strip()
    doc_id    = (body.get('doc_id') or '').strip()
    if not client_id or not doc_id:
        return JsonResponse({'error': 'client_id and doc_id required'}, status=400)

    session = ChatSessionService.start_new(client_id, doc_id)
    return JsonResponse({
        'chat_id': str(session.chat_id),
        'doc_id':  session.doc_id,
        'active':  session.active,
    })


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
    client_id = (request.GET.get('client_id') or '').strip()
    doc_id    = (request.GET.get('doc_id') or '').strip()
    if not client_id or not doc_id:
        return JsonResponse({'error': 'client_id and doc_id required'}, status=400)

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

    return JsonResponse({'sessions': result})


@csrf_exempt
@require_http_methods(['DELETE'])
def deleteSession(request, chat_id):
    client_id = (request.GET.get('client_id') or '').strip()
    doc_id    = (request.GET.get('doc_id') or '').strip()
    if not client_id or not doc_id:
        return JsonResponse({'error': 'client_id and doc_id required'}, status=400)

    ChatSessionService.delete_session(client_id, doc_id, chat_id)
    return JsonResponse({'deleted': True})


@csrf_exempt
@require_POST
def switchSession(request, chat_id):
    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid JSON body'}, status=400)

    client_id = (body.get('client_id') or '').strip()
    doc_id    = (body.get('doc_id') or '').strip()
    if not client_id or not doc_id:
        return JsonResponse({'error': 'client_id and doc_id required'}, status=400)

    try:
        session = ChatSessionService.switch_to(client_id, doc_id, chat_id)
    except Exception:
        return JsonResponse({'error': 'not found'}, status=404)

    return JsonResponse({
        'chat_id': str(session.chat_id),
        'doc_id':  session.doc_id,
        'active':  session.active,
    })
