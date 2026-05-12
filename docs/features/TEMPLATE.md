# Feature: AQAR-XXX: [Feature Title]

> **Sprint:** X: [Sprint Name]
> **Branch:** `feature/AQAR-XXX-short-description`
> **Author:** [Name]
> **Date:** YYYY-MM-DD
> **Status:** Draft | In Progress | Complete

---

## 1. User Story

> As a [role], I want [feature] so that [benefit].

**Priority:** P0 / P1 / P2 / P3
**Story Points:** X
**Related Issues:** AQAR-XXX, AQAR-YYY

## 2. Analysis

### Problem Statement

[What problem does this feature solve? Why is it needed?]

### Current State

[What exists today? What's the gap?]

### Constraints & Assumptions

- [List any technical, business, or timeline constraints]
- [List assumptions you're making]

## 3. Design

### Approach

[Describe the technical approach. Why this design over alternatives?]

### Architecture Impact

[Which components/packages are affected? New files? Modified files?]

```
packages/pipeline/aqar_pipeline/stages/
├── ingestion.py          ← NEW
├── __init__.py            ← MODIFIED
```

### Key Design Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| [e.g. Audio format] | WAV, MP3, FLAC | WAV 16kHz | Whisper native format, no lossy compression |

### Data Flow

[Describe how data flows through the feature: input → processing → output]

## 4. Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## 5. Test Plan

- **Unit Tests:** [What will be unit tested?]
- **Integration Tests:** [What integration tests are needed?]
- **Manual Verification:** [How to verify manually?]

## 6. Notes for Thesis

[Any observations, metrics, or insights relevant to the thesis documentation]

---

*This document follows the SDLC Analyse → Design → Implement → Test → DevOps cycle.*
