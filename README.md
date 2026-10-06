# Weather MCP Project

| 폴더 | 역할 | 포트 |
|---|---|---|
| `mcp_server/` | 날씨 MCP 서버 (FastMCP, Open-Meteo) | 8010 |
| `backend/` | FastAPI. MCP `get_weather` 호출 + Redis 캐시 + PostgreSQL 조회 기록 | 8000 |
| `frontend/` | Streamlit UI | 8501 |
| (compose) | `redis` / `postgres` 컨테이너 | 6380 / 5432 (127.0.0.1만) |

## 폴더 구조

각 서비스는 같은 형태로 되어 있습니다.

```
<서비스>/                     (mcp_server, backend, frontend)
├─ src/<서비스>/
│   ├─ __init__.py
│   ├─ config.py              .env 값을 한곳에서 읽는 설정 모듈
│   └─ server.py | app.py      실제 코드
├─ tests/                     pytest 테스트 (pytest.ini: pythonpath = src)
├─ docker/Dockerfile          빌드: 서비스 폴더에서 docker build -f docker/Dockerfile .
├─ compose.prod.yml           EC2 배포용
├─ .env.example               필요한 환경변수 목록 (복사해서 .env 로 사용, .env 는 git 제외)
├─ requirements.txt / requirements-dev.txt
└─ .venv/                     scripts/setup.ps1 이 생성 (git 제외)
```

직접 실행할 때는 서비스 폴더에서 `PYTHONPATH=src` 를 지정합니다.

```powershell
cd backend; $env:PYTHONPATH="src"; .\.venv\Scripts\python -m backend.app
```

## 환경 변수 (.env)

각 폴더에 자기 `.env` 가 있습니다 (git 에는 올라가지 않음, 형식은 `.env.example` 참고).

- `mcp_server/.env` : `MCP_HOST`, `MCP_PORT`
- `backend/.env` : `WEATHER_MCP_URL`, `REDIS_URL`, `DATABASE_URL`, `CACHE_TTL_SECONDS`, LLM 키
- `frontend/.env` : `BACKEND_URL`
- 루트 `.env` : docker compose 의 postgres 설정 (`POSTGRES_USER/PASSWORD/DB`)

## 로컬 실행 (Windows)

```powershell
cd C:\mcp_server
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1   # 최초 1회: 각 폴더 .venv 생성 + 설치
powershell -ExecutionPolicy Bypass -File scripts\run.ps1     # redis/postgres(docker) + 3개 서비스 실행
```

브라우저: http://127.0.0.1:8501 (Docker Desktop 이 없으면 캐시/조회 기록 없이 동작)

수동 실행 시 (각각 다른 터미널):

```powershell
cd mcp_server; $env:PYTHONPATH="src"; .\.venv\Scripts\python -m mcp_server.server
cd backend;    $env:PYTHONPATH="src"; .\.venv\Scripts\python -m backend.app
cd frontend;   $env:PYTHONPATH="src"; .\.venv\Scripts\streamlit run src/frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

## 전체 Docker 실행

```bash
docker compose up -d --build
```

## CI/CD (GitHub Actions)

서비스마다 EC2 인스턴스 1대씩 (총 5대). main 에 push 하면 바뀐 폴더의 CI 가 돌고, 통과하면 그 서비스 인스턴스에만 배포합니다.

| 워크플로 | 트리거 | CI | 배포 대상 |
|---|---|---|---|
| `mcp-server-ci.yml` | `mcp_server/**` | pytest → 이미지 빌드 → `/health`, `tools/list` | mcp 인스턴스 |
| `backend-ci.yml` | `backend/**` | redis·postgres 서비스로 pytest → 이미지 빌드 | backend 인스턴스 |
| `frontend-ci.yml` | `frontend/**` | Streamlit AppTest → 이미지 빌드 → `/_stcore/health` | frontend 인스턴스 |
| `infra-ci.yml` | `infra/**` | redis·postgres 컨테이너 healthy 확인 | redis, postgres 인스턴스 |
| `_deploy.yml` | (재사용) | 사설 IP 조회 → `.env` 생성 → 업로드 → `docker compose up -d --build` → 헬스체크 | |

필요한 secret 이 없으면 **배포만 건너뛰고** 워크플로는 성공합니다 (Summary 에 경고 표시).

### Repository secrets

| 이름 | 값 |
|---|---|
| `AWS_USER` | 공통 SSH 계정 (예: `ubuntu`) |
| `AWS_SSH_PRIVATE_KEY` | 공통 키페어 `.pem` 내용 전체 |
| `AWS_SSH_KNOWN_HOSTS` | `ssh-keyscan <5대 퍼블릭 IP>` 결과 전체 |
| `MCP_EC2_HOST` `BACKEND_EC2_HOST` `FRONTEND_EC2_HOST` `REDIS_EC2_HOST` `POSTGRES_EC2_HOST` | 각 인스턴스 퍼블릭 IP |
| `REDIS_PASSWORD` | redis 비밀번호 (영문/숫자 권장) |
| `POSTGRES_PASSWORD` | postgres 비밀번호 (영문/숫자 권장) |
| `BACKEND_ENV` (선택) | backend 추가 환경변수 (LLM 키 등, `KEY=VALUE` 여러 줄) |

### EC2 준비

- 5대 모두 같은 VPC, Docker + Compose 플러그인 설치, 22번(SSH) 허용
- 보안 그룹 인바운드 (서비스 포트)
  - frontend: 8501 ← 0.0.0.0/0
  - backend: 8000 ← frontend 보안 그룹
  - mcp: 8010 ← backend 보안 그룹
  - redis: 6379 ← backend 보안 그룹
  - postgres: 5432 ← backend 보안 그룹
- 인스턴스끼리는 사설 IP 로 통신합니다 (배포 시 자동 조회). 처음 배포는 infra → mcp → backend → frontend 순서가 안전합니다.
