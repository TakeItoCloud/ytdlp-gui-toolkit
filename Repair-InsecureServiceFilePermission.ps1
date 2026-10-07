#Requires -Version 5.1
<#
.SYNOPSIS
    Detects (and optionally repairs) Windows services whose EXECUTABLE FILE or its CONTAINING
    FOLDER can be modified/overwritten by non-privileged principals - which is what Nessus
    plugin 65057 "Insecure Windows Service Permissions" actually checks. Full logging (.log +
    .csv). Report mode (default) is read-only. Supersedes Repair-InsecureServicePermission.ps1,
    which checked the service OBJECT DACL (a different vector, not plugin 65057).
.DESCRIPTION
    For each service, resolves the .exe path, then inspects the ACL of BOTH the .exe and its
    parent folder. Flags Allow ACEs where a risky principal (Everyone S-1-1-0, Authenticated
    Users S-1-5-11, BUILTIN\Users S-1-5-32-545, or Domain Users *-513) holds a dangerous right
    (Write / WriteData / AppendData / Modify / FullControl / Delete / ChangePermissions /
    TakeOwnership). Apply mode, per target, FIRST saves the original ACL with icacls /save (exact
    rollback), then removes that principal's grant and re-grants Read&Execute only (RX) so the app
    still runs but can no longer be tampered with. ShouldProcess-guarded. No service restart needed.
    Run locally (elevated) or via Invoke-Command. Logs to -LogDirectory on the host it runs on.
.PARAMETER Mode          Report (default, read-only) or Apply.
.PARAMETER LogDirectory  Default C:\ProgramData\IMP1-Logs
.EXAMPLE  .\Repair-InsecureServiceFilePermission.ps1
.EXAMPLE  .\Repair-InsecureServiceFilePermission.ps1 -Mode Apply -WhatIf
.OUTPUTS  PSCustomObject (Service, ExePath, Target, TargetType, Principal, Rights, OriginalSddl, BackupFile, Applied, Mode)
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
    $BackupDir = Join-Path $LogDirectory "aclbackup-$env:COMPUTERNAME-$runStamp"
    $LogFile = Join-Path $LogDirectory "Repair-InsecureServiceFilePermission-$env:COMPUTERNAME-$runStamp.log"
    $CsvFile = Join-Path $LogDirectory "Repair-InsecureServiceFilePermission-$env:COMPUTERNAME-$runStamp.csv"
    function Write-Log {
        param([Parameter(Mandatory)][string]$Message,[ValidateSet('INFO','WARN','ERROR','ACTION','RESULT')][string]$Level='INFO')
        $line = '{0} [{1,-6}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),$Level,$Message
        Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
        if ($Level -eq 'WARN') { Write-Warning $Message } elseif ($Level -eq 'ERROR') { Write-Error $Message -ErrorAction Continue } else { Write-Verbose $line }
    }
    # Risky principals by well-known SID (language-independent); Domain Users matched by *-513.
    $riskySid = @('S-1-1-0','S-1-5-11','S-1-5-32-545')
    # Dangerous ATOMIC bits ONLY - never composite Modify/FullControl, whose read/execute sub-bits
    # would false-positive on ReadAndExecute ACEs. Includes GENERIC_WRITE (0x40000000) and
    # GENERIC_ALL (0x10000000) for ACEs stored with generic rights.
    $dangerBits = [int64](0x00000002 -bor 0x00000004 -bor 0x00000010 -bor 0x00000100 -bor `
                           0x00000040 -bor 0x00010000 -bor 0x00040000 -bor 0x00080000 -bor `
                           0x10000000 -bor 0x40000000)
    $results = New-Object System.Collections.Generic.List[object]

    function Get-ExePath {
        param([string]$PathName)
        if ([string]::IsNullOrWhiteSpace($PathName)) { return $null }
        $p = $PathName.Trim()
        if ($p.StartsWith('"')) { return ($p -split '"')[1] }         # quoted exe
        if ($p -match '^(.*?\.exe)\b') { return $matches[1] }          # first .exe token
        return ($p -split '\s',2)[0]
    }
    function Test-Target {
        param([string]$Target,[string]$TargetType,[string]$Service,[string]$Exe)
        if (-not (Test-Path -LiteralPath $Target)) { return }
        try { $acl = Get-Acl -LiteralPath $Target -ErrorAction Stop } catch { Write-Log "ACL read failed on $Target : $($_.Exception.Message)" 'WARN'; return }
        foreach ($ace in $acl.Access) {
            if ($ace.AccessControlType -ne 'Allow') { continue }
            try { $sid = $ace.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value } catch { $sid = $ace.IdentityReference.Value }
            $isRisky = ($riskySid -contains $sid) -or ($sid -like '*-513')
            if (-not $isRisky) { continue }
            $r = ([int64]([int]$ace.FileSystemRights)) -band 0xFFFFFFFF
            if (($r -band $dangerBits) -eq 0) { continue }
            $o = [pscustomobject]@{
                Service=$Service; ExePath=$Exe; Target=$Target; TargetType=$TargetType
                Principal="$($ace.IdentityReference) [$sid]"; Rights=$ace.FileSystemRights.ToString()
                OriginalSddl=$acl.Sddl; BackupFile=''; Applied=$false; Mode=$Mode; Sid=$sid
            }
            Write-Log "FLAG svc=$Service $TargetType=[$Target] principal=$($ace.IdentityReference) rights=[$($ace.FileSystemRights)]" 'INFO'

            if ($Mode -eq 'Apply') {
                if ($PSCmdlet.ShouldProcess($Target, "Remove $($ace.IdentityReference) write/modify, re-grant Read&Execute")) {
                    try {
                        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
                        $bk = Join-Path $BackupDir ((Split-Path $Target -Leaf) + '-' + [guid]::NewGuid().ToString('N').Substring(0,8) + '.acl')
                        & icacls "$Target" /save "$bk" /c /q | Out-Null     # exact rollback: icacls <parent> /restore "$bk"
                        $o.BackupFile = $bk
                        $inherit = if ($TargetType -eq 'Folder') { '(OI)(CI)(RX)' } else { '(RX)' }
                        & icacls "$Target" /remove:g "*$sid" /c /q | Out-Null
                        & icacls "$Target" /grant   "*${sid}:$inherit" /c /q | Out-Null
                        if ($LASTEXITCODE -ne 0) { throw "icacls exit code $LASTEXITCODE" }
                        $o.Applied = $true
                        Write-Log "FIXED $TargetType=[$Target] principal=$sid -> removed write/modify, granted RX (backup $bk)" 'ACTION'
                    } catch { Write-Log "FAILED $Target ($sid): $($_.Exception.Message)" 'ERROR' }
                }
            }
            $results.Add($o); $o
        }
    }
}

