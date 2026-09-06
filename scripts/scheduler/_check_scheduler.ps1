$tasks = Get-ScheduledTask | Where-Object { $_.TaskName -like 'Monitor Pre*' }

if (-not $tasks) {
    Write-Host 'No matching tasks found.'
    exit 0
}

foreach ($task in $tasks) {
    Write-Host "--- $($task.TaskName) ---"
    $task | Format-List TaskName, State, TaskPath
    $info = Get-ScheduledTaskInfo -TaskName $task.TaskName
    $info | Format-List LastRunTime, NextRunTime, LastTaskResult, NumberOfMissedRuns, Status
    Write-Host 'Actions:'
    foreach ($a in $task.Actions) {
        Write-Host "  $($a.Execute) $($a.Arguments)"
    }
    $task.Triggers | Format-List CimClass.CimClassName, StartBoundary, Enabled
    Write-Host ''
}
