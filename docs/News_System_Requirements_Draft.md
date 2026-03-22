# System Requirements: Personal News Intelligence Module (Decoupled Microservice)

## 1. Purpose
This module is an independent, heavily-decoupled intelligence layer designed to gather, normalize, analyze, condense, and present relevant news for the user. It is separated from the core 'Trust' financial engine to prevent code bloat, ensure high performance of the desktop app, and allow asynchronous, heavy LLM processing without freezing the primary user interface.

## 2. Core Objective
Given a portfolio of tickers (pulled via API from Trust) and global-interest topics, the module will ingest source material on a scheduled basis, convert it into a common internal format, deduplicate overlapping coverage, extract signals, and generate a concise daily briefing.

## 3. Functional Scope
*   **Inputs:** Portfolio watchlist of tickers, curated global news feeds (RSS/APIs), email newsletter sources, and user preferences.
*   **Outputs:** Structured JSON summary object exposed via a dedicated REST API endpoint.

## 4. Architectural Design Principles (The Scotty Doctrine)
*   **Total Decoupling:** The Intelligence Engine runs as a standalone backend process (e.g., on port 8001 or a remote cloud server).
*   **Asynchronous Processing:** Heavy tasks (LLM summarization, web scraping) operate entirely in the background.
*   **Dumb Client, Smart Server:** The Trust UI (React) does zero processing. It simply fetches the pre-compiled briefing JSON and renders it.
*   **Traceability:** Raw source material remains available to explain *why* an item was included.

## 5. High-Level Architecture
1.  **Independent Ingestion Daemon:** Python-based scheduled workers pulling RSS/API data.
2.  **Processing Pipeline:** Normalization -> Ticker Matching -> Deduplication -> LLM Summarization.
3.  **Local Datastore (Isolated):** A dedicated database (initially SQLite, scalable to Postgres/Vector DB) strictly for news caching.
4.  **Briefing API:** A lightweight FastAPI layer exposing `GET /api/briefing/latest`.
5.  **Trust UI Integration:** A new React component in `projects/trust/src/components/NewsView.jsx` that consumes the Briefing API.

## 6. Phased Rollout Plan
*   **Phase 1 (Decoupled MVP):** Scaffold independent project (`projects/intelligence`). Basic RSS ingestion, SQLite storage, deterministic ticker matching, and a simple FastAPI endpoint. Wire Trust UI to read from this endpoint.
*   **Phase 2 (The LLM Layer):** Introduce AI summarization over the deduplicated feeds to generate the 'Morning Briefing' narrative.
*   **Phase 3 (Portfolio Sync):** Intelligence Engine dynamically polls the Trust API (`GET /api/holdings`) to automatically update its watchlist.
*   **Phase 4 (Advanced Ingestion):** Gmail/IMAP integration for newsletters, SEC filings.

## 7. Recommended Stack
*   **Backend:** Python 3.11+, FastAPI (Port 8001), APScheduler/Celery for background jobs.
*   **Storage:** SQLite (MVP) migrating to Postgres if Vector search becomes necessary.
*   **Frontend (Inside Trust):** React 18, utilizing existing Nivo charts and UI components.