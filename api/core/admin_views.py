import time
from pathlib import Path

import psutil
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from api.core.models import ChatSession, ChatTurn
from workflow.engine.ws.live_stats import read_stats

# name shown in the UI -> log file written by settings.py's LOGGING config
LOG_SOURCES = {
    'django':   'django.log',
    'dockyard': 'dockyard.log',
    'rag':      'rag.log',
    'core':     'core.log',
}


@staff_member_required
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')


@staff_member_required
def admin_logs(request):
    source = request.GET.get('source', 'django')
    if source not in LOG_SOURCES:
        return JsonResponse({'error': 'unknown source'}, status=400)

    try:
        lines = int(request.GET.get('lines', 200))
    except ValueError:
        lines = 200
    lines = max(1, min(lines, 1000))

    path = Path(settings.LOG_DIR) / LOG_SOURCES[source]
    if not path.exists():
        return JsonResponse({'lines': [], 'exists': False})

    # Files here are capped at 5MB by the RotatingFileHandler, so reading
    # the whole thing and slicing is cheap — no need for a seek-from-end trick.
    with path.open('r', errors='replace') as f:
        all_lines = f.readlines()

    return JsonResponse({'lines': [l.rstrip('\n') for l in all_lines[-lines:]], 'exists': True})


@staff_member_required
def admin_stats(request):
    live = read_stats()

    disk = psutil.disk_usage('/')
    mem  = psutil.virtual_memory()

    return JsonResponse({
        'server': {
            'cpu_percent':  psutil.cpu_percent(interval=0.3),
            'mem_percent':  mem.percent,
            'mem_used_gb':  round(mem.used / 1e9, 1),
            'mem_total_gb': round(mem.total / 1e9, 1),
            'disk_percent':  disk.percent,
            'disk_used_gb':  round(disk.used / 1e9, 1),
            'disk_total_gb': round(disk.total / 1e9, 1),
        },
        'live': {
            'ws_connections': live.get('ws_connections', 0),
            'gemini':         live.get('gemini'),
            'stats_age_sec':  round(time.time() - live['updated_at'], 1) if 'updated_at' in live else None,
        },
        'db': {
            'total_sessions':  ChatSession.objects.count(),
            'active_sessions': ChatSession.objects.filter(active=True).count(),
            'total_turns':     ChatTurn.objects.count(),
            # "active" here = distinct visitors with a session touched in
            # the last 5 minutes — a DB-side proxy for recent activity,
            # separate from `live.ws_connections` which is only visitors
            # with an open WebSocket at this exact instant.
            'recent_users': (
                ChatSession.objects
                .filter(updated_at__gte=timezone.now() - timezone.timedelta(minutes=5))
                .values_list('client_id', flat=True)
                .distinct()
                .count()
            ),
        },
    })
