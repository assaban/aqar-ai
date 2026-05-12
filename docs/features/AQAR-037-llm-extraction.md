# Feature: AQAR-037: LLM Property Extraction (Multi-Provider)

> **Sprint:** 4: LLM Data Extraction
> **Branch:** `feature/AQAR-037-llm-extraction`
> **Author:** Aqar.ai Team
> **Date:** 2026-05-12
> **Status:** In Progress

---

## 1. User Stories

### US-013: Claude Property Extraction (AQAR-037, AQAR-038, AQAR-039, AQAR-040)

> As a pipeline stage, I want to extract structured property data from transcriptions using LLMs so that unstructured speech becomes searchable listings.

### US-014: Prompt Version Management (AQAR-041, AQAR-042)

> As a researcher, I want to version-control prompts and track which version extracted each property so that I can measure prompt improvement for my thesis.

### US-015: Extraction Quality Review (AQAR-043, AQAR-044)

> As an operator, I want low-confidence extractions flagged for manual review so that data quality is maintained.

**Priority:** P0 (AQAR-037/038/039/040), P1 (AQAR-041/042/043/044)
**Story Points:** 19 (combined)
**Related Issues:** AQAR-037 through AQAR-044

## 2. Analysis

### Problem Statement

After transcription, we have raw Arabic/Darija text describing properties. We need to extract structured data (price, area, rooms, location, property type, legal status) using LLMs. The system must support multiple LLM providers because:

1. **Cost optimization:** Local models (Ollama/Gemma) are free for development and bulk processing.
2. **Quality comparison:** Comparing extraction accuracy across providers is valuable for the thesis.
3. **Resilience:** If one provider is down, the system can fall back to another.
4. **Flexibility:** Different models may perform better for different extraction subtasks.

### Provider Priority

| Priority | Provider | Model | Use Case |
|----------|----------|-------|----------|
| Primary | Ollama (local) | Gemma 4, Gemma 3 | Development, bulk processing, cost-free |
| Secondary | OpenAI | GPT-4o, GPT-4o-mini | High accuracy extraction, comparison baseline |
| Tertiary | Anthropic | Claude Sonnet | Arabic language strength, comparison |

### Current State

- Transcript records exist with full_text and segments.
- Property model has all extraction target fields (price, area, rooms, etc.).
- Prompt template v1.0 exists in `prompts/property_extraction_v1.py`.
- No LLM integration code exists yet.

## 3. Design

### Strategy Pattern Architecture

The LLM extraction uses the **Strategy Pattern** with a provider abstraction layer. Each provider implements the same interface (`LLMProvider`), and the extraction task selects the provider at runtime based on configuration.

```
                    ┌─────────────────────┐
                    │   LLMProvider (ABC)  │
                    │                     │
                    │ + extract(prompt,    │
                    │   transcript) ->     │
                    │   ExtractionResult   │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────┴──────┐ ┌─────┴──────┐ ┌──────┴─────────┐
    │ OllamaProvider │ │ OpenAI     │ │ AnthropicProvider│
    │                │ │ Provider   │ │                  │
    │ gemma4, gemma3 │ │ gpt-4o     │ │ claude-sonnet    │
    └────────────────┘ └────────────┘ └──────────────────┘
```

### Architecture Impact

```
packages/pipeline/aqar_pipeline/
├── providers/
│   ├── __init__.py              < NEW (provider registry)
│   ├── base.py                  < NEW (ABC + dataclasses)
│   ├── ollama_provider.py       < NEW
│   ├── openai_provider.py       < NEW
│   └── anthropic_provider.py    < NEW
├── stages/
│   ├── __init__.py              < MODIFIED
│   ├── transcription.py         < MODIFIED (chain to extraction)
│   └── extraction.py            < NEW
├── utils/
│   └── prompt_loader.py         < NEW (versioned prompt management)
├── tests/unit/
│   ├── test_extraction.py       < NEW
│   └── test_providers.py        < NEW
└── prompts/                     (root level, already exists)
    └── property_extraction_v1.py < MODIFIED (structured for loader)

docker-compose.yml               < MODIFIED (add Ollama service)
```

### Key Design Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| Provider pattern | Factory, Strategy, Plugin | Strategy Pattern (ABC) | Clean interface, easy to add providers, testable with mocks. Each provider is self-contained. |
| Provider selection | Hardcoded, config file, env var, per-request | Env var default + per-request override | `LLM_PROVIDER` env var sets default. API can override for A/B testing. |
| Ollama integration | REST API, ollama-python SDK | REST API via httpx | Fewer dependencies, Ollama's REST API is simple and stable. Works with any Ollama-compatible server. |
| Response parsing | Regex, JSON mode, structured output | JSON mode with fallback parsing | All three providers support JSON output. Fallback parser handles malformed responses. |
| Prompt versioning | Database table, file naming, git tags | File-based with version in filename + metadata | Version-controlled, easy to diff, prompt_version stored on each Property for traceability. |
| Local model hosting | vLLM, Ollama, llama.cpp | Ollama | Simplest setup, Docker-native, supports Gemma 3/4, easy model management. |

### Data Flow

```
transcribe_audio() completes
    |
    v
extract_properties(video_source_id)
    |
    ├── Load Transcript from DB
    ├── Load prompt template (versioned)
    ├── Select LLM provider (env var or config)
    ├── JobManager.start_stage("extraction")
    ├── provider.extract(prompt, transcript_text)
    │     ├── Ollama: POST /api/generate (Gemma 4)
    │     ├── OpenAI: POST /v1/chat/completions
    │     └── Anthropic: POST /v1/messages
    ├── Parse JSON response -> list[PropertyData]
    ├── Validate and create Property records
    ├── Flag low-confidence extractions (needs_review=True)
    ├── JobManager.complete_stage()
    └── [Sprint 5: chain to geocode_properties()]
```

## 4. Acceptance Criteria

- [ ] Strategy Pattern with abstract LLMProvider base class
- [ ] OllamaProvider: Gemma 4 and Gemma 3 support via REST API
- [ ] OpenAIProvider: GPT-4o and GPT-4o-mini support
- [ ] AnthropicProvider: Claude Sonnet support
- [ ] Provider selection via LLM_PROVIDER env var with runtime override
- [ ] Versioned prompt loading from prompts/ directory
- [ ] Property.prompt_version tracks which prompt extracted the data
- [ ] Properties with confidence < 0.6 flagged with needs_review=True
- [ ] Retry with exponential backoff on API failures (tenacity)
- [ ] JSON response parsing with fallback for malformed output
- [ ] Ollama service added to docker-compose.yml
- [ ] Unit tests for providers, prompt loading, response parsing, confidence flagging

## 5. Test Plan

- **Unit Tests:** Provider interface compliance, response parsing, confidence flagging, prompt loading, JSON validation.
- **Integration Tests:** Extract from a real transcript using Ollama (requires running Ollama service).
- **Manual Verification:** Submit a real video, verify Property records are created with correct fields.

## 6. Notes for Thesis

- The Strategy Pattern enables systematic comparison of extraction accuracy across providers, a key evaluation dimension.
- Provider response times and token usage should be logged for cost analysis.
- The multi-provider architecture is a significant design contribution: most similar systems are locked to a single LLM.
- Prompt versioning enables measuring the impact of prompt engineering iterations, relevant for the methodology chapter.

---

*This document follows the SDLC Analyse, Design, Implement, Test, DevOps cycle.*
