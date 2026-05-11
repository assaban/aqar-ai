"""
Unit tests for pipeline router utilities.
"""

from apps.api.app.routers.pipeline import _extract_youtube_id


def test_extract_youtube_id_standard_url():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert _extract_youtube_id(url) == "dQw4w9WgXcQ"


def test_extract_youtube_id_short_url():
    url = "https://youtu.be/dQw4w9WgXcQ"
    assert _extract_youtube_id(url) == "dQw4w9WgXcQ"


def test_extract_youtube_id_embed_url():
    url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
    assert _extract_youtube_id(url) == "dQw4w9WgXcQ"


def test_extract_youtube_id_shorts_url():
    url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
    assert _extract_youtube_id(url) == "dQw4w9WgXcQ"


def test_extract_youtube_id_with_params():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120&list=PLxyz"
    assert _extract_youtube_id(url) == "dQw4w9WgXcQ"
