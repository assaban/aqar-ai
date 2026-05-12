# Feature: AQAR-017: YouTube Channel Discovery

> **Sprint:** 2: Video Ingestion Pipeline
> **Branch:** `feature/AQAR-017-youtube-discovery`
> **Author:** Aqar.ai Team
> **Date:** 2026-05-12
> **Status:** In Progress

---

## 1. User Story

> As a system, I want to automatically discover new real estate videos from configured YouTube channels so that new listings are captured without manual intervention.

**Priority:** P0 (MVP blocker)
**Story Points:** 5
**Related Issues:** AQAR-017, AQAR-018, AQAR-019

## 2. Analysis

### Problem Statement

Real estate agents in the Tangier-Tetouan region post property tour videos on YouTube daily. Currently, there is no automated way to discover these videos. The system needs to periodically scan configured channels, identify new videos, extract metadata, and queue them for processing through the AI pipeline.

### Current State

- The Celery beat scheduler is configured with a `discover-new-videos` task running every 6 hours (Sprint 1).
- The `ProcessingJob` model and status tracking exist in the database.
- The pipeline submit endpoint (`POST /api/v1/pipeline/submit`) exists but only accepts manual URL submissions.
- No actual ingestion logic exists yet; the `stages/` directory is empty.

### Constraints & Assumptions

- YouTube API quota: 10,000 units/day on the free tier. A channel list request costs 1 unit, a video list costs 1 unit. This limits us to roughly 5,000 channel checks per day.
- We use `yt-dlp` for metadata extraction (no API key needed) and fall back to the YouTube Data API v3 only when needed.
- Channels are configured via a YAML file, not hardcoded.
- Videos longer than `MAX_VIDEO_DURATION_MINUTES` (default 30) are skipped to avoid processing hour-long vlogs.
- We assume channel owners post in Arabic/Darija and include property-related content.

## 3. Design

### Approach

The discovery system uses `yt-dlp` as the primary metadata source. This avoids YouTube API quota limits entirely for the MVP. `yt-dlp` can extract channel video listings, video metadata, and thumbnails without authentication.

The design follows a two-phase approach:
1. **Discovery phase:** Scan each channel, collect video URLs and metadata.
2. **Filtering phase:** Deduplicate against existing `VideoSource` entries, skip too-long videos, and create new records with `PENDING` processing jobs.

### Architecture Impact

```
packages/pipeline/aqar_pipeline/
├── stages/
│   ├── __init__.py              ← MODIFIED (export tasks)
│   └── ingestion.py             ← NEW (core discovery logic)
├── config/
│   └── channels.yml             ← NEW (channel configuration)
├── utils/
│   └── youtube.py               ← NEW (yt-dlp wrapper)
└── celery_app.py                ← MODIFIED (import tasks)

apps/api/app/routers/
└── pipeline.py                  ← MODIFIED (dispatch Celery task)

packages/pipeline/tests/unit/
└── test_ingestion.py            ← NEW
```

### Key Design Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| Metadata source | YouTube Data API v3, yt-dlp, Scrapy | yt-dlp | No API key needed, no quota limits, extracts all required metadata. Battle-tested library. |
| Channel config | Database table, env vars, YAML file | YAML file | Version-controlled, easy to review changes, simple for solo developer. Can migrate to DB later. |
| Scheduling | Cron job, Celery beat, APScheduler | Celery beat | Already configured in Sprint 1. Reliable, persistent, integrates with existing Redis broker. |
| Dedup strategy | URL string match, platform+external_id | platform+external_id | Handles URL variations (youtu.be, youtube.com, with/without params). |

### Data Flow

```
Celery Beat (every 6h)
    │
    ▼
discover_videos(region="tangier-tetouan")
    │
    ├── Read channels.yml
    │
    ├── For each channel:
    │   ├── yt-dlp: fetch latest N videos
    │   ├── Filter: skip if already in DB (by external_id)
    │   ├── Filter: skip if duration > MAX_VIDEO_DURATION_MINUTES
    │   └── Create VideoSource + ProcessingJob (status=PENDING)
    │
    └── Log summary: X new videos discovered, Y skipped
```

## 4. Acceptance Criteria

- [ ] Celery beat task runs every 6 hours to check configured channels
- [ ] New videos (not already in DB) are added to the VideoSource table
- [ ] Video metadata (title, duration, published_at, thumbnail) is captured
- [ ] Videos longer than MAX_VIDEO_DURATION_MINUTES are skipped
- [ ] Channel list is configurable via YAML file
- [ ] Duplicate URLs are detected and skipped (by platform + external_id)
- [ ] ProcessingJob created with status=PENDING for each new video
- [ ] Unit tests cover: channel parsing, dedup logic, duration filtering

## 5. Test Plan

- **Unit Tests:** Channel YAML parsing, YouTube URL/ID extraction, duration filtering logic, dedup check, metadata mapping.
- **Integration Tests:** Full discovery flow with mocked yt-dlp responses against test database.
- **Manual Verification:** Add a real Tangier real estate YouTube channel to channels.yml, run `discover_videos` task manually, verify VideoSource records appear in DB.

## 6. Notes for Thesis

- The choice of yt-dlp over the YouTube Data API is significant for reproducibility. API quotas would limit the system to ~5,000 checks/day, while yt-dlp has no such limit.
- Channel discovery rates, false positive rates (non-property videos), and metadata completeness should be measured for the evaluation chapter.
- The YAML-based channel configuration enables easy A/B testing of different channel sets for thesis experiments.

---

*This document follows the SDLC Analyse → Design → Implement → Test → DevOps cycle.*
