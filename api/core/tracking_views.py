import json
import logging
import re
import uuid
from urllib.parse import urlparse

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from api.core.models import PageView

logger = logging.getLogger(__name__)

# Long-lived, separate from the 7-day chat cookie (readar_cid) — a visitor
# who comes back a month later should count as "returning", not new.
VISITOR_COOKIE      = 'pv_vid'
VISITOR_MAX_AGE     = 60 * 60 * 24 * 365
# Set on the owner's own browsers so their visits never reach the DB.
IGNORE_COOKIE       = 'pv_ignore'

# Same visitor + same path inside this window is treated as a duplicate
# (React StrictMode double-effects, quick refreshes, double-clicks).
DEDUPE_SECONDS      = 30

_BOT_RE = re.compile(
    r'bot|crawl|spider|slurp|facebookexternalhit|preview|headless|lighthouse|'
    r'pingdom|uptime|monitor|curl|wget|python-requests|httpx|aiohttp|axios|'
    r'go-http|okhttp|scrapy|java/|libwww|postman|phantom',
    re.IGNORECASE,
)


def _device(ua: str) -> str:
    u = ua.lower()
    if 'ipad' in u or 'tablet' in u:
        return 'tablet'
    if 'mobi' in u or 'android' in u or 'iphone' in u:
        return 'mobile'
    return 'desktop'


def _browser(ua: str) -> str:
    # Order matters: Edge/Opera UAs also contain "Chrome", Chrome's contains "Safari".
    for needle, name in (('edg', 'Edge'), ('opr/', 'Opera'), ('firefox', 'Firefox'),
                         ('chrome', 'Chrome'), ('crios', 'Chrome'), ('safari', 'Safari')):
        if needle in ua.lower():
            return name
    return 'Other'


def _referrer_host(raw: str, own_host: str) -> str:
    if not raw:
        return ''
    host = (urlparse(raw).hostname or '').lower()
    if host.startswith('www.'):
        host = host[4:]
    own = own_host.split(':')[0].lower()
    if own.startswith('www.'):
        own = own[4:]
    return '' if host == own else host[:255]


@csrf_exempt
@require_POST
def track_pageview(request):
    # Never let analytics break the site — every failure path is a quiet 204.
    if request.COOKIES.get(IGNORE_COOKIE):
        return HttpResponse(status=204)

    ua = request.META.get('HTTP_USER_AGENT', '')
    if not ua or _BOT_RE.search(ua):
        return HttpResponse(status=204)

    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return HttpResponse(status=204)

    path = str(body.get('path') or '')[:255]
    if not path.startswith('/'):
        return HttpResponse(status=204)

    visitor_id = request.COOKIES.get(VISITOR_COOKIE)
    is_new = not visitor_id
    if is_new:
        visitor_id = uuid.uuid4().hex

    recent_cutoff = timezone.now() - timezone.timedelta(seconds=DEDUPE_SECONDS)
    duplicate = (not is_new) and PageView.objects.filter(
        visitor_id=visitor_id, path=path, created_at__gte=recent_cutoff,
    ).exists()

    if not duplicate:
        try:
            PageView.objects.create(
                visitor_id=visitor_id,
                path=path,
                referrer_host=_referrer_host(str(body.get('referrer') or ''), request.get_host()),
                device=_device(ua),
                browser=_browser(ua),
                # Only present if the site is ever put behind Cloudflare; blank otherwise.
                country=(request.META.get('HTTP_CF_IPCOUNTRY', '') or '')[:2].upper().replace('XX', ''),
                is_new_visitor=is_new,
            )
        except Exception:
            logger.exception('track_pageview: failed to record view for path=%s', path)

    response = HttpResponse(status=204)
    if is_new:
        response.set_cookie(
            VISITOR_COOKIE, visitor_id,
            max_age=VISITOR_MAX_AGE, httponly=True, samesite='Lax', secure=True,
        )
    return response


@csrf_exempt
@require_POST
def track_optout(request):
    """Body {"off": true} stops this browser being counted; {"off": false}
    resumes. Called by the frontend when the URL has ?notrack=1 / ?notrack=0,
    and by the "exclude this browser" toggle on the admin dashboard."""
    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        body = {}

    off = bool(body.get('off', True))
    response = JsonResponse({'ignored': off})
    if off:
        response.set_cookie(
            IGNORE_COOKIE, '1',
            max_age=VISITOR_MAX_AGE, httponly=True, samesite='Lax', secure=True,
        )
    else:
        response.delete_cookie(IGNORE_COOKIE)
    return response


def is_ignored(request) -> bool:
    return bool(request.COOKIES.get(IGNORE_COOKIE))