process {
    foreach ($svc in Get-CimInstance -ClassName Win32_Service -ErrorAction SilentlyContinue) {
        $exe = Get-ExePath -PathName $svc.PathName
        if (-not $exe) { continue }
        # Skip OS-trusted locations (System32 etc. are secured by default; focus on third-party apps)
        if ($exe -match '(?i)\\Windows\\') { continue }
        Test-Target -Target $exe -TargetType 'File'   -Service $svc.Name -Exe $exe
        $dir = Split-Path -Path $exe -Parent
        if ($dir) { Test-Target -Target $dir -TargetType 'Folder' -Service $svc.Name -Exe $exe }
    }
}

end {
    if ($results.Count) { $results | Select-Object Service,ExePath,Target,TargetType,Principal,Rights,OriginalSddl,BackupFile,Applied,Mode | Export-Csv -LiteralPath $CsvFile -NoTypeInformation -Encoding UTF8 }
    $fixed = @($results | Where-Object Applied -eq $true).Count
    Write-Log "SUMMARY flagged=$($results.Count) fixed=$fixed Mode=$Mode" 'RESULT'
    Write-Log "Evidence CSV (incl. OriginalSddl + BackupFile for rollback): $CsvFile"
    Write-Information ("[{0}] insecure-service-FILE-perms: flagged {1}, fixed {2} (Mode={3})" -f $env:COMPUTERNAME,$results.Count,$fixed,$Mode)
    Write-Information (" log: {0}" -f $LogFile)
    if ($Mode -eq 'Apply') { Write-Information (" ACL backups (for icacls /restore): {0}" -f $BackupDir) }
}
