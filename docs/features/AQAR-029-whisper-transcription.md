# Feature: AQAR-029: Whisper Transcription Pipeline

> **Sprint:** 3: Transcription Pipeline
> **Branch:** `feature/AQAR-029-whisper-transcription`
> **Author:** Aqar.ai Team
> **Date:** 2026-05-12
> **Status:** In Progress

---

## 1. User Stories

### US-010: Whisper Transcription (AQAR-029, AQAR-030, AQAR-031)

> As a pipeline stage, I want to transcribe audio files using OpenAI Whisper so that spoken property details are converted to text.

### US-012: Darija/Arabic Text Normalization (AQAR-035, AQAR-036)

> As a pipeline utility, I want to normalize Darija transcription text so that downstream LLM extraction handles dialectal variations consistently.

**Priority:** P0 (AQAR-029/030/031), P2 (AQAR-035/036)
**Story Points:** 11 (combined)
**Related Issues:** AQAR-029, AQAR-030, AQAR-031, AQAR-035, AQAR-036

## 2. Analysis

### Problem Statement

After audio extraction (Sprint 2), we have WAV files (16kHz mono) containing spoken Arabic/Darija property descriptions. These need to be transcribed to text before the LLM can extract structured data. The transcription stage is the most compute-intensive part of the pipeline and directly impacts downstream extraction quality.

### Current State

- Audio files are downloaded and converted to WAV 16kHz mono (AQAR-020).
- `audio_extraction.py` has a TODO comment where transcription chaining should happen.
- The `Transcript` model exists with fields for full_text, segments, language, confidence.
- Whisper is already in the pipeline dependencies (`openai-whisper>=20231117`).
- The worker Dockerfile includes FFmpeg (required by Whisper).

### Constraints & Assumptions

- Whisper `large-v3` gives the best Arabic accuracy but requires ~10GB VRAM (GPU) or runs slowly on CPU. For the dev environment, we default to `base` model and allow override via `WHISPER_MODEL` env var.
- Typical transcription time: 1-5 minutes on CPU for a 10-minute video (base model). GPU drops this to seconds.
- Whisper outputs timestamped segments which are valuable for linking properties to specific video timestamps.
- Darija (Moroccan Arabic) is not a separate language code in Whisper. We use `ar` (Arabic) as the language hint.
- Some videos mix Arabic, French, and Darija. Whisper handles this reasonably with the `ar` hint.

## 3. Design

### Approach

The transcription stage is a Celery task that:
1. Loads a cached Whisper model (singleton pattern to avoid reloading per task).
2. Transcribes the WAV file with language hint `ar`.
3. Extracts full text, timestamped segments, and confidence scores.
4. Stores results in the `Transcript` table.
5. Optionally normalizes Darija text (number words, abbreviations).
6. Updates ProcessingJob via JobManager and chains to the next stage.
7. Triggers audio cleanup after successful transcription.

### Architecture Impact

```
packages/pipeline/aqar_pipeline/
├── stages/
│   ├── __init__.py              < MODIFIED (export new task)
│   ├── audio_extraction.py      < MODIFIED (chain to transcription)
│   └── transcription.py         < NEW
├── utils/
│   ├── whisper_loader.py        < NEW (singleton model loader)
│   └── text_normalizer.py       < NEW (Darija normalization)
└── tests/unit/
    ├── test_transcription.py    < NEW
    └── test_text_normalizer.py  < NEW
```

### Key Design Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| Model loading | Load per task, singleton, shared memory | Singleton with module-level cache | Avoids reloading 3GB model for each task. First task loads it, subsequent tasks reuse. |
| Default model | tiny, base, small, medium, large-v3 | base (dev), configurable via env | base gives reasonable accuracy with fast CPU inference. Production uses large-v3 via WHISPER_MODEL env var. |
| Language handling | Auto-detect, fixed ar, multi-language | Fixed `ar` with auto-detect fallback | Most content is Arabic/Darija. Fixed hint improves accuracy. Detected language stored for analysis. |
| Segment storage | Flat text only, JSON segments, separate table | JSONB segments in Transcript table | Segments enable timestamp-linked property extraction in Sprint 4. JSONB avoids extra joins. |
| Normalization | Pre-transcription, post-transcription, none | Post-transcription (before LLM) | Normalize after Whisper output, before sending to Claude for extraction. Keeps raw transcript intact. |

### Data Flow

```
extract_audio() completes
    |
    v
transcribe_audio(video_source_id, audio_path)
    |
    ├── Load Whisper model (cached singleton)
    ├── JobManager.start_stage("transcription")
    ├── whisper.transcribe(audio_path, language="ar")
    ├── Extract: full_text, segments[], language, confidence
    ├── Normalize Darija text (optional)
    ├── Create Transcript record in DB
    ├── JobManager.complete_stage()
    ├── Trigger cleanup_audio()
    └── [Sprint 4: chain to extract_properties()]
```

## 4. Acceptance Criteria

- [ ] Whisper model processes WAV audio files
- [ ] Language hint set to Arabic (ar) for better accuracy
- [ ] Full text and timestamped segments stored in Transcript table
- [ ] Transcription confidence score calculated and stored
- [ ] Processing time tracked for performance benchmarking
- [ ] Model name/version recorded for reproducibility
- [ ] Audio file cleaned up after successful transcription
- [ ] Darija text normalizer handles number words and common abbreviations
- [ ] Unit tests for normalizer, segment parsing, confidence calculation

## 5. Test Plan

- **Unit Tests:** Text normalizer (number words, abbreviations), segment parsing, confidence averaging, Whisper option building.
- **Integration Tests:** Transcribe a short WAV file (generate synthetic audio in test), verify Transcript record.
- **Manual Verification:** Submit a real Moroccan real estate YouTube video, inspect the transcript in the database.

## 6. Notes for Thesis

- Whisper model size vs. accuracy vs. speed tradeoff is a key evaluation dimension. Test with base, small, medium, and large-v3 on the golden dataset.
- Word Error Rate (WER) measurement against the golden dataset is Sprint 3's US-011 (AQAR-032/033/034). Can be added as a follow-up.
- The Darija normalization module is a novel contribution: no existing NLP library handles Moroccan Arabic number words and real estate vocabulary.
- Transcription processing times should be logged per model size for the performance evaluation chapter.

---

*This document follows the SDLC Analyse, Design, Implement, Test, DevOps cycle.*
