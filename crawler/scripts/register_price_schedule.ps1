# Windows 작업 스케줄러 — 매일 04:00 KST 시세 배치 1회
# 관리자 권한 불필요. 시간 변경: -At "06:30"

param(
    [string]$At = "04:00",
    [string]$TaskName = "PokemonCardPrice-DailyBatch"
)

$Script = Join-Path $PSScriptRoot "run_daily_price_batch.ps1"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`""
$Trigger = New-ScheduledTaskTrigger -Daily -At $At
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Settings $Settings -Description "포켓몬 카드 시세 — 3팩씩 일일 배치 크롤" -Force

Write-Host "등록됨: $TaskName — 매일 $At"
Write-Host "확인: Get-ScheduledTask -TaskName $TaskName"
Write-Host "해제: Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
