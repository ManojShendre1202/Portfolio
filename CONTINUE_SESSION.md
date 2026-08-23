# Readar — Continuation Notes

Handoff doc for picking this work back up in a new session. This file is
about **current state and what's next**, not full history — see
`rag_retrieval_debugging_summary.txt` for the pre-2026-08-23 retrieval
debugging history (now superseded — every issue it flagged as open was
resolved this session, see below).

## TOP PRIORITY FOR NEXT SESSION: frontend — show all 10 docs + better viz/chat

This session expanded the corpus from 1 doc to 10 and fixed the
ingestion/retrieval pipeline end to end (see "What changed" below), but the
**frontend still only knows about 1 doc**. Two files need updating, plus a
vaguer "make chat screen better" ask that needs scoping out with the user
before touching anything:

1. **`frontend/src/pages/readar/curatedDocs.js`** — `CURATED_DOCS` only has
   `python-tutorial` (`ready: true`) plus two unrelated placeholder PDF docs
   (`gdpr`, `offer-letter`, both `ready: false`, not part of this doc-expansion
   effort). Needs one new entry per new doc (`pytorch`, `opencv`, `numpy`,
   `langchain`, `langgraph`, `docker`, `git`, `postgresql`, `chroma`) —
   `id`/`title`/`source`/`sourceUrl`/`hook`/`type`/`chapters`/`startChapter`/
   `ready`. `DOC_CHAPTERS` and `SUGGESTED_QUESTIONS` also only have
   `python-tutorial` entries — need the other 9 filled in too (chapter
   slug→label lists, a few good demo questions per doc).

