import hashlib
import json
import logging
import re
import uuid
from datetime import timedelta
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
# Set on the owner's own browsers (?notrack=1). Those visits are still stored,
# but labelled 'owner' and kept out of the visitor numbers.
IGNORE_COOKIE       = 'pv_ignore'

# PageView.visit_class values (see the model for what each one means).
OWNER      = 'owner'
BOT        = 'bot'
GENUINE    = 'genuine'
UNVERIFIED = 'unverified'
LEGACY     = 'legacy'
# The classes that make up the headline "unique visitors" / "page views".
COUNTED_CLASSES = (LEGACY, UNVERIFIED, GENUINE)

# Same visitor + same path inside this window is treated as a duplicate
# (React StrictMode double-effects, quick refreshes, double-clicks).
DEDUPE_SECONDS      = 30
# Bots are stored so they can be counted, but a hammering client must not be
# able to flood the table: one row per user-agent + path per window.
BOT_DEDUPE_SECONDS  = 600
# The "engaged" beacon only upgrades a view that is at least this old and no
# more than ENGAGE_WINDOW old — a scripted client has to wait, not just fire
# two requests back to back.
ENGAGE_MIN_AGE_SECONDS = 2
ENGAGE_WINDOW          = timedelta(minutes=30)

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


def _os(ua: str) -> str:
    # Order matters: iOS UAs say "like Mac OS X", Android UAs say "Linux".
    u = ua.lower()
    if 'iphone' in u or 'ipad' in u or 'ipod' in u:
        return 'iOS'
    if 'android' in u:
        return 'Android'
    if 'windows' in u:
        return 'Windows'
    if 'cros' in u:
        return 'ChromeOS'
    if 'macintosh' in u or 'mac os' in u:
        return 'macOS'
    if 'linux' in u or 'x11' in u:
        return 'Linux'
    return 'Other'


def _ua_hash(ua: str) -> str:
    """Short one-way hash of the user-agent: lets the dashboard see "many hits
    from one identical client" without keeping the UA string itself."""
    return hashlib.sha256(ua.encode('utf-8', 'ignore')).hexdigest()[:12]


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


def _as_int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _classify(request, ua: str, body: dict) -> tuple[str, str]:
    """(visit_class, reason). The owner check runs first so your own visits are
    never mistaken for bots. These are heuristics: they catch lazy scripts and
    headless browsers, not a careful bot that fakes everything — those end up
    as 'unverified' until (unless) the page sees a real interaction."""
    if request.COOKIES.get(IGNORE_COOKIE):
        return OWNER, 'ignore-cookie'

    # Logged in to /admin/ in this browser = you. Needs no per-device setup.
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated and user.is_staff:
        return OWNER, 'staff-session'

    if not ua:
        return BOT, 'no-ua'
    if _BOT_RE.search(ua):
        return BOT, 'ua-keyword'
    if body.get('webdriver') is True:          # navigator.webdriver, set by Selenium/Playwright
        return BOT, 'webdriver'
    if not request.META.get('HTTP_ACCEPT_LANGUAGE'):   # every real browser sends this
        return BOT, 'no-lang'
    if _as_int(body.get('sw')) == 0 or _as_int(body.get('sh')) == 0:   # headless: no screen
        return BOT, 'no-screen'

    return UNVERIFIED, ''


@csrf_exempt
@require_POST
def track_pageview(request):
    # Never let analytics break the site — every failure path is a quiet 204.
    ua = request.META.get('HTTP_USER_AGENT', '')

    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return HttpResponse(status=204)
    if not isinstance(body, dict):
        body = {}

    path = str(body.get('path') or '')[:255]
    if not path.startswith('/'):
        return HttpResponse(status=204)

    visit_class, reason = _classify(request, ua, body)
    ua_hash = _ua_hash(ua)

    if visit_class == BOT:
        # Bots don't keep cookies, so one stable pseudo-ID per user-agent stops
        # every hit from showing up as a brand-new "visitor", and no cookie is
        # issued to them.
        visitor_id = f'bot-{ua_hash}'
        is_new = False
        window = BOT_DEDUPE_SECONDS
        issue_cookie = False
    else:
        visitor_id = request.COOKIES.get(VISITOR_COOKIE)
        is_new = not visitor_id
        if is_new:
            visitor_id = uuid.uuid4().hex
        window = DEDUPE_SECONDS
        issue_cookie = is_new

    recent_cutoff = timezone.now() - timedelta(seconds=window)
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
                os=_os(ua),
                ua_hash=ua_hash,
                visit_class=visit_class,
                bot_reason=reason,
                # Only present if the site is ever put behind Cloudflare; blank otherwise.
                country=(request.META.get('HTTP_CF_IPCOUNTRY', '') or '')[:2].upper().replace('XX', ''),
                is_new_visitor=is_new,
            )
        except Exception:
            logger.exception('track_pageview: failed to record view for path=%s', path)

    response = HttpResponse(status=204)
    if issue_cookie:
        response.set_cookie(
            VISITOR_COOKIE, visitor_id,
            max_age=VISITOR_MAX_AGE, httponly=True, samesite='Lax', secure=True,
        )
    return response


@csrf_exempt
@require_POST
def track_engaged(request):
    """Second beacon, sent by the page only after a few seconds on it AND a real
    interaction (scroll / pointer / key / touch). Upgrades that visitor's recent
    'unverified' view of the path to 'genuine'. Needs the pv_vid cookie that the
    first request set, and a view at least ENGAGE_MIN_AGE_SECONDS old."""
    visitor_id = request.COOKIES.get(VISITOR_COOKIE)
    if not visitor_id:
        return HttpResponse(status=204)

    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return HttpResponse(status=204)
    path = str(body.get('path') or '')[:255] if isinstance(body, dict) else ''
    if not path.startswith('/'):
        return HttpResponse(status=204)

    now = timezone.now()
    try:
        PageView.objects.filter(
            visitor_id=visitor_id,
            path=path,
            visit_class=UNVERIFIED,
            created_at__gte=now - ENGAGE_WINDOW,
            created_at__lte=now - timedelta(seconds=ENGAGE_MIN_AGE_SECONDS),
        ).update(visit_class=GENUINE)
    except Exception:
        logger.exception('track_engaged: failed to upgrade view for path=%s', path)
    return HttpResponse(status=204)


@csrf_exempt
@require_POST
def track_optout(request):
    """Body {"off": true} marks this browser as the owner's (its visits are
    labelled 'owner' and not counted as visitors); {"off": false} undoes that.
    Called by the frontend when the URL has ?notrack=1 / ?notrack=0, and by the
    "exclude this browser" toggle on the admin dashboard. Being logged in to
    /admin/ in a browser has the same effect without this cookie."""
    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        body = {}

    off = bool(body.get('off', True)) if isinstance(body, dict) else True
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
