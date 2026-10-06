"""
Weather Backend
- Frontend 요청을 받아 Weather MCP 서버의 get_weather 도구를 호출합니다 (JSON-RPC tools/call).
- Redis: 같은 도시/날짜 결과를 CACHE_TTL_SECONDS 동안 캐시합니다.
- PostgreSQL: 모든 조회 기록을 weather_history 테이블에 저장합니다.
Redis/DB 주소가 없거나 연결이 안 되면 해당 기능만 건너뛰고 날씨 조회는 계속 동작합니다.
"""

import json
import logging
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Query

from backend import config

log = logging.getLogger("backend")
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


# ---------- Redis ----------
_redis = None


def get_redis():
    """Redis 클라이언트. 설정이 없거나 연결 실패 시 None."""
    global _redis
    if not config.REDIS_URL:
        return None
    if _redis is None:
        import redis

        _redis = redis.Redis.from_url(config.REDIS_URL, decode_responses=True, socket_timeout=2, socket_connect_timeout=2)
    try:
        _redis.ping()
        return _redis
    except Exception as exc:  # noqa: BLE001
        log.warning("redis unavailable: %s", exc)
        return None


def cache_key(city: str, day: str) -> str:
    return f"weather:{city.strip().lower()}:{day}"


# ---------- PostgreSQL ----------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS weather_history (
    id SERIAL PRIMARY KEY,
    city TEXT NOT NULL,
    day TEXT NOT NULL,
    cached BOOLEAN NOT NULL DEFAULT FALSE,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


def db_connect():
    """DB 연결. 설정이 없거나 연결 실패 시 None."""
    if not config.DATABASE_URL:
        return None
    try:
        import psycopg

        return psycopg.connect(config.DATABASE_URL, connect_timeout=3, autocommit=True)
    except Exception as exc:  # noqa: BLE001
        log.warning("database unavailable: %s", exc)
        return None


def init_db() -> None:
    conn = db_connect()
    if conn:
        with conn:
            conn.execute(CREATE_TABLE_SQL)


def save_history(city: str, day: str, cached: bool, result: dict) -> None:
    conn = db_connect()
    if not conn:
        return
    try:
        with conn:
            conn.execute(
                "INSERT INTO weather_history (city, day, cached, result) VALUES (%s, %s, %s, %s)",
                (city, day, cached, json.dumps(result, ensure_ascii=False)),
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("save_history failed: %s", exc)


def load_history(limit: int) -> list[dict]:
    conn = db_connect()
    if not conn:
        return []
    with conn:
        rows = conn.execute(
            "SELECT city, day, cached, result, created_at FROM weather_history ORDER BY id DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return [
        {"city": r[0], "day": r[1], "cached": r[2], "result": r[3], "created_at": r[4].isoformat()}
        for r in rows
    ]


# ---------- MCP ----------
def call_mcp_weather(city: str, day: str) -> dict:
    """Weather MCP 서버의 get_weather 도구를 호출해 결과 dict를 돌려준다."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "get_weather", "arguments": {"city": city, "day": day}},
    }
    with httpx.Client(timeout=20) as client:
        response = client.post(config.WEATHER_MCP_URL, headers=MCP_HEADERS, json=payload)
        response.raise_for_status()
    body = response.json()
    if "error" in body:
        raise RuntimeError(body["error"].get("message", "MCP error"))
    result = body["result"]
    if result.get("isError"):
        raise RuntimeError(result["content"][0].get("text", "MCP tool error"))
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        # FastMCP는 dict 반환값을 {"result": {...}} 로 감싸는 경우가 있다.
        if set(structured) == {"result"} and isinstance(structured["result"], dict):
            return structured["result"]
        return structured
    return json.loads(result["content"][0]["text"])


# ---------- FastAPI ----------
@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Weather Backend", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    conn = db_connect()
    if conn:
        conn.close()
    return {
        "status": "ok",
        "service": "backend",
        "redis": "ok" if get_redis() else "unavailable",
        "database": "ok" if conn else "unavailable",
    }


@app.get("/weather")
def weather(city: str = Query("서울", min_length=1), day: Literal["today", "tomorrow"] = "tomorrow") -> dict:
    r = get_redis()
    key = cache_key(city, day)
    if r:
        hit = r.get(key)
        if hit:
            data = json.loads(hit)
            save_history(city, day, True, data)
            return {**data, "cached": True}

    try:
        data = call_mcp_weather(city, day)
    except (httpx.HTTPError, RuntimeError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Weather MCP 호출 실패: {exc}") from exc

    if r and data.get("success"):
        r.setex(key, config.CACHE_TTL_SECONDS, json.dumps(data, ensure_ascii=False))
    save_history(city, day, False, data)
    return {**data, "cached": False}


@app.get("/history")
def history(limit: int = Query(20, ge=1, le=100)) -> dict:
    return {"items": load_history(limit)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.BACKEND_HOST, port=config.BACKEND_PORT)
