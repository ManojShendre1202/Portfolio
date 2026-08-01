"""
doc_pages.py — serves the real rendered curated-doc HTML for the split-view
left pane.

Reuses the actual source page (already captured + id-stamped by
Readar_dev/html_parser/html_parser.py into data/html/raw/{doc}/{chapter}_ids.html)
rather than reinventing a theme:
    - injects <base href="..."> so all of docs.python.org's relative asset/
      link paths resolve correctly when served from our own domain
    - forces the site's own official dark stylesheet on unconditionally
      (it ships one already, gated behind `prefers-color-scheme: dark` —
      we just drop that guard instead of authoring our own dark palette)
    - injects a small script for citation highlight-by-dom_id (postMessage
      from the parent) and for intercepting clicks on same-tutorial chapter
      links so navigation stays inside our app instead of leaving it
"""

import re
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_GET

DATA_ROOT = Path(settings.BASE_DIR).parent / 'data' / 'html' / 'raw'

DOC_PAGE_SOURCES = {
    'python-tutorial': {
        'dir':       'python_tutorial',
        'base_href': 'https://docs.python.org/3/tutorial/',
        'chapters': [
            'appetite', 'interpreter', 'introduction', 'controlflow',
            'datastructures', 'modules', 'inputoutput', 'errors', 'classes',
            'stdlib', 'stdlib2', 'venv', 'whatnow', 'interactive',
            'floatingpoint', 'appendix',
        ],
    },
}

_DARK_MEDIA_GUARD = re.compile(r'\s*media="\(prefers-color-scheme:\s*dark\)"')
_HEAD_OPEN        = re.compile(r'(<head[^>]*>)', re.IGNORECASE)

_INJECTED_SCRIPT = """
<style>
.rd-flash { outline: 2px solid #e0a040 !important; background: rgba(224,160,64,0.16) !important;
            transition: background 0.4s, outline 0.4s; }
</style>
<script>
(function () {
  window.addEventListener('message', function (e) {
    if (!e.data || e.data.type !== 'highlight') return;
    document.querySelectorAll('.rd-flash').forEach(function (el) { el.classList.remove('rd-flash'); });
    var el = document.getElementById(e.data.id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.add('rd-flash');
    }
  });

  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href') || '';
    var m = href.match(/^([a-zA-Z0-9_]+)\\.html(#.*)?$/);
    if (!m) return;
    e.preventDefault();
    window.parent.postMessage({ type: 'navigate-chapter', chapter: m[1], hash: m[2] || '' }, '*');
  });
})();
</script>
"""


def _prepare_doc_page_html(raw_html: str, base_href: str) -> str:
    html = _DARK_MEDIA_GUARD.sub('', raw_html)
    html = _HEAD_OPEN.sub(r'\1<base href="' + base_href + '">', html, count=1)
    if '</body>' in html:
        html = html.replace('</body>', _INJECTED_SCRIPT + '</body>')
    else:
        html += _INJECTED_SCRIPT
    return html


@require_GET
@xframe_options_exempt
def getDocPage(request, doc_id, chapter):
    source = DOC_PAGE_SOURCES.get(doc_id)
    if not source or chapter not in source['chapters']:
        return HttpResponse('Not found', status=404)

    file_path = DATA_ROOT / source['dir'] / f'{chapter}_ids.html'
    if not file_path.exists():
        return HttpResponse('Not found', status=404)

    raw_html = file_path.read_text(encoding='utf-8')
    html     = _prepare_doc_page_html(raw_html, source['base_href'])
    return HttpResponse(html, content_type='text/html; charset=utf-8')
