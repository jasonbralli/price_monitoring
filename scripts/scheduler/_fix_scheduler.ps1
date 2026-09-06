param()
$ErrorActionPreference = 'Stop'
$bat = 'C:\Users\Jason\Desktop\PROJETOS\03 - DONE\price_monitoring\scripts\run_coleta.bat'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$task = Get-ScheduledTask | Where-Object { $_.TaskName -like 'Monitor Pre*' }
if (-not $task) {
    Write-Output 'No matching tasks found.'
    exit 0
}
$fixed = $false
foreach ($t in $task) {
    $hasBat = $false
    foreach ($a in $t.Actions) {
        if ($a.Arguments -like '*run_coleta.bat*') { $hasBat = $true }
    }
    if (-not $hasBat) {
        $t.Actions.Clear() | Out-Null
        $t.Actions.Add((New-ScheduledTaskAction -Execute $bat)) > $null
        $fixed = $true
    }
    if ($t.Settings.StartWhenAvailable -ne $true) { $t.Settings.StartWhenAvailable = $true; $fixed = $true }
    if ($t.Settings.RunOnlyIfNetworkAvailable -ne $true) { $t.Settings.RunOnlyIfNetworkAvailable = $true; $fixed = $true }
    if ($t.Settings.ExecutionTimeLimit -ne 'PT01H') { $t.Settings.ExecutionTimeLimit = 'PT01H'; $fixed = $true }
    if ($t.Settings.MultipleInstances -ne 'IgnoreNew') { $t.Settings.MultipleInstances = 'IgnoreNew'; $fixed = $true }
    if ($fixed) { Set-ScheduledTask -InputObject $t | Out-Null }
}
Write-Output ('fixed=' + ($fixed.ToString().ToLower()))
