"""Backend 테스트 - MCP 서버는 httpx MockTransport, Redis는 fakeredis로 대체한다.
DATABASE_URL 이 설정된 환경(CI의 postgres 서비스)에서는 DB 기록 테스트도 실행한다."""

import json
import os

import fakeredis
import httpx
import pytest
from fastapi.testclient import TestClient

from backend import app as backend
from backend import config

WEATHER = {"success": True, "city": "서울", "country": "대한민국", "date": "2026-10-03",
           "temperature_max": 22.5, "temperature_min": 13.2, "precipitation_probability": 60,
           "weather_code": 61, "source": "Open-Meteo"}


def _mcp_ok(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    assert body["method"] == "tools/call"
    assert body["params"]["name"] == "get_weather"
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {
        "content": [{"type": "text", "text": json.dumps(WEATHER)}],
        "structuredContent": WEATHER, "isError": False}})


@pytest.fixture
def mcp_calls(monkeypatch):
    calls = []
    real_client = httpx.Client

    def factory(*args, **kwargs):
        def handler(request):
            calls.append(request)
            return _mcp_ok(request)
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(backend.httpx, "Client", factory)
    return calls


@pytest.fixture
def no_db(monkeypatch):
    monkeypatch.setattr(config, "DATABASE_URL", "")


@pytest.fixture
def fake_redis(monkeypatch):
    monkeypatch.setattr(config, "REDIS_URL", "redis://fake")
    monkeypatch.setattr(backend, "_redis", fakeredis.FakeRedis(decode_responses=True))


@pytest.fixture
def no_redis(monkeypatch):
    monkeypatch.setattr(config, "REDIS_URL", "")


def test_health_without_redis_and_db(no_redis, no_db):
    with TestClient(backend.app) as client:
        body = client.get("/health").json()
    assert body == {"status": "ok", "service": "backend", "redis": "unavailable", "database": "unavailable"}


def test_weather_calls_mcp(mcp_calls, no_redis, no_db):
    with TestClient(backend.app) as client:
        body = client.get("/weather", params={"city": "서울", "day": "tomorrow"}).json()
    assert body["cached"] is False
    assert body["temperature_max"] == 22.5
    assert len(mcp_calls) == 1


def test_weather_uses_redis_cache(mcp_calls, fake_redis, no_db):
    with TestClient(backend.app) as client:
        first = client.get("/weather", params={"city": "서울"}).json()
        second = client.get("/weather", params={"city": "서울"}).json()
    assert first["cached"] is False
    assert second["cached"] is True
    assert len(mcp_calls) == 1  # 두 번째는 Redis에서


def test_wrapped_structured_content(monkeypatch, no_redis, no_db):
    real_client = httpx.Client

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(lambda r: httpx.Response(200, json={
            "jsonrpc": "2.0", "id": 1, "result": {"content": [], "structuredContent": {"result": WEATHER}}}))
        return real_client(*args, **kwargs)

    monkeypatch.setattr(backend.httpx, "Client", factory)
    assert backend.call_mcp_weather("서울", "tomorrow") == WEATHER


def test_mcp_failure_returns_502(monkeypatch, no_redis, no_db):
    real_client = httpx.Client

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(lambda r: httpx.Response(500))
        return real_client(*args, **kwargs)

    monkeypatch.setattr(backend.httpx, "Client", factory)
    with TestClient(backend.app) as client:
        assert client.get("/weather").status_code == 502


def test_invalid_day_rejected(no_redis, no_db):
    with TestClient(backend.app) as client:
        assert client.get("/weather", params={"day": "yesterday"}).status_code == 422


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL 없음 (CI postgres 서비스에서 실행)")
def test_history_saved_to_postgres(mcp_calls, no_redis, monkeypatch):
    monkeypatch.setattr(config, "DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    with TestClient(backend.app) as client:
        client.get("/weather", params={"city": "서울"})
        items = client.get("/history", params={"limit": 1}).json()["items"]
    assert items[0]["city"] == "서울"
    assert items[0]["result"]["temperature_max"] == 22.5
