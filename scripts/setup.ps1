# 각 개발 폴더(mcp_server, backend, frontend)에 .venv 를 만들고 의존성을 설치합니다.
# 사용법 (C:\mcp_server 에서):  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# Python 찾기 (3.12 우선)
$py = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($v in "3.12", "3.13", "3.11") {
        try { & py "-$v" -c "import sys" 2>$null } catch { continue }
        if ($LASTEXITCODE -eq 0) { $py = @("py", "-$v"); break }
    }
}
if (-not $py) { $py = @("python") }
Write-Host "Python: $($py -join ' ')" -ForegroundColor Cyan

foreach ($dir in "mcp_server", "backend", "frontend") {
    $path = Join-Path $root $dir
    Write-Host "`n=== $dir ===" -ForegroundColor Green
    Push-Location $path
    try {
        if (-not (Test-Path ".venv")) {
            if ($py.Count -gt 1) { & $py[0] $py[1] -m venv .venv } else { & $py[0] -m venv .venv }
        }
        $vpy = Join-Path $path ".venv\Scripts\python.exe"
        & $vpy -m pip install --upgrade pip -q
        & $vpy -m pip install -r requirements.txt -r requirements-dev.txt
        if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
            Copy-Item ".env.example" ".env"
            Write-Host ".env.example -> .env 복사 (값을 채워주세요)" -ForegroundColor Yellow
        }
    } finally { Pop-Location }
}
Write-Host "`n완료! 실행: powershell -ExecutionPolicy Bypass -File scripts\run.ps1" -ForegroundColor Cyan
