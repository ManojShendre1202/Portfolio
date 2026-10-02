import re
import time
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path

import psutil
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from api.core.models import ChatSession, ChatTurn, PageView
from api.core.tracking_views import is_ignored
from workflow.engine.ws.live_stats import read_stats

# name shown in the UI -> log file written by settings.py's LOGGING config
LOG_SOURCES = {
    'django':   'django.log',
    'dockyard': 'dockyard.log',
    'rag':      'rag.log',
    'core':     'core.log',
}

# Matches settings.py's 'standard' formatter:
#   '%(asctime)s %(levelname)s %(name)s: %(message)s'
# asctime is "YYYY-MM-DD HH:MM:SS,mmm" in the process's local time, which is
# UTC here (Django pins TZ to settings.TIME_ZONE = 'UTC').
_LOG_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}),(\d{3}) '
    r'(DEBUG|INFO|WARNING|ERROR|CRITICAL) (\S+): (.*)$'
)

# RotatingFileHandler keeps django.log plus django.log.1 … .3 (backupCount=3).
_LOG_BACKUPS = 3


@staff_member_required
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')


def _read_log_lines(path: Path, want: int) -> list[str]:
    """Newest `want`-ish raw lines, reaching back into rotated backups when
    the current file alone doesn't have enough. Files are capped at 5MB so
    reading them whole is cheap."""
    lines: list[str] = []
    for i in range(_LOG_BACKUPS + 1):
        p = path if i == 0 else path.with_name(f'{path.name}.{i}')
        if not p.exists():
            break
        with p.open('r', errors='replace') as f:
            lines = f.read().splitlines() + lines
        if len(lines) >= want:
            break
    return lines


def _parse_log(raw_lines: list[str]) -> list[dict]:
    """Group raw lines into entries. A line that doesn't start with a
    timestamp (traceback frames, multi-line messages) belongs to the entry
    before it."""
    entries: list[dict] = []
    for line in raw_lines:
        m = _LOG_RE.match(line)
        if m:
            date, hms, ms, level, logger_name, message = m.groups()
            entries.append({
                'ts': f'{date}T{hms}.{ms}Z',
                'level': level,
                'logger': logger_name,
                'message': message,
            })
        elif entries:
            entries[-1]['message'] += '\n' + line
        elif line.strip():
            entries.append({'ts': None, 'level': 'INFO', 'logger': '', 'message': line})
    return entries


@staff_member_required
def admin_logs(request):
    source = request.GET.get('source', 'django')
    if source not in LOG_SOURCES:
        return JsonResponse({'error': 'unknown source'}, status=400)

    try:
        limit = int(request.GET.get('lines', 200))
    except ValueError:
        limit = 200
    limit = max(1, min(limit, 1000))

    path = Path(settings.LOG_DIR) / LOG_SOURCES[source]
    if not path.exists():
        return JsonResponse({'entries': [], 'exists': False})

    # Over-read raw lines so multi-line entries (tracebacks) still leave us
    # with `limit` whole entries after grouping.
    raw = _read_log_lines(path, limit * 4)
    entries = _parse_log(raw)[-limit:]

    return JsonResponse({
        'entries': entries,
        'exists': True,
        'server_time': timezone.now().isoformat(),
    })


@staff_member_required
def admin_stats(request):
    live = read_stats()

    disk = psutil.disk_usage('/')
    mem  = psutil.virtual_memory()

    return JsonResponse({
        'server_time': timezone.now().isoformat(),
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
            'ws_connections':   live.get('ws_connections', 0),
            'gemini':           live.get('gemini'),
            'stats_age_sec':    round(time.time() - live['updated_at'], 1) if 'updated_at' in live else None,
            'avg_latency_sec':  live.get('avg_latency_sec'),
            'last_latency_sec': live.get('last_latency_sec'),
            'recent_calls':     live.get('recent_calls', []),
        },
        'db': {
            'total_sessions':  ChatSession.objects.count(),
            'active_sessions': ChatSession.objects.filter(active=True).count(),
            'total_turns':     ChatTurn.objects.count(),
        },
    })


def _distinct_visitors(qs) -> int:
    return qs.values('visitor_id').distinct().count()


def _breakdown(qs, field: str, blank_label: str | None = None, limit: int = 8) -> list[dict]:
    """Distinct visitors per value of `field`, biggest first."""
    rows = (
        qs.values(field)
        .annotate(visitors=Count('visitor_id', distinct=True), views=Count('id'))
        .order_by('-visitors', '-views')
    )
    out = []
    for r in rows:
        name = r[field]
        if not name:
            if blank_label is None:
                continue
            name = blank_label
        out.append({'name': name, 'visitors': r['visitors'], 'views': r['views']})
    return out[:limit]


