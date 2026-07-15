# 매일 1회 — 다음 3팩 시세 배치 크롤 (빠른 모드)
# Task Scheduler 등록: register_price_schedule.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Seeds = Join-Path $Root "crawler\seeds"
$LogDir = Join-Path $Seeds "_batch_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Stamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$LogFile = Join-Path $LogDir "batch_$Stamp.log"

Push-Location $Seeds
try {
    python crawl_prices_batch.py --apply 2>&1 | Tee-Object -FilePath $LogFile
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($code -ne 0) {
    Write-Error "배치 크롤 실패 (exit $code). 로그: $LogFile"
}
Write-Host "완료. 로그: $LogFile"
