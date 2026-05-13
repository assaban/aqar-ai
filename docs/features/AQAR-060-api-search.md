# Feature: AQAR-060: API & Search

> **Sprint:** 6: API & Search
> **Branch:** `feature/AQAR-060-api-search`
> **Author:** Aqar.ai Team
> **Date:** 2026-05-12
> **Status:** In Progress

---

## 1. User Stories

### US-021: Property List & Filter API (AQAR-060, AQAR-061, AQAR-062)

> As a frontend developer, I want a comprehensive property list API with filtering and pagination so that I can build the search interface.

### US-022: Full-Text Search (AQAR-063, AQAR-064, AQAR-065)

> As a property seeker, I want to search for properties using natural language so that I can find listings matching my description.

### US-023: Statistics Dashboard API (AQAR-066, AQAR-067)

> As a thesis reviewer, I want system statistics so that I can evaluate the pipeline's performance and coverage.

### US-024: API Documentation (AQAR-068, AQAR-069)

> As a developer, I want interactive API documentation so that frontend and mobile developers can integrate easily.

**Priority:** P0 (AQAR-060/063), P1 (AQAR-066), P2 (AQAR-068)
**Story Points:** 15 (combined)

## 2. Design

### New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/search` | Full-text search via Meilisearch (Arabic + French) |
| GET | `/api/v1/properties` | Enhanced: spatial query (lat, lng, radius_km) |
| GET | `/api/v1/stats` | Enhanced: per-neighborhood breakdown, pipeline timing |
| GET | `/api/v1/stats/neighborhoods` | Neighborhood property count and avg price |
| GET | `/api/v1/videos` | List processed videos with property counts |
| GET | `/api/v1/videos/{id}` | Video detail with transcript and properties |

### Key Design Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| Search engine | DB full-text, Meilisearch, Elasticsearch | Meilisearch | Already running, Arabic tokenization, instant search, geo filter support. |
| Spatial filtering | App-level haversine, Meilisearch _geoRadius, PostGIS ST_DWithin | Both Meilisearch (search) + PostGIS (list) | Meilisearch for search results, PostGIS for list endpoint. Best of both. |
| Stats aggregation | Real-time query, materialized view, cache | Real-time with Redis cache (60s TTL) | Small dataset for MVP. Cache prevents repeated expensive aggregations. |

---

*This document follows the SDLC Analyse, Design, Implement, Test, DevOps cycle.*
