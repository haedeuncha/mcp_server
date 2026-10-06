"""Weather Backend 설정 - 서비스 폴더의 .env 를 읽어 한곳에서 관리한다.
환경변수가 이미 있으면(Docker/배포) 그 값이 우선이다."""

import os
from pathlib import Path

from dotenv import load_dotenv

# src/backend/config.py → 서비스 루트(.env 위치)는 두 단계 위
SERVICE_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(SERVICE_ROOT / ".env")

WEATHER_MCP_URL = os.getenv("WEATHER_MCP_URL", "http://127.0.0.1:8010/mcp")
REDIS_URL = os.getenv("REDIS_URL", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "600"))
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

# LLM (추후 사용)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
