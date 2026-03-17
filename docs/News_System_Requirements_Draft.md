# System Requirements: Personal News Intelligence Module

## 1. Purpose
This module is a callable subfunction of the broader portfolio platform whose job is to gather, normalize, analyze, condense, and present relevant news and information for the user. It is not a real-time trading engine and does not need to optimize for millisecond latency; it is a personal intelligence layer designed to help the user understand what matters across a defined portfolio watchlist plus selected global topics.

## 2. Core Objective
Given a portfolio of tickers, a set of global-interest topics, and optional personal content sources (newsletters, podcasts), the module will ingest source material on a scheduled basis, convert it into a common internal format, deduplicate overlapping coverage, identify which items matter to the user, extract company and macro signals, and generate a concise daily or on-demand briefing.

## 3. Functional Scope
*   **Inputs:** Portfolio watchlist of tickers, optional sector/theme watchlists, curated global news feeds, email newsletter sources (Gmail/IMAP), podcast feeds/transcripts, and user preferences.
*   **Outputs:** Structured summary object for the parent app, human-readable condensed briefing, grouped company-level updates, grouped macro themes, and traceability metadata.

## 4. Design Principles
*   Favor signal over volume.
*   Clearly separate ingestion from analysis.
*   Keep raw source material available for traceability.
*   Explain *why* an item was included in the final briefing.
*   Remain extensible for future source types.

## 5. High-Level Architecture
1.  **Source Registry:** Stores definitions for all approved feeds, APIs, inboxes, and filters.
2.  **Ingestion Layer:** Pulls content on a schedule.
3.  **Normalization Layer:** Converts incoming material into a unified `Content Record` schema.
4.  **Analysis Layer:** Performs deduplication, entity extraction, ticker mapping, relevance/novelty scoring, and event detection.
5.  **Briefing Layer:** Clusters related items into stories, prioritizes by user exposure, and generates the final narrative.

## 6. Core Services
*   **Service 1 (Source Management):** Manages user-approved RSS, newsletters, and podcasts.
*   **Service 2 (Ingestion):** Scheduled fetch jobs.
*   **Service 3 (Content Normalization):** Cleans HTML, extracts text, captures metadata.
*   **Service 4 (Entity & Relevance):** Identifies tickers/topics; scores against portfolio.
*   **Service 5 (Deduplication & Story Clustering):** Merges duplicate stories into an evolving thread.
*   **Service 6 (Summarization & Briefing):** Produces summaries via LLM based on clustered data.
*   **Service 7 (Storage):** Persists raw items, clean items, and clusters in Postgres.
*   **Service 8 (Parent Interface API):** Exposes endpoints for the Trust platform.

## 7. Phased Rollout Plan
*   **Phase 1 (Foundational MVP):** Source registry, RSS ingestion, normalized schema, ticker matching, basic deduplication, Postgres storage, and simple daily summary. Prove end-to-end ingestion.
*   **Phase 2 (Portfolio Relevance):** Entity extraction, company-to-ticker resolution, event tagging.
*   **Phase 3 (Newsletter Ingestion):** Gmail/IMAP integration, body parsing, link extraction.
*   **Phase 4 (Podcasts & Transcripts):** Audio text chunking and theme extraction.
*   **Phase 5 (Story Clustering):** Narrative detection across multiple sources over time.
*   **Phase 6 (User Controls):** Source weighting, topic preferences, briefing styles.
*   **Phase 7 (Advanced Intelligence):** SEC filing ingestion, source-quality scoring.

## 8. Recommended Stack
*   Python-based ingestion workers.
*   Postgres for storage (Vector/JSONB compatible).
*   Cron/Task Scheduler for jobs.
*   LLM-assisted summarization (applied *only after* deterministic extraction and deduplication).