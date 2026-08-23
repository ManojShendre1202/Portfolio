// docPageRender.js — turns the raw curated-doc HTML the backend hands back
// (see api/core/doc_pages.py's getDocPage — it's just a file server, no
// rendering logic) into the HTML actually fed to the split-view iframe via
// srcDoc:
//   - injects <base href="..."> so the source site's relative asset/link
//     paths resolve correctly when framed from our own domain
//   - drops the source site's prefers-color-scheme dark-mode guard so its
//     own dark stylesheet applies unconditionally, instead of us authoring
//     a separate dark palette
//   - injects the citation-highlight-by-dom_id listener (postMessage from
//     the parent) and the same-tutorial chapter-link interceptor so
//     navigation stays inside our app instead of leaving it
//   - CSS fallbacks for docs whose own styling doesn't reliably survive
//     being framed standalone (see MDX_FALLBACK_CSS below)

const DARK_MEDIA_GUARD = /\s*media="\(prefers-color-scheme:\s*dark\)"/g
const HEAD_OPEN        = /(<head[^>]*>)/i

// Fallback styling for Mintlify docs (langchain/langgraph/chroma): their
// headings/lists/paragraphs depend on a Tailwind bundle loaded from
// /mintlify-assets/... whose availability inside our split-view frame isn't
// reliable, and paragraphs render as <span data-as="p"> (no default block
// styling at all). These rules guarantee correct layout either way; scoped
// to .mdx-content so other docs' pages are untouched.
const MDX_FALLBACK_CSS = `
.mdx-content [data-as="p"] { display: block !important; margin: 1em 0 !important; }
.mdx-content h1, .mdx-content h2, .mdx-content h3, .mdx-content h4 {
  font-weight: 600 !important; margin: 1.4em 0 0.5em !important;
}
.mdx-content h1 { font-size: 1.875rem !important; }
.mdx-content h2 { font-size: 1.5rem !important; }
.mdx-content h3 { font-size: 1.25rem !important; }
.mdx-content h4 { font-size: 1.1rem !important; }
.mdx-content ul, .mdx-content ol { padding-left: 1.5em !important; margin: 0.75em 0 !important; }
.mdx-content ul { list-style-type: disc !important; }
.mdx-content ol { list-style-type: decimal !important; }
.mdx-content li { margin: 0.3em 0 !important; display: list-item !important; }

/* Mintlify callout boxes (Note/Tip/Warning) often lay out a run of related
   points as plain sibling <p> tags with NO <ul>/<li> at all — the little
   leading dot on the real site is pure decorative CSS from their bundle, not
   semantic markup, so there's no list-style fix for it. Approximate the same
   look: every paragraph after the callout's first (bold intro line) gets a
   leading bullet. */
[data-component-part="callout-content"] p:not(:first-child) {
  position: relative !important;
  padding-left: 1.1em !important;
}
[data-component-part="callout-content"] p:not(:first-child)::before {
  content: "•";
  position: absolute;
  left: 0;
  opacity: 0.7;
}

/* #content-container reserves padding-top for Mintlify's own fixed/sticky
   navbar (logo, search, nav links), which lives outside the scraped page
   content and never renders here — without this override that reserved
   space is just a huge blank gap at the top of the frame. */
#content-container { padding-top: 2rem !important; }

#rd-synth-title {
  font-size: 1.875rem !important;
  font-weight: 600 !important;
  margin: 0 0 1rem !important;
  color: inherit;
}
`

const INJECTED = `
<style>
.rd-flash { outline: 2px solid #e0a040 !important; background: rgba(224,160,64,0.16) !important;
            transition: background 0.4s, outline 0.4s; }
${MDX_FALLBACK_CSS}
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
`

// Mintlify pages carry their title only as a data-page-title="..." attribute
// (normally rendered into a real <h1> by their client-side JS, which we
// don't run) — none of the scraped pages have a static <h1> at all. Insert
// one ourselves from that attribute so the page doesn't open on a blank gap
// with no heading.
function injectMissingMintlifyTitle(html) {
  if (/<h1[^>]*id=["']page-title["']/.test(html)) return html
  const match = html.match(/data-page-title="([^"]*)"/)
  if (!match) return html
  const title = match[1].replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&')
  const doc = new DOMParser().parseFromString(html, 'text/html')
  const anchor = doc.querySelector('[data-page-title]')
  if (!anchor?.parentNode) return html
  const h1 = doc.createElement('h1')
  h1.id = 'rd-synth-title'
  h1.textContent = title
  anchor.parentNode.insertBefore(h1, anchor)
  return '<!DOCTYPE html>' + doc.documentElement.outerHTML
}

export function prepareDocPageHtml(rawHtml, baseHref) {
  let html = rawHtml.replace(DARK_MEDIA_GUARD, '')
  html = html.replace(HEAD_OPEN, `$1<base href="${baseHref}">`)
  html = injectMissingMintlifyTitle(html)
  return html.includes('</body>')
    ? html.replace('</body>', INJECTED + '</body>')
    : html + INJECTED
}
