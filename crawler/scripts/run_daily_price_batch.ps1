# KR/JP 확장팩+프로모+박스 시세 크롤 (catch-up, 마지막 크롤 다음날~오늘)
# 번개장터 전용 (Collectory · 유유테이 제거)
# 자동 간격은 4일 (§15). GitHub Actions schedule이 그때 돈다.
# 로컬 예약은 register_price_schedule.ps1 을 실행할 때만 등록된다.

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
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
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Cmd[0] $Cmd[1..($Cmd.Length - 1)] 2>&1 |
            ForEach-Object {
                if ($_ -is [System.Management.Automation.ErrorRecord]) {
                    $_.ToString()
                } else {
                    $_
                }
            } |
            Tee-Object -FilePath $LogFile -Append
    } finally {
        $ErrorActionPreference = $prevEap
    }
    if ($LASTEXITCODE -ne 0) {
        throw "실패 (exit $LASTEXITCODE): $($Cmd -join ' ')"
    }
}

Push-Location $Seeds
try {
    "===== KR all 80 sets $($Stamp) =====" | Tee-Object -FilePath $LogFile
    Invoke-Logged @($Python, "crawl_prices_batch.py", "--apply", "--daily", "--all")

    "" | Tee-Object -FilePath $LogFile -Append
    "===== JP all 82 sets =====" | Tee-Object -FilePath $LogFile -Append
    Invoke-Logged @($Python, "crawl_prices_batch_jp.py", "--apply", "--all")

    "" | Tee-Object -FilePath $LogFile -Append
    "===== KR box prices (all 82 sets) =====" | Tee-Object -FilePath $LogFile -Append
    Invoke-Logged @($Python, "crawl_box_prices_batch.py", "--apply", "--all")

    "" | Tee-Object -FilePath $LogFile -Append
    "===== JP box prices (all 82 sets) =====" | Tee-Object -FilePath $LogFile -Append
    Invoke-Logged @($Python, "crawl_box_prices_batch.py", "--apply", "--all", "--region", "JP")

    "" | Tee-Object -FilePath $LogFile -Append
    "===== Home highlights from views =====" | Tee-Object -FilePath $LogFile -Append
    Invoke-Logged @($Python, "update_home_highlights.py", "--apply")
} finally {
    Pop-Location
}

Write-Host "완료. 로그: $LogFile"
