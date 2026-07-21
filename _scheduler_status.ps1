param()
$ErrorActionPreference = 'Stop'
$taskName = 'Monitor Precos Peruibe - Diario'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $task) { Write-Output 'NOT_FOUND'; exit 0 }
$info = Get-ScheduledTaskInfo -TaskName $taskName
Write-Output ('STATE=' + $task.State)
Write-Output ('LASTRUN=' + $info.LastRunTime)
Write-Output ('NEXTRUN=' + $info.NextRunTime)
Write-Output ('LASTRESULT=' + $info.LastTaskResult)
Write-Output ('MISSED=' + $info.NumberOfMissedRuns)
foreach ($a in $task.Actions) {
    Write-Output ('ACTION_EXECUTE=' + $a.Execute)
    Write-Output ('ACTION_ARGUMENTS=' + $a.Arguments)
}
foreach ($t in $task.Triggers) {
    Write-Output ('TRIGGER=' + $t.CimClass.CimClassName)
    Write-Output ('TRIGGER_START=' + $t.StartBoundary)
    Write-Output ('TRIGGER_ENABLED=' + $t.Enabled)
}
