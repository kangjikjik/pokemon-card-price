# 매일 1회 — KR/JP 전 79팩 시세 크롤 (일별 스냅샷 누적)
# Task Scheduler 등록: register_price_schedule.ps1
# 권장: KST 00:00 (자정)

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Seeds = Join-Path $Root "crawler\seeds"
$LogDir = Join-Path $Seeds "_batch_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

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
    Invoke-Logged @("python", "crawl_prices_batch.py", "--apply", "--daily", "--all")

    "" | Tee-Object -FilePath $LogFile -Append
    "===== JP all 79 sets (5-set groups) =====" | Tee-Object -FilePath $LogFile -Append
    Invoke-Logged @("python", "crawl_prices_batch_jp.py", "--apply", "--all", "--size", "5", "--pause", "60")
} finally {
    Pop-Location
}

Write-Host "완료. 로그: $LogFile"
