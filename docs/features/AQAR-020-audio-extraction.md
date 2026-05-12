# Feature: AQAR-020: Audio Extraction

> **Sprint:** 2: Video Ingestion Pipeline
> **Branch:** `feature/AQAR-020-audio-extraction`
> **Author:** Aqar.ai Team
> **Date:** 2026-05-12
> **Status:** In Progress

---

## 1. User Story

> As a pipeline stage, I want to download video audio in WAV format so that Whisper can transcribe it.

**Priority:** P0 (MVP blocker)
**Story Points:** 5
**Related Issues:** AQAR-020, AQAR-021, AQAR-022

## 2. Analysis

### Problem Statement

After a video is discovered and stored in the database (AQAR-017), the next step is to download its audio track. Whisper requires audio input (ideally WAV at 16kHz mono) to perform speech-to-text. We need a reliable download and conversion pipeline that handles YouTube's various formats and gracefully manages disk space.

### Current State

- VideoSource records exist in the database with status PENDING.
- yt-dlp is already installed in the worker container (with FFmpeg).
- The ingestion stage creates ProcessingJob records but does not yet trigger audio download.
- The download directory `/tmp/aqar/downloads` is configured as a Docker volume.

### Constraints & Assumptions

- Whisper performs best with WAV 16kHz mono audio. Other formats work but with potential quality loss.
- Average video is 5-15 minutes. At 16kHz mono WAV, that is roughly 10-30 MB per file.
- Disk space: the worker volume should be cleaned after successful transcription.
- YouTube may rate-limit downloads. We use yt-dlp's built-in retry/backoff.
- Some videos may be age-restricted or geo-blocked. These should fail gracefully.

## 3. Design

### Approach

The audio extraction is a Celery task that:
1. Receives a `video_source_id` from the ingestion stage.
2. Uses yt-dlp to download the best audio stream.
3. Converts to WAV 16kHz mono via FFmpeg (yt-dlp handles this with postprocessors).
4. Stores the audio file at a predictable path: `{DOWNLOAD_PATH}/{video_id}.wav`.
5. Updates the ProcessingJob status to `TRANSCRIBING` (ready for next stage).
6. On failure, updates status to `FAILED` with error details.

After successful transcription (Sprint 3), a cleanup task deletes the audio file.

### Architecture Impact

```
packages/pipeline/aqar_pipeline/
├── stages/
│   ├── __init__.py              < MODIFIED (export new task)
│   ├── ingestion.py             < MODIFIED (chain to audio extraction)
│   └── audio_extraction.py      < NEW
├── utils/
│   ├── youtube.py               < MODIFIED (add download function)
│   └── audio.py                 < NEW (audio file utilities)
└── tests/unit/
    └── test_audio_extraction.py < NEW
```

### Key Design Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| Audio format | MP3, WAV, FLAC, OGG | WAV 16kHz mono | Whisper's native input format. No lossy compression artifacts that could degrade Arabic transcription accuracy. |
| Download tool | youtube-dl, yt-dlp, pytube | yt-dlp | Already installed, actively maintained, handles rate limiting, supports postprocessors for FFmpeg conversion. |
| File naming | UUID, hash, video_id | `{external_id}.wav` | Predictable, easy to debug, maps directly to YouTube video ID. |
| Cleanup strategy | Immediate after transcription, cron job, manual | Immediate after transcription | Keeps disk usage minimal. Cleanup task called by the transcription stage on success. |

### Data Flow

```
ingest_video() / discover_videos()
    │
    ▼
extract_audio(video_source_id)
    │
    ├── Load VideoSource from DB
    ├── Update ProcessingJob: status=INGESTING
    ├── yt-dlp: download best audio stream
    ├── FFmpeg: convert to WAV 16kHz mono
    ├── Save to: /tmp/aqar/downloads/{external_id}.wav
    ├── Update ProcessingJob: status=TRANSCRIBING
    └── Return audio_path for next stage
         │
         ▼
    [Sprint 3: transcribe_audio(video_source_id, audio_path)]
```

## 4. Acceptance Criteria

- [ ] yt-dlp downloads audio-only stream from YouTube URL
- [ ] Audio is converted to WAV format (16kHz mono) for Whisper
- [ ] Downloaded files stored in configurable DOWNLOAD_PATH
- [ ] ProcessingJob status updated to INGESTING during download
- [ ] ProcessingJob status updated to TRANSCRIBING after success
- [ ] Failed downloads captured with error details in ProcessingJob
- [ ] Cleanup utility deletes audio files after use
- [ ] Unit tests cover: path generation, format validation, cleanup logic

## 5. Test Plan

- **Unit Tests:** Audio path generation, WAV validation, cleanup function, yt-dlp option building.
- **Integration Tests:** Download a short public-domain video, verify WAV output format.
- **Manual Verification:** Submit a real YouTube URL, check that WAV file appears in the downloads volume.

## 6. Notes for Thesis

- Audio quality directly impacts transcription accuracy. The choice of 16kHz mono WAV eliminates codec artifacts as a confounding variable when evaluating Whisper performance.
- Download times and file sizes should be logged for the system performance chapter.
- The cleanup strategy ensures the system can run continuously without disk exhaustion, an important operational consideration for the deployment chapter.

---

*This document follows the SDLC Analyse, Design, Implement, Test, DevOps cycle.*
