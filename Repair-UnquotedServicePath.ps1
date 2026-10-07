#Requires -Version 5.1
<#
.SYNOPSIS
    Detects (and optionally repairs) Windows services whose ImagePath is unquoted and contains
    spaces - the unquoted service path privilege-escalation vector (Nessus plugin 63155). Full
    logging: writes a structured .log and evidence .csv per run. Report mode is read-only.
.DESCRIPTION
    Enumerates services via CIM, isolates the executable token, flags any unquoted path with a
    space. Apply mode rewrites ImagePath with the executable quoted, preserving arguments and the
    REG_EXPAND_SZ type, via ShouldProcess. Runs locally (elevated) or through Invoke-Command;
    logs under -LogDirectory (default C:\ProgramData\IMP1-Logs) on the host it runs on.
.PARAMETER Mode  Report (default, read-only) or Apply.
.PARAMETER LogDirectory  Default C:\ProgramData\IMP1-Logs
.EXAMPLE  .\Repair-UnquotedServicePath.ps1
.EXAMPLE  .\Repair-UnquotedServicePath.ps1 -Mode Apply -WhatIf
.OUTPUTS  PSCustomObject (Service, StartMode, Original, Proposed, Applied, Mode)
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
[OutputType([pscustomobject])]
param(
    [ValidateSet('Report','Apply')][string]$Mode = 'Report',
    [string]$LogDirectory = 'C:\ProgramData\IMP1-Logs'
)

begin {
    $InformationPreference = 'Continue'
    $runStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
    $LogFile = Join-Path $LogDirectory "Repair-UnquotedServicePath-$env:COMPUTERNAME-$runStamp.log"
    $CsvFile = Join-Path $LogDirectory "Repair-UnquotedServicePath-$env:COMPUTERNAME-$runStamp.csv"
    function Write-Log {
        param([Parameter(Mandatory)][string]$Message,[ValidateSet('INFO','WARN','ERROR','ACTION','RESULT')][string]$Level='INFO')
        $line = '{0} [{1,-6}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),$Level,$Message
        Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
        if ($Level -eq 'WARN') { Write-Warning $Message } elseif ($Level -eq 'ERROR') { Write-Error $Message -ErrorAction Continue } else { Write-Verbose $line }
    }
    $results = New-Object System.Collections.Generic.List[object]
    Write-Log "=== Repair-UnquotedServicePath Mode=$Mode on $env:COMPUTERNAME by $env:USERNAME (WhatIf=$WhatIfPreference) ==="
}

process {
    try { $services = Get-CimInstance -ClassName Win32_Service -ErrorAction Stop }
    catch { Write-Log "Unable to enumerate services: $($_.Exception.Message)" 'ERROR'; throw }

    foreach ($svc in $services) {
        $path = $svc.PathName
        if ([string]::IsNullOrWhiteSpace($path)) { continue }
        if ($path.TrimStart().StartsWith('"')) { continue }
        if ($path -notmatch '\.exe') { continue }
        $exe = ($path -split '(?<=\.exe)', 2)[0]
        if ($exe -notmatch '\s') { continue }

        $newPath = '"' + $exe + '"' + $path.Substring($exe.Length)
        $applied = $false
        Write-Log "FLAG $($svc.Name) [$($svc.StartMode)] Original=[$path]" 'INFO'
        if ($Mode -eq 'Apply') {
            if ($PSCmdlet.ShouldProcess($svc.Name, "Quote ImagePath to [$newPath]")) {
                try {
                    # Set-ItemProperty handles quotes+spaces natively (reg.exe breaks on them)
                    # and -Type ExpandString preserves the REG_EXPAND_SZ type.
                    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$($svc.Name)" `
                        -Name ImagePath -Value $newPath -Type ExpandString -ErrorAction Stop
                    $applied = $true
                    Write-Log "FIXED $($svc.Name) -> [$newPath]" 'ACTION'
                } catch { Write-Log "FAILED $($svc.Name): $($_.Exception.Message)" 'ERROR' }
            }
        }
        $o = [pscustomobject]@{ Service=$svc.Name; StartMode=$svc.StartMode; Original=$path; Proposed=$newPath; Applied=$applied; Mode=$Mode }
        $results.Add($o); $o
    }
}

end {
    if ($results.Count) { $results | Export-Csv -LiteralPath $CsvFile -NoTypeInformation -Encoding UTF8 }
    $fixed = @($results | Where-Object Applied -eq $true).Count
    Write-Log "SUMMARY flagged=$($results.Count) fixed=$fixed Mode=$Mode" 'RESULT'
    Write-Log "Evidence CSV: $CsvFile"
    Write-Information ("[{0}] unquoted-path: flagged {1}, fixed {2} (Mode={3})" -f $env:COMPUTERNAME,$results.Count,$fixed,$Mode)
    Write-Information (" log: {0}" -f $LogFile)
}
