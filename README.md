<div align="center">

# Portfolio & Readar

**[manojshendre.com](https://manojshendre.com)**

Personal portfolio, plus **Readar** — a graph-based Retrieval-Augmented Generation (RAG) chat
engine built from scratch and served live at [`/readar/`](https://manojshendre.com/readar/).

[![React](https://img.shields.io/badge/React-19-149ECA?logo=react&logoColor=white)](https://react.dev)
[![Django](https://img.shields.io/badge/Django-5-092E20?logo=django&logoColor=white)](https://www.djangoproject.com)
[![Gemini](https://img.shields.io/badge/Gemini-API-8E75B2?logo=googlegemini&logoColor=white)](https://ai.google.dev)
[![Docker](https://img.shields.io/badge/Docker-Deployed-2496ED?logo=docker&logoColor=white)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-Personal_Project-lightgrey)](#status)

</div>

---

## Contents

- [Overview](#overview)
- [Readar — RAG Architecture](#readar--rag-architecture)
- [Tech Stack](#tech-stack)
- [Repository Layout](#repository-layout)
- [Getting Started](#getting-started)
- [Status](#status)

---

## Overview

This repository powers one Django backend serving two applications:

| App | Route | Description |
|---|---|---|
| **Portfolio** | `/` | A React + Vite single-page site — professional experience, technical skills, and project deep-dives. |
| **Readar** | `/readar/` | A from-scratch RAG chatbot. Pick a curated document, ask it anything, and get streamed answers with clickable citations that scroll to and highlight the exact source paragraph. |

---

## Readar — RAG Architecture

Readar is not a wrapper around a vector database or an off-the-shelf RAG framework — the
retrieval graph, hop traversal, reranking, and memory system are all implemented directly.

```
Document ─▶ Parse (DOM-aware) ─▶ Embed (nomic-embed-text-v1.5)
                                        │
                                        ▼
                          Cosine-Similarity Node Graph
                                        │
Question ─▶ Embed ─▶ BFS Hop Retrieval ─▶ Cross-Encoder Rerank
                                        │
                                        ▼
                        Gemini (streamed) ─▶ Cited Answer
                                        │
                                        ▼
                   Hidden turn summary ─▶ Per-session memory graph
```

**Key design decisions:**

- **Similarity graph, not entity graph** — nodes are paragraphs, edges are cosine similarity
  above a tuned threshold. Coreferences resolve naturally without an entity-extraction pass.
- **Two-stage retrieval** — a cheap wide BFS hop-traversal net, then a cross-encoder reranker
  scores candidates against the literal query. Measured **~75–85% token reduction** with no
  accuracy loss across stress tests.
- **Retrieval-augmented memory, not history replay** — each turn's hidden summary is embedded
  into its own small per-session graph, so cost stays flat whether it's turn 2 or turn 30.
- **Concurrency-hardened** — blocking embed/rerank/Gemini calls run off the shared event loop
  in dedicated executors; a proactive rate guard returns a friendly message instead of a raw
  exception under real concurrent load.

Full technical writeup is on the [live site's project section](https://manojshendre.com/#readar).

---

## Tech Stack

<table>
<tr><td><strong>Frontend</strong></td><td>React 19 · Vite · Framer Motion · React Router</td></tr>
<tr><td><strong>Backend</strong></td><td>Django 5 · Waitress · WebSockets · PostgreSQL (Supabase)</td></tr>
<tr><td><strong>RAG / ML</strong></td><td>nomic-embed-text-v1.5 · cross-encoder/ms-marco-MiniLM-L-6-v2 · Google Gemini API</td></tr>
<tr><td><strong>Infra</strong></td><td>Docker · Nginx · Oracle Cloud Infrastructure (OCI, ARM)</td></tr>
</table>

---

## Repository Layout

```
api/              Django app — Readar session/turn models, curated-doc page serving
backend/          Django settings, ASGI/WSGI entry points, RAG pipeline (backend/RAG/)
workflow/         WebSocket chat server + worker pool engine
frontend/         React + Vite SPA (portfolio + Readar UI)
documents/        Curated document source HTML + prebuilt retrieval graph (.pkl)
config/           Workflow pipeline stage config
```

---

## Getting Started

### Backend

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python server.py               # Django app (Waitress)
```

In a second terminal, start the chat WebSocket server + worker pool — required for Readar's
chat to function, since `server.py` only serves the Django app:

```bash
python -m workflow.main
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment

A local `backend/.env` (not committed) is required, at minimum:

```
PROD=DEV
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://localhost:5173
GEMINI_API_KEY=...
# + database credentials
```

---

## Status

Readar is a temporary, non-commercial interview/portfolio demo — curated documents only, no
live upload path. It will be taken down once its purpose (the active job search) concludes.
