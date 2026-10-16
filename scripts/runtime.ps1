function Stop-juridIAProcessTree([System.Diagnostics.Process]$Process) {
    if ($Process.HasExited) { return }
    $startedAt = $Process.StartTime
    foreach ($childRow in @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $($Process.Id)")) {
        $child = Get-Process -Id $childRow.ProcessId -ErrorAction SilentlyContinue
        if ($child -and $child.StartTime -ge $startedAt) { Stop-juridIAProcessTree $child }
    }
    if (-not $Process.HasExited) { Stop-Process -Id $Process.Id -ErrorAction SilentlyContinue }
}
