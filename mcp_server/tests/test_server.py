"""Weather MCP Server 테스트 (외부 Open-Meteo 호출 없이 실행된다)."""

import httpx
import pytest
from starlette.testclient import TestClient

import server

MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def _fake_open_meteo(request: httpx.Request) -> httpx.Response:
    if "geocoding" in request.url.host:
        name = request.url.params["name"]
        if name == "없는도시":
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"results": [{"name": "서울", "country": "대한민국", "latitude": 37.56, "longitude": 126.97}]})
    return httpx.Response(200, json={"daily": {
        "time": ["2026-10-02", "2026-10-03"],
        "temperature_2m_max": [24.1, 22.5],
        "temperature_2m_min": [15.0, 13.2],
        "precipitation_probability_max": [10, 60],
        "weather_code": [1, 61],
    }})


@pytest.fixture
def mock_open_meteo(monkeypatch):
    real_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(_fake_open_meteo)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(server.httpx, "Client", client_factory)


@pytest.fixture(scope="module")
def client():
    # Streamable HTTP 세션 매니저는 프로세스당 한 번만 시작할 수 있어 module 범위로 공유한다.
    # MCP_HOST=127.0.0.1 이면 DNS rebinding 보호로 Host 헤더를 검사하므로 로컬 주소로 요청한다.
    with TestClient(server.mcp.streamable_http_app(), base_url="http://127.0.0.1:8010") as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "weather-mcp"}


def test_tools_list_exposes_get_weather(client):
    response = client.post("/mcp", headers=MCP_HEADERS, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert response.status_code == 200
    tools = {tool["name"]: tool for tool in response.json()["result"]["tools"]}
    assert "get_weather" in tools
    assert tools["get_weather"]["annotations"]["readOnlyHint"] is True


def test_get_weather_tomorrow(mock_open_meteo):
    result = server.get_weather("서울", "tomorrow")
    assert result["success"] is True
    assert result["date"] == "2026-10-03"
    assert result["temperature_max"] == 22.5
    assert result["precipitation_probability"] == 60


def test_get_weather_today(mock_open_meteo):
    assert server.get_weather("서울", "today")["date"] == "2026-10-02"


def test_get_weather_city_not_found(mock_open_meteo):
    assert server.get_weather("없는도시") == {"success": False, "error": "CITY_NOT_FOUND", "city": "없는도시"}


def test_get_weather_rejects_invalid_day():
    with pytest.raises(ValueError):
        server.get_weather("서울", "yesterday")
