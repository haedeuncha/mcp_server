# Weather MCP Server

Open-Meteo로 실제 날씨를 조회하는 MCP Tool Server (`get_weather`). Backend만 Docker 내부 주소 `http://weather-mcp:8010/mcp`로 접근합니다.

## 로컬 테스트

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -v
```

## CI/CD (`.github/workflows/weather-mcp-cicd.yml`)

```text
PR / push   -> test (pytest, Open-Meteo mock) -> docker-smoke (/health, MCP tools/list)
main push   -> deploy: SSH로 서버에 소스 업로드 -> docker build -> weather-mcp 컨테이너 교체 -> /health 확인
```

- Repository secrets: `AWS_HOST`, `AWS_USER`, `AWS_SSH_PRIVATE_KEY`, `AWS_SSH_KNOWN_HOSTS`
- 서버에는 Docker만 있으면 됩니다. Host 포트는 열지 않고 `weather-net` 네트워크에만 붙습니다.
- Backend 컨테이너도 같은 네트워크(`weather-net`)에 연결해야 `weather-mcp:8010`으로 호출할 수 있습니다.
