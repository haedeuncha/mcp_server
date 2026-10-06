"""
시나리오
사용자가 선택한 도시의 실제 날씨를 Open-Meteo에서 조회하는 MCP Tool Server입니다.
Docker에서는 Backend만 내부 주소 weather-mcp:8010으로 접근하고, 로컬 개발에서는 127.0.0.1:8010을 씁니다.
도시를 좌표로 변환한 뒤 오늘 또는 내일의 최고·최저 기온과 강수 확률을 반환합니다.
"""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.responses import JSONResponse

load_dotenv(Path(__file__).with_name(".env"))

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8010"))

mcp = FastMCP("weather-tools", host=MCP_HOST, port=MCP_PORT, stateless_http=True, json_response=True)

# Open-Meteo 지오코딩은 한글 도시명("서울")을 찾지 못하므로 영문 이름으로 바꿔 다시 검색한다.
KOREAN_CITY_ALIASES = {
    "서울": "Seoul", "부산": "Busan", "인천": "Incheon", "대구": "Daegu", "대전": "Daejeon",
    "광주": "Gwangju", "울산": "Ulsan", "세종": "Sejong", "수원": "Suwon", "성남": "Seongnam",
    "고양": "Goyang", "용인": "Yongin", "창원": "Changwon", "청주": "Cheongju", "전주": "Jeonju",
    "천안": "Cheonan", "포항": "Pohang", "제주": "Jeju", "서귀포": "Seogwipo", "강릉": "Gangneung",
    "춘천": "Chuncheon", "원주": "Wonju", "속초": "Sokcho", "여수": "Yeosu", "순천": "Suncheon",
    "목포": "Mokpo", "경주": "Gyeongju", "안동": "Andong", "김해": "Gimhae", "평택": "Pyeongtaek",
}
CITY_SUFFIXES = ("특별자치시", "특별자치도", "특별시", "광역시", "시")


def search_names(city: str) -> list[str]:
    """검색할 이름 후보: 입력값 → (접미사 제거) → 영문 별칭 순서."""
    name = city.strip()
    names = [name]
    base = name
    for suffix in CITY_SUFFIXES:
        if base.endswith(suffix) and len(base) > len(suffix):
            base = base[: -len(suffix)]
            break
    if base != name:
        names.append(base)
    alias = KOREAN_CITY_ALIASES.get(base)
    if alias:
        names.append(alias)
    return list(dict.fromkeys(names))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True))
def get_weather(city: str, day: str = "tomorrow") -> dict:
    """도시 이름과 today 또는 tomorrow를 받아 실제 일별 날씨를 반환합니다."""
    if day not in {"today", "tomorrow"}:
        raise ValueError("day는 today 또는 tomorrow여야 합니다.")
    with httpx.Client(timeout=15) as client:
        place = None
        for name in search_names(city):
            geo = client.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": name, "count": 1, "language": "ko", "format": "json"})
            geo.raise_for_status()
            places = geo.json().get("results", [])
            if places:
                place = places[0]
                break
        if place is None:
            return {"success": False, "error": "CITY_NOT_FOUND", "city": city}
        forecast = client.get("https://api.open-meteo.com/v1/forecast", params={"latitude": place["latitude"], "longitude": place["longitude"], "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code", "timezone": "auto", "forecast_days": 2})
        forecast.raise_for_status()
    daily = forecast.json()["daily"]
    index = 0 if day == "today" else 1
    return {"success": True, "city": place["name"], "country": place.get("country"), "date": daily["time"][index], "temperature_max": daily["temperature_2m_max"][index], "temperature_min": daily["temperature_2m_min"][index], "precipitation_probability": daily["precipitation_probability_max"][index], "weather_code": daily["weather_code"][index], "source": "Open-Meteo"}

@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    return JSONResponse({"status": "ok", "service": "weather-mcp"})

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
