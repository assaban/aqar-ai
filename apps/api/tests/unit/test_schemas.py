"""
Unit tests for API schemas.

Tests cover: response model validation, search hit mapping,
neighborhood stats, and video detail response.
"""

import uuid

from apps.api.app.schemas import (
    NeighborhoodStat,
    NeighborhoodStatsResponse,
    SearchHit,
    SearchResponse,
    StatsResponse,
    VideoDetailResponse,
    VideoListResponse,
)


class TestSearchSchemas:
    """Tests for search-related schemas."""

    def test_search_hit_with_all_fields(self):
        hit = SearchHit(
            id="abc-123",
            property_type="apartment",
            listing_type="sale",
            title_generated="Bel appartement",
            price=750000,
            area_sqm=85,
            rooms=4,
            neighborhood="Iberia",
            city="Tangier",
        )
        assert hit.id == "abc-123"
        assert hit.price == 750000

    def test_search_hit_defaults(self):
        hit = SearchHit(id="abc-123")
        assert hit.property_type == "other"
        assert hit.listing_type == "unknown"
        assert hit.title_generated == ""
        assert hit.neighborhood == ""

    def test_search_response(self):
        resp = SearchResponse(
            hits=[SearchHit(id="1"), SearchHit(id="2")],
            query="apartment tangier",
            total=50,
            processing_time_ms=12,
        )
        assert len(resp.hits) == 2
        assert resp.total == 50
        assert resp.query == "apartment tangier"

    def test_search_response_empty(self):
        resp = SearchResponse(hits=[], query="", total=0)
        assert len(resp.hits) == 0


class TestStatsSchemas:
    """Tests for enhanced stats schemas."""

    def test_stats_response_with_breakdowns(self):
        stats = StatsResponse(
            total_videos=100,
            total_properties=250,
            total_published=200,
            processing_completed=90,
            property_types={"apartment": 150, "house": 60, "villa": 30, "land": 10},
            listing_types={"sale": 180, "rent": 50, "unknown": 20},
        )
        assert stats.total_videos == 100
        assert stats.property_types["apartment"] == 150
        assert stats.listing_types["sale"] == 180

    def test_neighborhood_stat(self):
        stat = NeighborhoodStat(
            neighborhood="Iberia",
            property_count=25,
            avg_price=650000,
            min_price=300000,
            max_price=1200000,
        )
        assert stat.neighborhood == "Iberia"
        assert stat.property_count == 25

    def test_neighborhood_stats_response(self):
        resp = NeighborhoodStatsResponse(
            neighborhoods=[
                NeighborhoodStat(neighborhood="Iberia", property_count=25),
                NeighborhoodStat(neighborhood="Marshan", property_count=15),
            ],
            total_neighborhoods=2,
        )
        assert resp.total_neighborhoods == 2


class TestVideoSchemas:
    """Tests for video-related schemas."""

    def test_video_detail_response(self):
        resp = VideoDetailResponse(
            id=str(uuid.uuid4()),  # Generates a valid random UUID
            url="https://youtube.com/watch?v=test",
            platform="youtube",
            title="Test Video",
            properties_count=3,
            transcript_text="Some transcript",
            transcript_language="ar",
            transcript_confidence=0.85,
            processing_status="completed",
            stage_timings={"ingestion": 1.2, "transcription": 45.3},
        )
        assert resp.transcript_language == "ar"
        assert resp.processing_status == "completed"
        assert resp.stage_timings["transcription"] == 45.3

    def test_video_list_response(self):
        resp = VideoListResponse(
            items=[],
            total=0,
            page=1,
            per_page=20,
            has_next=False,
        )
        assert resp.total == 0
