# 로컬 시세 크롤을 4일마다 자정(KST)에 등록하는 스크립트.
# 이 파일을 실행하기 전에는 이 PC 예약은 등록되지 않는다. GitHub Actions 4일 예약은 켜 둔다.
# 간격: TRADE_CRAWL_CRITERIA.md §15 (4일, catch-up으로 빈 날 보충)

param(
    [string]$At = "00:00",
    [string]$TaskName = "PokemonCardPrice-DailyBatch"
)

$Script = Join-Path $PSScriptRoot "run_daily_price_batch.ps1"
$Argument = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $Script
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $Argument
$Trigger = New-ScheduledTaskTrigger -Daily -DaysInterval 4 -At $At
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 8)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Settings $Settings -Description "Pokemon prices - every 4 days KR/JP cards+promo+box crawl" -Force

Write-Host "Registered: $TaskName at $At every 4 days"
Write-Host "Inspect: Get-ScheduledTask -TaskName $TaskName"
Write-Host ('Remove: Unregister-ScheduledTask -TaskName {0} -Confirm:$false' -f $TaskName)
Write-Host "GitHub Actions schedule is still off. This script only registers a local task when run."
