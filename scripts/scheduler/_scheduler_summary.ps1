[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$tasks = @(Get-ScheduledTask | Where-Object { $_.TaskName -like 'Monitor Pre*' })
if (-not $tasks) { Write-Output 'No matching tasks found.'; exit 0 }
foreach ($t in $tasks) {
    Write-Output ('TASK=' + $t.TaskName)
    Write-Output ('STATE=' + $t.State)
    $info = Get-ScheduledTaskInfo -TaskName $t.TaskName
    Write-Output ('LASTRUN=' + $info.LastRunTime)
    Write-Output ('NEXTRUN=' + $info.NextRunTime)
    Write-Output ('LASTRESULT=' + $info.LastTaskResult)
    foreach ($a in $t.Actions) { Write-Output ('ACTION_EXECUTE=' + $a.Execute); Write-Output ('ACTION_ARGUMENTS=' + $a.Arguments) }
    foreach ($tr in $t.Triggers) { Write-Output ('TRIGGER=' + $tr.CimClass.CimClassName); Write-Output ('START=' + $tr.StartBoundary) }
    Write-Output ''
}
