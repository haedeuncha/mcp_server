"""Frontend 스모크 테스트 - Streamlit AppTest로 화면을 렌더링하고, 백엔드 응답은 mock으로 대체한다."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")

WEATHER = {"success": True, "cached": True, "city": "서울", "country": "대한민국", "date": "2026-10-03",
           "temperature_max": 22.5, "temperature_min": 13.2, "precipitation_probability": 60, "source": "Open-Meteo"}


def fake_get(url, **_kwargs):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    if url.endswith("/weather"):
        resp.json.return_value = WEATHER
    elif url.endswith("/health"):
        resp.json.return_value = {"status": "ok", "redis": "ok", "database": "ok"}
    else:
        resp.json.return_value = {"items": []}
    return resp


def test_renders_without_backend():
    at = AppTest.from_file(APP).run(timeout=30)
    assert not at.exception
    assert at.title[0].value == "Weather Dashboard"


def test_fetch_weather_shows_metrics():
    with patch("requests.get", side_effect=fake_get):
        at = AppTest.from_file(APP).run(timeout=30)
        at.button[0].click().run(timeout=30)
    assert not at.exception
    assert [m.value for m in at.metric] == ["22.5°C", "13.2°C", "60%"]