@staff_member_required
def admin_analytics(request):
    try:
        days = int(request.GET.get('days', 7))
    except ValueError:
        days = 7
    days = max(1, min(days, 365))

    # The browser sends its own UTC offset (minutes east of UTC) so "today"
    # and the per-day buckets line up with the viewer's calendar, not UTC's.
    try:
        tz_minutes = int(request.GET.get('tz', 0))
    except ValueError:
        tz_minutes = 0
    tz_minutes = max(-14 * 60, min(tz_minutes, 14 * 60))
    tz = dt_timezone(timedelta(minutes=tz_minutes))

    now         = timezone.now()
    local_today = now.astimezone(tz).date()
    start_date  = local_today - timedelta(days=days - 1)
    start       = datetime.combine(start_date, datetime.min.time(), tzinfo=tz)
    prev_start  = start - timedelta(days=days)

    all_views = PageView.objects.all()
    qs        = all_views.filter(created_at__gte=start)
    prev_qs   = all_views.filter(created_at__gte=prev_start, created_at__lt=start)

    visitors     = _distinct_visitors(qs)
    new_visitors = _distinct_visitors(qs.filter(is_new_visitor=True))

    # Per-day series, with zero-filled gaps so the chart has no holes.
    by_day = {
        r['day']: r for r in
        qs.annotate(day=TruncDate('created_at', tzinfo=tz))
          .values('day')
          .annotate(views=Count('id'), visitors=Count('visitor_id', distinct=True))
    }
    series = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        row = by_day.get(d)
        series.append({
            'date': d.isoformat(),
            'views': row['views'] if row else 0,
            'visitors': row['visitors'] if row else 0,
        })

    today_start     = datetime.combine(local_today, datetime.min.time(), tzinfo=tz)
    yesterday_start = today_start - timedelta(days=1)
    today_visitors     = _distinct_visitors(all_views.filter(created_at__gte=today_start))
    yesterday_visitors = _distinct_visitors(
        all_views.filter(created_at__gte=yesterday_start, created_at__lt=today_start)
    )
    online_now = _distinct_visitors(all_views.filter(created_at__gte=now - timedelta(minutes=5)))

    first = all_views.order_by('created_at').values_list('created_at', flat=True).first()

    # Chat engagement comes from ChatSession/ChatTurn, which the app purges
    # after a week — so for windows longer than 7 days these undercount.
    sessions_qs = ChatSession.objects.filter(created_at__gte=start)
    turns_qs    = ChatTurn.objects.filter(created_at__gte=start, role='user')
    readar_visitors = _distinct_visitors(qs.filter(path__startswith='/readar'))
    chatters = sessions_qs.values('client_id').distinct().count()

    recent = [
        {
            'ts': v.created_at.isoformat(),
            'path': v.path,
            'referrer': v.referrer_host,
            'device': v.device,
            'browser': v.browser,
            'country': v.country,
            'new': v.is_new_visitor,
            'visitor': v.visitor_id[-6:],
        }
        for v in all_views.order_by('-created_at')[:40]
    ]

    return JsonResponse({
        'server_time': now.isoformat(),
        'days': days,
        'ignored_browser': is_ignored(request),
        'totals': {
            'views': qs.count(),
            'visitors': visitors,
            'new_visitors': new_visitors,
            'returning_visitors': visitors - new_visitors,
            'prev_views': prev_qs.count(),
            'prev_visitors': _distinct_visitors(prev_qs),
            'today_visitors': today_visitors,
            'yesterday_visitors': yesterday_visitors,
            'online_now': online_now,
            'all_time_views': all_views.count(),
            'tracking_since': first.isoformat() if first else None,
        },
        'series': series,
        'top_pages': _breakdown(qs, 'path', limit=10),
        'referrers': _breakdown(qs, 'referrer_host', blank_label='Direct / unknown'),
        'devices': _breakdown(qs, 'device'),
        'browsers': _breakdown(qs, 'browser'),
        'countries': _breakdown(qs, 'country'),
        'engagement': {
            'readar_visitors': readar_visitors,
            'chat_sessions': sessions_qs.count(),
            'chatters': chatters,
            'questions_asked': turns_qs.count(),
            'limited_by_retention': days > 7,
        },
        'recent': recent,
    })
