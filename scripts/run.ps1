# 로컬 실행: redis/postgres(docker) + mcp_server(8010) + backend(8000) + frontend(127.0.0.1:8501)
# 사용법 (C:\mcp_server 에서):  powershell -ExecutionPolicy Bypass -File scripts\run.ps1
$ErrorActionPreference = "Continue"   # docker 진행 메시지(stderr)로 스크립트가 멈추지 않게
$root = Split-Path -Parent $PSScriptRoot

# 0) .venv 확인
foreach ($dir in "mcp_server", "backend", "frontend") {
    if (-not (Test-Path (Join-Path $root "$dir\.venv\Scripts\python.exe"))) {
        Write-Host "$dir\.venv 가 없습니다. 먼저 scripts\setup.ps1 을 실행하세요." -ForegroundColor Red
        exit 1
    }
}

# 1) redis(127.0.0.1:6380) + postgres(127.0.0.1:5432) - Docker Desktop 이 켜져 있을 때만
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "redis / postgres 컨테이너 시작" -ForegroundColor Green
    docker compose -f (Join-Path $root "compose.yml") up -d redis postgres 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { Write-Host "docker 실행 실패: 캐시/조회 기록 없이 계속합니다 (Docker Desktop 이 켜져 있는지 확인)" -ForegroundColor Yellow }
} else {
    Write-Host "docker 없음: redis/postgres 없이 실행합니다 (캐시/조회 기록 비활성)" -ForegroundColor Yellow
}

function Start-App($dir, $cmd) {
    $path = Join-Path $root $dir
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$path'; `$host.UI.RawUI.WindowTitle='$dir'; .\.venv\Scripts\$cmd"
}

function Wait-Port($port, $name) {
    for ($i = 0; $i -lt 30; $i++) {
        if ((Test-NetConnection 127.0.0.1 -Port $port -WarningAction SilentlyContinue).TcpTestSucceeded) {
            Write-Host "  $name 준비됨 (127.0.0.1:$port)" -ForegroundColor Green; return $true
        }
        Start-Sleep -Seconds 1
    }
    Write-Host "  $name 이(가) $port 에서 응답하지 않습니다. '$name' 창의 에러를 확인하세요." -ForegroundColor Red
    return $false
}

# 포트를 이미 쓰는 프로세스가 있으면 알려주고 새로 띄우지 않는다 (이전 실행 창이 남아 있는 경우 등)
function Port-Owner($port) {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { return Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue }
    return $null
}

function Run-Service($dir, $cmd, $port) {
    $owner = Port-Owner $port
    if ($owner) {
        Write-Host "  ${dir}: ${port} 포트를 이미 '$($owner.ProcessName)'(PID $($owner.Id))가 쓰고 있어 새로 띄우지 않습니다." -ForegroundColor Yellow
        Write-Host "     이전 실행 창이면 그대로 쓰면 되고, 다시 띄우려면: Stop-Process -Id $($owner.Id)" -ForegroundColor Yellow
        return $true
    }
    Start-App $dir $cmd
    return (Wait-Port $port $dir)
}

# 2) 각 서비스는 별도 창에서 실행
Run-Service "mcp_server" "python.exe server.py" 8010 | Out-Null
Run-Service "backend"    "python.exe app.py"    8000 | Out-Null
if (Run-Service "frontend" "streamlit.exe run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true" 8501) {
    Start-Process "http://127.0.0.1:8501"
}
