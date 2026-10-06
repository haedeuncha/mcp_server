# 각 개발 폴더(mcp_server, backend, frontend)에 .venv 를 만들고 의존성을 설치합니다.
# 사용법 (C:\mcp_server 에서):  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
# 이미 만들어진 .venv 는 그대로 두고 패키지만 다시 확인합니다.
$ErrorActionPreference = "Continue"   # pip/docker 의 진행 메시지(stderr)로 스크립트가 멈추지 않게
$root = Split-Path -Parent $PSScriptRoot

# Python 찾기 (3.12 우선)
$py = @("python")
if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($v in "3.12", "3.13", "3.11") {
        & py "-$v" -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { $py = @("py", "-$v"); break }
    }
}
Write-Host "Python: $($py -join ' ')" -ForegroundColor Cyan

$failed = @()
foreach ($dir in "mcp_server", "backend", "frontend") {
    $path = Join-Path $root $dir
    $vpy = Join-Path $path ".venv\Scripts\python.exe"
    Write-Host "`n=== $dir ===" -ForegroundColor Green
    Push-Location $path
    if (-not (Test-Path $vpy)) {
        if ($py.Count -gt 1) { & $py[0] $py[1] -m venv .venv } else { & $py[0] -m venv .venv }
    }
    if (-not (Test-Path $vpy)) { Write-Host "  .venv 생성 실패" -ForegroundColor Red; $failed += $dir; Pop-Location; continue }
    & $vpy -m pip install --disable-pip-version-check -q --upgrade pip 2>&1 | Out-Null
    & $vpy -m pip install --disable-pip-version-check -r requirements.txt -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { Write-Host "  패키지 설치 실패" -ForegroundColor Red; $failed += $dir }
    if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
        Copy-Item ".env.example" ".env"
        Write-Host "  .env.example -> .env 복사 (값을 채워주세요)" -ForegroundColor Yellow
    }
    Pop-Location
}

if ($failed.Count -gt 0) {
    Write-Host "`n실패: $($failed -join ', ')  - 위 에러 메시지를 확인하세요." -ForegroundColor Red
    exit 1
}
Write-Host "`n완료! 실행: powershell -ExecutionPolicy Bypass -File scripts\run.ps1" -ForegroundColor Cyan
