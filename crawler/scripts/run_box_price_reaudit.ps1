# 박스 시세 전체 재크롤 (백그라운드)
# 이미지 검증 + 거래완료 우선(90일) → 호가
# 완료 시 _batch_logs/box_reaudit_<stamp>.done 생성

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
$LogFile = Join-Path $LogDir "box_reaudit_$Stamp.log"
$DoneFile = Join-Path $LogDir "box_reaudit_$Stamp.done"

Push-Location $Seeds
try {
    "===== KR box reaudit $Stamp =====" | Out-File -FilePath $LogFile -Encoding utf8
    & $Python crawl_box_prices.py --apply --all --quiet 2>&1 | Tee-Object -FilePath $LogFile -Append
    if ($LASTEXITCODE -ne 0) { throw "KR box crawl failed (exit $LASTEXITCODE)" }

    "" | Tee-Object -FilePath $LogFile -Append
    "===== JP box reaudit =====" | Tee-Object -FilePath $LogFile -Append
    & $Python crawl_box_prices.py --apply --all --region JP --quiet 2>&1 | Tee-Object -FilePath $LogFile -Append
    if ($LASTEXITCODE -ne 0) { throw "JP box crawl failed (exit $LASTEXITCODE)" }

    @{
        finished_at = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        log = $LogFile
        policy = "image_verify + sold_90d_then_listing"
    } | ConvertTo-Json | Out-File -FilePath $DoneFile -Encoding utf8

    "DONE box reaudit $Stamp" | Tee-Object -FilePath $LogFile -Append
} catch {
    "FAILED: $_" | Tee-Object -FilePath $LogFile -Append
    exit 1
} finally {
    Pop-Location
}
