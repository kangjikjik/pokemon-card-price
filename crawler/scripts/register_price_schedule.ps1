# Register the local daily price crawl at midnight (KST).
# Primary scheduler — GitHub Actions cron is disabled (403 from cloud IPs).

param(
    [string]$At = "00:00",
    [string]$TaskName = "PokemonCardPrice-DailyBatch"
)

$Script = Join-Path $PSScriptRoot "run_daily_price_batch.ps1"
$Argument = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $Script
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $Argument
$Trigger = New-ScheduledTaskTrigger -Daily -At $At
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 8)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Settings $Settings -Description "Pokemon prices - daily KR/JP full crawl" -Force

Write-Host "Registered: $TaskName at $At daily"
Write-Host "Inspect: Get-ScheduledTask -TaskName $TaskName"
Write-Host ('Remove: Unregister-ScheduledTask -TaskName {0} -Confirm:$false' -f $TaskName)
Write-Host "GitHub Actions cron is disabled; this local task is the primary scheduler."
