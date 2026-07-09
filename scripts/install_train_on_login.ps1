$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = "python"
$taskName = "ResearchMind Local SLM Training"
$command = "cd `"$projectRoot`"; $python researchmind_cli.py train-local --iters 300"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"$command`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Train ResearchMind local SLM from model/data/train_data.txt after login." -Force
Write-Host "Installed scheduled task: $taskName"
