"""Weather MCP Server 설정 - 서비스 폴더의 .env 를 읽어 한곳에서 관리한다.
환경변수가 이미 있으면(Docker/배포) 그 값이 우선이다."""

import os
from pathlib import Path

from dotenv import load_dotenv

# src/mcp_server/config.py → 서비스 루트(.env 위치)는 두 단계 위
SERVICE_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(SERVICE_ROOT / ".env")

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8010"))
