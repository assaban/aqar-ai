# Feature: AQAR-070: Web Portal

> **Sprint:** 7: Web Portal
> **Branch:** `feature/AQAR-070-web-portal`
> **Author:** Aqar.ai Team
> **Date:** 2026-05-12
> **Status:** In Progress

---

## 1. User Stories

### US-025: Property Search Page (AQAR-070, AQAR-071, AQAR-072, AQAR-073)

> As a property seeker, I want a search page with filters and results so that I can browse available properties.

### US-026: Map View (AQAR-074, AQAR-075, AQAR-076, AQAR-077)

> As a property seeker, I want to see properties on an interactive map so that I can understand locations geographically.

### US-027: Property Detail Page (AQAR-078, AQAR-079, AQAR-080)

> As a property seeker, I want a detailed property page with all extracted information and the source video so that I can evaluate the listing.

### US-028: Arabic/French Bilingual UI (AQAR-081, AQAR-082, AQAR-083)

> As a Moroccan user, I want the interface available in Arabic and French so that I can use it in my preferred language.

**Priority:** P0 (search, map, detail), P2 (bilingual)
**Story Points:** 21 (combined)

## 2. Design

### Tech Stack

- **Framework:** Next.js 15 (App Router, SSR)
- **Styling:** Tailwind CSS 4
- **Maps:** Leaflet (open source, no API key needed for dev)
- **State:** React hooks (useState, useEffect), URL search params
- **API Client:** fetch with typed helpers
- **i18n:** Deferred to Sprint 9 (basic structure prepared)

### Pages

| Route | Page | SSR |
|-------|------|-----|
| `/` | Home: search bar + featured properties | SSR |
| `/search` | Full search with filters, results grid, map toggle | Client |
| `/property/[id]` | Property detail with video, map, confidence | SSR |
| `/stats` | Dashboard with system statistics | SSR |

### Key Design Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| Map library | Mapbox GL, Google Maps, Leaflet | Leaflet + OpenStreetMap | Free, no API key for dev, good enough for MVP. Mapbox for production later. |
| CSS framework | CSS Modules, styled-components, Tailwind | Tailwind CSS | Fast development, responsive utilities, consistent with modern Next.js apps. |
| Search UX | Separate search page, inline search, modal | Dedicated /search page with URL params | Shareable search URLs, SSR-friendly, clean separation. |
| i18n | next-intl, next-i18next, custom | Deferred, RTL-ready structure | Solo developer, Arabic UI is Sprint 9 scope. Layout prepared for RTL toggle. |

---

*This document follows the SDLC Analyse, Design, Implement, Test, DevOps cycle.*