2. **`Portfolio/api/core/doc_pages.py`** — `DOC_PAGE_SOURCES` (backs the
   split-view left pane, which renders the actual source HTML with citation
   highlight-by-dom_id) also only has `python-tutorial`. Needs an entry per
   new doc: `dir` (matches `documents/raw/<doc>/`), `base_href`, `chapters`
   (list of chapter slugs, must match the `.html` filenames on disk).
   **Important nuance for whoever picks this up**: `base_href` here assumes
   one flat base URL per doc, which works for `pytorch`/`numpy`/`git`/
   `postgresql` (flat `base_url + slug + suffix` pattern in
   `Readar_dev/html_parser/fetch_doc.py`'s `DOC_CONFIGS`) but **not** for
   `opencv`/`docker`/`chroma`, which used the `"pages"` config form (each
   page has its own full relative path, e.g. OpenCV's
   `db/deb/tutorial_display_image.html`). A single doc-level `base_href`
   won't resolve those docs' relative asset/link paths correctly — this
   needs a per-chapter `base_href` (or reuse the exact relative path stored
   in `fetch_doc.py`'s `DOC_CONFIGS[doc]["pages"]`) rather than the current
   single-string-per-doc field.

3. **"Make chat screen even better"** — no spec given yet, discuss with the
   user first before implementing anything.

## What changed this session (2026-08-23)

### 1. Corpus expanded from 1 doc to 10, ingestion pipeline generalized

Downloaded, parsed, and ingested 9 new docs — final set: `python_tutorial`
(existing), `pytorch`, `opencv`, `numpy`, `langchain`, `langgraph`, `docker`,
`git`, `postgresql`, `chroma`. (Originally planned pandas/scikit-learn/
Kubernetes were dropped in favor of LangChain+LangGraph — more relevant to
demoing this RAG app's own domain — and Chroma was added as the vector-DB
entry.)

Both pipeline scripts, previously hardcoded to `python_tutorial` only, are
now doc-agnostic:
- `Readar_dev/html_parser/fetch_doc.py` — `DOC_CONFIGS` dict per doc (flat
  `base_url+slug+suffix` form, or `"pages"` form for sites with
  per-page/unpredictable paths like Doxygen). `fetch_doc(doc_name)` to run.
- `Readar_dev/html_parser/html_parser.py` — `parse_doc(doc_name, ...)`,
  auto-discovers chapter files if no explicit list given. Same CLI pattern.

Real generator-level parsing bugs found and fixed (all generic — reusable
for any future doc using these generators, not hardcoded to one site):
- Sphinx `a.headerlink` anchors leaking `#`/`¶` into every heading (and thus
  into every node under it, via heading-fold)
- sphinx-gallery boilerplate (PyTorch tutorials, scikit-learn-style):
  "go to end to download", timing footer, download-links, series breadcrumb
- PyData Sphinx Theme secondary sidebar (NumPy, pandas, scikit-learn, ...)
  leaking a related-projects list into content
- Doxygen (OpenCV): code blocks are `<div class="fragment">`/`<div
  class="line">`, not `<pre>` — zero code nodes were being extracted before
  this fix. Also: multi-language tutorial pages embed C++/Java/Python
  variants simultaneously in the DOM (JS-toggled tabs, all present at once)
  — now tagged with `node["lang"]` via `detect_lang()` rather than dropped
  or blindly mixed together. Doxygen title-bar logo table and
  Prev/Next-Tutorial nav also stripped.
- Mintlify (LangChain, LangGraph, Chroma): paragraphs render as
  `<span data-as="p">` instead of real `<p>` — was silently losing almost
  all prose (`install.html` parsed to 0 paragraph nodes before the fix).
  Also stripped the "Edit this page on GitHub"/MCP-promo `.source-links`
  callout.
- DocBook (PostgreSQL): standard Prev/Up/Next `table[summary=...]` nav and
  `a.id_link` heading anchors stripped; `#docComments` feedback widget too.
- **Table support added** — `CONTENT_TAGS` had no `<table>` handling at all
  before this session; real content (e.g. NumPy's ~100-row MATLAB↔NumPy
  command-equivalence table) was being silently dropped entirely. Now one
  node per row (`type: "table_row"`), not one giant node per table.
- List-nested code blocks (Doxygen "Code at glance" bullets, but also found
  in the *existing* `python_tutorial` data — 2 pages had this) were being
  flattened into plain list text, losing all code formatting. Now pulled
  out into their own properly-formatted code nodes.
- Zero-width space/joiner (`​`/`‌`) stripped from `clean_text` —
  found leaking into table cells from copy-pasted source content.
- `fetch_doc.py` encoding bug: `resp.encoding = resp.apparent_encoding`
  (chardet's guess) was overriding a page's own correct `<meta charset>`
  declaration, producing real mojibake on a NumPy page. Now trusts the
  declared charset first, falls back to chardet only if none is declared.

### 2. Ingestion-time code-chunking fix (the item flagged as top-priority
last session) — implemented, tested, revised

Original fix (`Readar_dev/RAG/ingest.py`, `merge_code_into_anchor()`):
folds every `code` node into the node immediately preceding it in document
order, instead of leaving code as an independent node with its own
embedding. This was the actual root cause of the graph's known weak
spot — the graph has no document-order edges (confirmed: fully connected,
`C(n,2)` edges, pure cosine similarity), so a code block's fate at
retrieval time depended entirely on whether it happened to embed close to
its own prose, which it often doesn't.

**Revised mid-session** based on user feedback: code is now stored as
`node["code_blocks"]` (a list of fenced strings), **excluded from the
embedded `text` field**, not concatenated into it. Reasoning, confirmed by
a real measured case: concatenating code into the embedded text lets code
content skew what a chunk matches on — a LangChain page repeats the same
`create_agent(...)` example once per LLM provider tab (openai/anthropic/
google_genai/...) as consecutive code nodes; textually merging them
produced one bloated, code-dominated embedding that out-competed
everything else for an unrelated-strength query, single-handedly filling
the 6000-char context budget. Keeping code out of the embedded text fixed
this — `doc_retrieval.py`'s `build_context()` still appends `code_blocks`
into what's shown to the LLM once a chunk is retrieved, so retrieval
*ranking* is judged on prose meaning only, while the LLM still sees the
code. (Note: those per-provider blocks are NOT redundant duplicates —
each has a different provider/model string — correctly flagged by the user
mid-session; no deduplication was needed or applied.)

Inline `` `code` `` spans (not full `<pre>` blocks) are explicitly left
untouched — still flattened into surrounding prose with no special
marking. Only block-level code was in scope.

All 10 docs re-ingested twice this session (once with the original merge,
once after the code_blocks revision) — final state reflects the revised
version. `GRAPH_PATHS` in `doc_retrieval.py` updated with all 10 doc_ids.

### 3. Retrieval validated, reranker removed

Ran 20 real queries (2 per doc, mix of Simple/Moderate/Complex) through the
full pipeline twice — once with reranking, once retrieval-only
(`READAR_SKIP_RERANKER` mode) — plus explicit inspection of
`keyword_seed_candidates()`'s extracted keyphrases per query. Findings:
- 20/20 answerable from retrieved context on manual inspection, code
  correctly attached in all 20 (`has_code_fence=True` throughout)
- Retrieval-only: ~1.0–1.9s total per query, node counts 9–35 (median
  ~19–20), ~1471 tokens average context
- Reranking added 1–7.4s per query (60–90% of total latency when it ran —
  it self-skips when candidates ≤15) for a reordering that measurably
  wasn't needed

**Reranker fully removed** from the codebase as a result: `rerank_nodes()`,
`_reranker`/`CrossEncoder` load, `RERANK_TOP_N` deleted from
`doc_retrieval.py`; `readar_chat_engine.py`'s `_run_retrieval` now returns a
4-tuple (no `reranked` count) and goes straight from `retrieve_subgraph` to
`build_context`; `debug_retrieval.py` simplified to match (also fixed a
pre-existing bug there: `doc_id=doc_id` referenced an undefined lowercase
variable). Verbose per-candidate `logger.info()` diagnostic loops in
`keyword_seed_candidates()`/`retrieve_subgraph()` dropped to `logger.debug`
— production logs now show one summary line per stage instead of dumping
every candidate.

## How to test changes

`backend/RAG/Query/debug_retrieval.py` — standalone REPL, no Gemini/DB/
WebSocket. Run from anywhere:
```
python backend/RAG/Query/debug_retrieval.py
```
Hardcoded to `DOC_ID = 'python-tutorial'` at the top — edit that constant to
test a different doc_id (all 10 are registered in `doc_retrieval.GRAPH_PATHS`).

To re-run ingestion for all docs after a parser/ingest change:
```python
import glob, os
from ingest import ingest
JSON_FOLDER = r"...\Portfolio\documents\parsed"
GRAPH_FOLDER = r"...\Portfolio\documents\graph_output"
for path in sorted(glob.glob(os.path.join(JSON_FOLDER, "*.json"))):
    ingest(path, graph_folder=GRAPH_FOLDER)
```
Run with `PYTHONIOENCODING=utf-8` set — a stdout `→` character in
`save_graph()`'s print crashes on the default Windows console codepage
otherwise (harmless — the file is already written by the time it crashes —
but it aborts the loop before later docs get processed).

## Dependencies

`requirements.txt` currently has `spacy==3.8.14` (+ separate model download:
`python -m spacy download en_core_web_sm`). `llama-cpp-python` was tried and
removed — not a dependency anymore, but if reintroducing local-LLM-based
extraction, note it needs the prebuilt CPU wheel index on Windows (plain
`pip install` fails without a C++ compiler):
```
pip install llama-cpp-python --prefer-binary --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```
