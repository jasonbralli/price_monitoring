$taskName = 'Monitor Precos Peruibe - Diario'
$task = Get-ScheduledTask | Where-Object { $_.TaskName -eq $taskName }
if (-not $task) {
    Write-Host "Task not found: $taskName"
    exit 1
}
Write-Host "TaskName:" $task.TaskName
Write-Host "State:" $task.State
Write-Host "MultipleInstances:" $task.Settings.MultipleInstances
Write-Host "ExecutionTimeLimit:" $task.Settings.ExecutionTimeLimit
Write-Host "StartWhenAvailable:" $task.Settings.StartWhenAvailable
Write-Host "RunOnlyIfNetworkAvailable:" $task.Settings.RunOnlyIfNetworkAvailable
$info = Get-ScheduledTaskInfo -TaskName $taskName
Write-Host "LastRunTime:" $info.LastRunTime
Write-Host "NextRunTime:" $info.NextRunTime
Write-Host "LastTaskResult:" $info.LastTaskResult
Write-Host "NumberOfMissedRuns:" $info.NumberOfMissedRuns
Write-Host 'Actions:'
foreach ($a in $task.Actions) {
    Write-Host "  Execute:" $a.Execute
    Write-Host "  Arguments:" $a.Arguments
}
