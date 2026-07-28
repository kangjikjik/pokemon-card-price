# 매일 1회 — KR/JP 확장팩+프로모+박스 시세 크롤 (일별 스냅샷 누적)
# 프로모: KR 배치 끝(KR), JP 배치 끝(JP) — 별도 단계 없음 (crawler/PRICING.md)
# Task Scheduler 등록: register_price_schedule.ps1
# 권장: KST 00:00 (자정)

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Seeds = Join-Path $Root "crawler\seeds"
$Python = Join-Path $Root "crawler\.venv\Scripts\python.exe"
$LogDir = Join-Path $Seeds "_batch_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

if (-not (Test-Path $Python)) {
    throw "Crawler virtualenv Python not found: $Python"
}

$Stamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$LogFile = Join-Path $LogDir "daily_$Stamp.log"

function Invoke-Logged {
    param([string[]]$Cmd)
    Write-Host (">>> " + ($Cmd -join " "))
    & $Cmd[0] $Cmd[1..($Cmd.Length - 1)] 2>&1 | Tee-Object -FilePath $LogFile -Append
    if ($LASTEXITCODE -ne 0) {
        throw "실패 (exit $LASTEXITCODE): $($Cmd -join ' ')"
    }
}

Push-Location $Seeds
try {
    "===== KR all 79 sets $($Stamp) =====" | Tee-Object -FilePath $LogFile
    Invoke-Logged @($Python, "crawl_prices_batch.py", "--apply", "--daily", "--all")

    "" | Tee-Object -FilePath $LogFile -Append
    "===== JP all 79 sets =====" | Tee-Object -FilePath $LogFile -Append
    Invoke-Logged @($Python, "crawl_prices_batch_jp.py", "--apply", "--all", "--fallback")

    "" | Tee-Object -FilePath $LogFile -Append
    "===== KR box prices (all 79 sets) =====" | Tee-Object -FilePath $LogFile -Append
    Invoke-Logged @($Python, "crawl_box_prices_batch.py", "--apply", "--all")

    "" | Tee-Object -FilePath $LogFile -Append
    "===== JP box prices (all 79 sets) =====" | Tee-Object -FilePath $LogFile -Append
    Invoke-Logged @($Python, "crawl_box_prices_batch.py", "--apply", "--all", "--region", "JP")
} finally {
    Pop-Location
}

Write-Host "완료. 로그: $LogFile"
