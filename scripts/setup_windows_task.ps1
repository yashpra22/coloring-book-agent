# ═══════════════════════════════════════════════════════════
#  Windows Task Scheduler Setup Script
#  Run this in PowerShell as Administrator
# ═══════════════════════════════════════════════════════════

$ProjectDir = "c:\Users\titangrey\Desktop\Image generator\coloring-book-agent"
$TaskName = "DailyColoringBook"
$PythonExe = (Get-Command python).Source

# Check if task already exists
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Task '$TaskName' already exists. Removing..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create action — run main.py
$action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "main.py" `
    -WorkingDirectory $ProjectDir

# Create trigger — daily at 6 AM
$trigger = New-ScheduledTaskTrigger -Daily -At 6:00AM

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3)

# Create principal (run whether logged in or not)
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Highest

# Register the task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Daily automated coloring book PDF generation for kids" `
    -Force

Write-Host ""
Write-Host "✅ Task '$TaskName' registered successfully!" -ForegroundColor Green
Write-Host "   Schedule: Daily at 6:00 AM"
Write-Host "   Command:  $PythonExe main.py"
Write-Host "   Directory: $ProjectDir"
Write-Host ""
Write-Host "To test now, run: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "To remove, run:  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
