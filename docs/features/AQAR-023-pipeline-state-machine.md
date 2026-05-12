# Feature: AQAR-023/024/028: Pipeline State Machine and Celery Dispatch

> **Sprint:** 2: Video Ingestion Pipeline
> **Branch:** `feature/AQAR-023-pipeline-state-machine`
> **Author:** Aqar.ai Team
> **Date:** 2026-05-12
> **Status:** In Progress

---

## 1. User Stories

### US-008: Processing Job Tracking (AQAR-023, AQAR-024)

> As an operator, I want to track the status and timing of each pipeline stage so that I can monitor throughput and debug failures.

### US-009: Pipeline Submit API (AQAR-028)

> As a user, I want the submit endpoint to actually dispatch a Celery task so that submitted videos are processed automatically.

**Priority:** P0 (AQAR-023), P1 (AQAR-024, AQAR-028)
**Story Points:** 6 (combined)
**Related Issues:** AQAR-023, AQAR-024, AQAR-028

## 2. Analysis

### Problem Statement

Three loose ends remain in Sprint 2:

1. **AQAR-023 (State Machine):** The ProcessingJob model has status fields, but there is no centralized state machine to enforce valid transitions (e.g. PENDING -> INGESTING -> TRANSCRIBING). Each stage currently manages status updates independently, which risks inconsistent states.

2. **AQAR-024 (Stage Timing):** Individual stages record timing in their own way. We need a consistent utility for starting/stopping timers and storing per-stage durations in the `stage_timings` JSONB field.

3. **AQAR-028 (Celery Dispatch):** The API endpoint `POST /api/v1/pipeline/submit` creates records but has a `TODO` comment where it should dispatch the Celery task. The ingestion task also does not chain to the audio extraction task after completion.

### Current State

- `ProcessingJob` has `status`, `stage_timings`, and error fields, but no state machine validation.
- `audio_extraction.py` has inline `_update_job_success` and `_update_job_failure` helpers.
- `pipeline.py` router has `# TODO: Dispatch Celery task` on line 72.
- `ingest_video` returns a dict but does not chain to `extract_audio`.

## 3. Design

### Approach

1. **State Machine** (`utils/job_manager.py`): A centralized `JobManager` class that wraps all ProcessingJob state transitions, timing, and error recording. All stages use this instead of inline DB updates.

2. **Stage Timing**: Integrated into the JobManager via `start_stage()` and `complete_stage()` methods that automatically record elapsed time.

3. **Celery Dispatch + Chaining**: The API sends `ingest_video.delay(url)`. After ingestion completes, it chains to `extract_audio.delay(video_source_id)`. This creates a progressive pipeline where each stage triggers the next.

### Architecture Impact

```
packages/pipeline/aqar_pipeline/
├── utils/
│   └── job_manager.py           < NEW (state machine + timing)
├── stages/
│   ├── ingestion.py             < MODIFIED (use JobManager, chain to extract_audio)
│   └── audio_extraction.py      < MODIFIED (use JobManager)

apps/api/app/
├── routers/
│   └── pipeline.py              < MODIFIED (dispatch Celery task)
└── schemas/__init__.py          < MODIFIED (add stage_timings to response)

packages/pipeline/tests/unit/
└── test_job_manager.py          < NEW
```

### Key Design Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| State machine style | Finite state machine library, enum transitions, custom class | Custom JobManager class | Lightweight, no extra dependency, easy to test. A full FSM library is overkill for 7 states. |
| Task chaining | Celery chain primitive, manual `.delay()` at end of task, signals | Manual `.delay()` at task end | Simpler to debug than Celery chains. Each task decides whether to trigger the next, allowing conditional logic (e.g. skip transcription if audio fails). |
| Timing granularity | Per-task, per-stage, per-function | Per-stage | Maps cleanly to the pipeline stages. Stored in `stage_timings` JSONB for easy querying and thesis metrics. |

### Data Flow

```
POST /api/v1/pipeline/submit
    │
    ├── Create VideoSource + ProcessingJob
    ├── Dispatch: ingest_video.delay(video_url)
    └── Return job_id
         │
         ▼
ingest_video(video_url)
    │
    ├── JobManager.start_stage("ingestion")
    ├── Fetch metadata, create records
    ├── JobManager.complete_stage("ingestion")
    └── Chain: extract_audio.delay(video_source_id)
         │
         ▼
extract_audio(video_source_id)
    │
    ├── JobManager.start_stage("audio_extraction")
    ├── Download + convert WAV
    ├── JobManager.complete_stage("audio_extraction")
    └── [Sprint 3: chain to transcribe_audio]
```

## 4. Acceptance Criteria

- [ ] ProcessingJob status transitions are validated (no invalid jumps)
- [ ] Stage timings recorded in stage_timings JSONB field
- [ ] POST /api/v1/pipeline/submit dispatches ingest_video Celery task
- [ ] ingest_video chains to extract_audio on success
- [ ] All stages use JobManager for status updates
- [ ] Invalid state transitions raise clear errors
- [ ] Unit tests for JobManager: transitions, timing, error recording

## 5. Test Plan

- **Unit Tests:** Valid/invalid state transitions, timing recording, error capture, transition matrix coverage.
- **Integration Tests:** Submit a URL via API, verify job transitions through PENDING -> INGESTING -> TRANSCRIBING.
- **Manual Verification:** `curl -X POST localhost:8000/api/v1/pipeline/submit -d '{"url":"..."}' `, then poll `/pipeline/status/{id}` to see stage progression.

## 6. Notes for Thesis

- The state machine pattern is a classic SDLC design pattern worth documenting in the architecture chapter.
- Stage timing data is critical for the performance evaluation chapter. Average times per stage across 50+ videos will quantify the pipeline's throughput.
- The Celery chaining approach (task A triggers task B on success) creates a loosely coupled pipeline that is easy to extend with new stages.

---

*This document follows the SDLC Analyse, Design, Implement, Test, DevOps cycle.*
