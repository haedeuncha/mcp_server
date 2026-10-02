# 로컬 실행: redis/postgres(docker) + mcp_server(8010) + backend(8000) + frontend(127.0.0.1:8501)
# 사용법 (C:\mcp_server 에서):  powershell -ExecutionPolicy Bypass -File scripts\run.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# 1) redis + postgres (Docker Desktop 이 있을 때만). 없으면 backend 는 캐시/기록 없이 동작
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "redis / postgres 컨테이너 시작" -ForegroundColor Green
    docker compose -f (Join-Path $root "compose.yml") up -d redis postgres
} else {
    Write-Host "docker 없음: redis/postgres 없이 실행합니다 (캐시/조회 기록 비활성)" -ForegroundColor Yellow
}

function Start-App($dir, $cmd) {
    $path = Join-Path $root $dir
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$path'; `$host.UI.RawUI.WindowTitle='$dir'; .\.venv\Scripts\$cmd"
}

# 2) 각 서비스는 별도 창에서 실행
Start-App "mcp_server" "python.exe server.py"
Start-Sleep -Seconds 3
Start-App "backend" "python.exe app.py"
Start-Sleep -Seconds 3
Start-App "frontend" "streamlit.exe run app.py --server.address 127.0.0.1 --server.port 8501"

Write-Host "`n열기: http://127.0.0.1:8501" -ForegroundColor Cyan
Start-Sleep -Seconds 5
Start-Process "http://127.0.0.1:8501"
