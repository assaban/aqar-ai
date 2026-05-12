# Feature: AQAR-048: Geocoding & Search Index

> **Sprint:** 5: Geocoding & Storage
> **Branch:** `feature/AQAR-048-geocoding-search`
> **Author:** Aqar.ai Team
> **Date:** 2026-05-12
> **Status:** In Progress

---

## 1. User Stories

### US-017: Location Geocoding (AQAR-048, AQAR-049, AQAR-050, AQAR-051)

> As a pipeline stage, I want to geocode extracted location text to GPS coordinates so that properties can be displayed on a map.

### US-018: Tangier Neighborhood Gazetteer (AQAR-052, AQAR-053, AQAR-054)

> As a geocoding enhancer, I want a local gazetteer of Tangier neighborhoods and landmarks so that Darija place names resolve to accurate coordinates.

### US-019: Meilisearch Index (AQAR-055, AQAR-056, AQAR-057)

> As a backend service, I want properties indexed in Meilisearch so that users can perform fast full-text search with Arabic support.

### US-020: Spatial Queries (AQAR-058, AQAR-059)

> As a user, I want to search for properties within a radius of a point on the map so that I can find homes near my workplace or school.

**Priority:** P0 (AQAR-048/055), P1 (AQAR-051/052/058)
**Story Points:** 18 (combined)
**Related Issues:** AQAR-048 through AQAR-059

## 2. Analysis

### Problem Statement

After LLM extraction (Sprint 4), properties have raw location text (e.g. "حي إيبيريا طنجة") but no GPS coordinates. We need to:

1. **Geocode** location text to latitude/longitude, prioritizing a local gazetteer for Tangier neighborhoods (Darija names not found in global geocoders).
2. **Index** properties in Meilisearch for instant full-text search with Arabic support.
3. **Enable spatial queries** via PostGIS for "find properties near me" functionality.

### Current State

- Property records exist with `extras.location_raw` and `extras.neighborhood_hint` from LLM extraction.
- Location model has PostGIS geometry column, ready for spatial queries.
- Meilisearch is running in Docker but has no indexes configured.
- Properties API has basic filtering but no search or spatial queries.

## 3. Design

### Geocoding Strategy (Three-Tier Fallback)

```
1. Local Gazetteer (Tangier neighborhoods, free, instant)
   |
   ├── Match found? -> Use gazetteer coordinates
   |
   └── No match? -> Fall through
       |
       2. Nominatim (OpenStreetMap, free, rate-limited)
          |
          ├── Match found? -> Use Nominatim coordinates
          |
          └── No match? -> Fall through
              |
              3. Google Maps Geocoding API (paid, high accuracy)
                 |
                 ├── Match found? -> Use Google coordinates
                 |
                 └── No match? -> Skip geocoding, flag for review
```

### Architecture Impact

```
packages/pipeline/aqar_pipeline/
├── stages/
│   ├── __init__.py                < MODIFIED
│   ├── extraction.py              < MODIFIED (chain to geocoding)
│   └── geocoding.py               < NEW
├── providers/
│   ├── geocoding/
│   │   ├── __init__.py            < NEW (geocoding provider registry)
│   │   ├── base.py                < NEW (ABC)
│   │   ├── gazetteer.py           < NEW (local Tangier gazetteer)
│   │   ├── nominatim.py           < NEW
│   │   └── google_maps.py         < NEW
│   └── ...
├── utils/
│   └── meilisearch_sync.py        < NEW
├── data/
│   └── tangier_gazetteer.json     < NEW (neighborhood coordinates)
└── tests/unit/
    ├── test_geocoding.py          < NEW
    ├── test_gazetteer.py          < NEW
    └── test_meilisearch_sync.py   < NEW
```

### Key Design Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| Geocoding pattern | Single provider, chain of responsibility, tiered fallback | Tiered fallback (gazetteer -> Nominatim -> Google) | Local gazetteer handles Darija names; external providers handle the rest. Cost-effective. |
| Gazetteer format | SQLite, YAML, JSON | JSON file | Simple, version-controlled, fast to load (~50 neighborhoods). |
| Fuzzy matching | Exact match, Levenshtein, trigram | Trigram similarity (difflib) | Handles Arabic spelling variations without external deps. |
| Meilisearch sync | Real-time on create, batch job, change data capture | On-create sync + batch rebuild | Immediate indexing after geocoding. Batch rebuild for schema changes. |
| Spatial query | PostGIS ST_DWithin, Meilisearch geo filter, app-level | PostGIS ST_DWithin | Database-level filtering is most efficient. Already have PostGIS. |

## 4. Acceptance Criteria

- [ ] Three-tier geocoding: gazetteer -> Nominatim -> Google Maps
- [ ] Tangier gazetteer with 50+ neighborhoods (Arabic + French + Darija)
- [ ] Fuzzy matching handles spelling variations
- [ ] Coordinates stored in Location table with PostGIS geometry
- [ ] Meilisearch index created with Arabic tokenization
- [ ] Properties synced to Meilisearch after geocoding
- [ ] Spatial query: GET /api/v1/properties?lat=X&lng=Y&radius_km=Z
- [ ] Pipeline complete: geocoding marks job as COMPLETED
- [ ] Unit tests for gazetteer, geocoding fallback, Meilisearch sync

---

*This document follows the SDLC Analyse, Design, Implement, Test, DevOps cycle.*
