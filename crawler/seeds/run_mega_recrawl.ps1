# MEGA 5팩 + MG6 전체 재크롤 (트레이너 동기화 → SNK 제거 → KR/JP/박스)
$ErrorActionPreference = "Stop"
$Sets = @("MG7", "MG6", "MG5a", "MG5", "MG4a", "MG4")
$Root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $Root "seeds")

Write-Host "=== 1/4 트레이너·아이템 공식명/이미지 ===" -ForegroundColor Cyan
python sync_mega_trainer_kr.py --apply
python fix_mg6_trainer_item_kr.py --apply
python fix_mg7_trainer_kr.py --apply

Write-Host "`n=== 2/4 SNKRDUNK DB purge ===" -ForegroundColor Cyan
python purge_mega_snk.py --apply

foreach ($code in $Sets) {
    Write-Host "`n=== [$code] KR 카드 ===" -ForegroundColor Yellow
    python crawl_set_prices.py --set $code --apply --quiet

    Write-Host "=== [$code] JP 카드 (번개만) ===" -ForegroundColor Yellow
    python crawl_set_prices_jp.py --set $code --apply --quiet

    Write-Host "=== [$code] KR 박스 ===" -ForegroundColor Yellow
    python crawl_box_prices.py --set $code --apply --quiet

    Write-Host "=== [$code] JP 박스 ===" -ForegroundColor Yellow
    python crawl_box_prices.py --set $code --region JP --apply --quiet
}

Write-Host "`n완료" -ForegroundColor Green
