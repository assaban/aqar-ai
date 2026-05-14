# Feature: Deferred Items and Pipeline Controls

> **Sprint:** Backlog cleanup
> **Branch:** `feature/AQAR-032-deferred-items`
> **Author:** Aqar.ai Team
> **Date:** 2026-05-13
> **Status:** In Progress

---

## Scope

This branch addresses all deferred items from Sprints 3-7 plus pipeline operational controls:

### 1. English UI (AQAR-081/082/083)
- Switch all French UI text to English (primary language)
- Prepare i18n structure for Spanish later

### 2. Pipeline Admin Controls (Operations)
- Admin endpoints to retry, cancel, and restart stuck jobs
- GET /api/v1/pipeline/admin/stuck: find and list stuck jobs
- POST /api/v1/pipeline/admin/retry/{job_id}: retry a specific job
- POST /api/v1/pipeline/admin/retry-all-stuck: batch retry stuck jobs
- POST /api/v1/pipeline/admin/cancel/{job_id}: cancel a job
- Pipeline health diagnostics endpoint

### 3. WER Benchmark Framework (AQAR-032/033/034)
- Golden dataset structure with manual transcriptions
- WER calculation utility
- make test-ml runs benchmarks

### 4. LLM Extraction Benchmark Framework (AQAR-045/046/047)
- Golden extraction dataset structure
- Field-level accuracy scoring utility
- Benchmark reporting

---

*This document follows the SDLC Analyse, Design, Implement, Test, DevOps cycle.*
