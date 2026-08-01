// ── curated, pre-verified documents shown in the doc picker ──
// No upload path — every doc here was scraped/parsed/tested offline before going live.
// See note.md "FINAL DECISION (2026-07-17): no upload button, curated docs only"

export const CURATED_DOCS = [
  {
    id:       'python-tutorial',
    title:    'The Python Tutorial',
    source:   'docs.python.org',
    sourceUrl: 'https://docs.python.org/3/tutorial/',
    hook:     'Cross-chapter reasoning — ask something that spans two chapters written in different vocabulary.',
    type:     'html',
    chapters: 16,
    startChapter: 'introduction',
    ready:    true,
  },
  {
    id:       'gdpr',
    title:    'GDPR',
    source:   'eur-lex.europa.eu',
    sourceUrl: 'https://eur-lex.europa.eu/eli/reg/2016/679/oj',
    hook:     'Clause-level legal retrieval — precise cross-clause inference across a dense regulatory text.',
    type:     'pdf',
    ready:    false,
  },
  {
    id:       'offer-letter',
    title:    'Offer Letter',
    source:   'sample document',
    sourceUrl: null,
    hook:     'Short, dense document — fast, reliable end-to-end demo for quick factual answers.',
    type:     'pdf',
    ready:    false,
  },
]

// chapter order + labels — must match Portfolio/api/core/doc_pages.py's
// DOC_PAGE_SOURCES['python-tutorial']['chapters'] (confirmed via curl against
// docs.python.org/3/tutorial/index.html, see note.md 2026-07-29)
export const DOC_CHAPTERS = {
  'python-tutorial': [
    { slug: 'appetite',       label: 'Whetting Your Appetite' },
    { slug: 'interpreter',    label: 'Using the Python Interpreter' },
    { slug: 'introduction',   label: 'An Informal Introduction' },
    { slug: 'controlflow',    label: 'More Control Flow Tools' },
    { slug: 'datastructures', label: 'Data Structures' },
    { slug: 'modules',        label: 'Modules' },
    { slug: 'inputoutput',    label: 'Input and Output' },
    { slug: 'errors',         label: 'Errors and Exceptions' },
    { slug: 'classes',        label: 'Classes' },
    { slug: 'stdlib',         label: 'Standard Library — Part 1' },
    { slug: 'stdlib2',        label: 'Standard Library — Part 2' },
    { slug: 'venv',           label: 'Virtual Environments and Packages' },
    { slug: 'whatnow',        label: 'What Now?' },
    { slug: 'interactive',    label: 'Interactive Input Editing' },
    { slug: 'floatingpoint',  label: 'Floating-Point Arithmetic' },
    { slug: 'appendix',       label: 'Appendix' },
  ],
}

export const SUGGESTED_QUESTIONS = {
  'python-tutorial': [
    "What's under heading 4.6?",
    'How do generators relate to the iterator protocol?',
    'What does `@dataclass` do?',
  ],
}
