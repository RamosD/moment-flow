"""Unit tests for light YouTube URL parsing."""

import pytest

from apps.catalogue.utils import extract_youtube_video_id

VIDEO_ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtube.com/watch?v={VIDEO_ID}&t=10s",
        f"https://youtu.be/{VIDEO_ID}",
        f"https://www.youtube.com/shorts/{VIDEO_ID}",
        f"https://www.youtube.com/embed/{VIDEO_ID}",
        f"https://music.youtube.com/watch?v={VIDEO_ID}",
    ],
)
def test_extracts_video_id(url):
    assert extract_youtube_video_id(url) == VIDEO_ID


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://vimeo.com/123456",
        "not-a-url",
        "",
        None,
        "https://www.youtube.com/watch?v=tooshort",
    ],
)
def test_returns_none_for_non_youtube(url):
    assert extract_youtube_video_id(url) is None
