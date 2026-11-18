#Requires -Version 5.1
param([switch]$SkipBackup, [switch]$SkipDeviceFolders)

$BackendRoot = "C:\labtrack\backend\LabTrack.CSharp\src"
$OutDir      = "$env:USERPROFILE\Desktop\LabTrack-Diagnostics"
$BackupRoot  = "$env:USERPROFILE\Desktop\LabTrack-Backups"
$DeviceRoot  = "$env:USERPROFILE\Desktop\LabTrack-Devices"
$ErrorActionPreference = "Continue"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"

foreach ($d in @($OutDir, $BackupRoot)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

# Underscore-prefixed = walang alias collision
function _H  { param($t); Write-Host ""; Write-Host ("="*72) -ForegroundColor Magenta; Write-Host "  $t" -ForegroundColor Magenta; Write-Host ("="*72) -ForegroundColor Magenta }
function _OK { param($t); Write-Host "  [OK] $t" -ForegroundColor Green }
function _W  { param($t); Write-Host "  [WARN] $t" -ForegroundColor Yellow }
function _E  { param($t); Write-Host "  [ERR] $t" -ForegroundColor Red }
function _S  { param($t); Write-Host "  $t" -ForegroundColor Gray }

$issues = New-Object System.Collections.ArrayList

# ==================== 1. BACKUP (filtered - works kahit API running) ====================
_H "PHASE 1: BACKUP"
$zipPath = $null
if (-not $SkipBackup) {
    $zipPath = Join-Path $BackupRoot "backend-$stamp.zip"
    try {
        _S "Creating backup (source only - excludes bin/obj)..."
        $tempDir = Join-Path $env:TEMP "ltbk-backup-$stamp"
        if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force }
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

        $fileCount = 0
        Get-ChildItem $BackendRoot -Recurse -File -EA SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\(bin|obj|\.vs)\\' } |
            ForEach-Object {
                $rel = $_.FullName.Substring($BackendRoot.Length + 1)
                $dest = Join-Path $tempDir $rel
                $dir = Split-Path $dest -Parent
                if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
                Copy-Item -LiteralPath $_.FullName -Destination $dest -Force -EA SilentlyContinue
                $fileCount++
            }

        Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath -Force -EA Stop
        Remove-Item $tempDir -Recurse -Force -EA SilentlyContinue
        $sizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
        _OK "Backup: $zipPath ($sizeMB MB, $fileCount files)"
    } catch {
        _W "Backup failed: $_"
        $zipPath = $null
        $ans = Read-Host "  Continue WITHOUT backup? (y/N)"
        if ($ans -notmatch '^[yY]') { _E "Aborted"; exit 1 }
        _W "Continuing without backup"
    }
} else {
    _W "Backup skipped (-SkipBackup)"
}

# ==================== 2. DIAGNOSE ====================
_H "PHASE 2: DIAGNOSE"

_S ""; _S "[A] Projects:"
$projects = Get-ChildItem $BackendRoot -Directory | Select-Object -ExpandProperty Name
_S "    $($projects -join ', ')"

_S ""; _S "[B] Empty folders:"
$emptyFolders = @()
Get-ChildItem $BackendRoot -Recurse -Directory -EA SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\\(obj|bin|\.vs)\\' } |
    ForEach-Object {
        $files = @(Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue |
                   Where-Object { $_.FullName -notmatch '\\(obj|bin)\\' })
        if ($files.Count -eq 0) { $emptyFolders += $_.FullName }
    }
if ($emptyFolders.Count -eq 0) { _OK "None" }
else {
    _W "$($emptyFolders.Count) found"
    foreach ($f in $emptyFolders) { _S "    $($f.Replace($BackendRoot,'.'))" }
    [void]$issues.Add("$($emptyFolders.Count) empty folders")
}

_S ""; _S "[C] Duplicate services (Api vs Application):"
$apiSvcDir = Join-Path $BackendRoot "LabTrack.Api\Services"
$appSvcDir = Join-Path $BackendRoot "LabTrack.Application\Services"
$dupServices = @()
if ((Test-Path $apiSvcDir) -and (Test-Path $appSvcDir)) {
    Get-ChildItem $apiSvcDir -Filter "*.cs" | ForEach-Object {
        $counter = Join-Path $appSvcDir $_.Name
        if (Test-Path $counter) {
            $apiL = (Get-Content $_.FullName).Count
            $appL = (Get-Content $counter).Count
            $same = ((Get-Content $_.FullName -Raw) -eq (Get-Content $counter -Raw))
            $dupServices += [pscustomobject]@{ Name = $_.BaseName; ApiLines = $apiL; AppLines = $appL; Identical = $same }
        }
    }
}
if ($dupServices.Count -eq 0) { _OK "None" }
else {
    _W "$($dupServices.Count) found (REPORT ONLY - manual merge)"
    foreach ($s in $dupServices) {
        _S ("    {0,-30} Api:{1,4}L App:{2,4}L Same:{3}" -f $s.Name, $s.ApiLines, $s.AppLines, $s.Identical)
    }
    [void]$issues.Add("$($dupServices.Count) duplicate services (manual)")
}

_S ""; _S "[D] Inline interfaces:"
$ctrlDir = Join-Path $BackendRoot "LabTrack.Api\Controllers"
$inlineIfaces = @()
if (Test-Path $ctrlDir) {
    Get-ChildItem $ctrlDir -Filter "*Controller.cs" | ForEach-Object {
        $c = Get-Content $_.FullName -Raw
        $m = [regex]::Matches($c, 'public\s+interface\s+(I\w+Service)')
        foreach ($x in $m) {
            $inlineIfaces += [pscustomobject]@{ Controller = $_.BaseName; Interface = $x.Groups[1].Value }
            _S "    $($_.BaseName) -> $($x.Groups[1].Value)"
        }
    }
}
if ($inlineIfaces.Count -eq 0) { _OK "None" }
else {
    _W "$($inlineIfaces.Count) found (will extract to stubs)"
    [void]$issues.Add("$($inlineIfaces.Count) inline interfaces")
}

_S ""; _S "[E] Entity usage:"
$entDir = Join-Path $BackendRoot "LabTrack.Domain\Entities"
$unusedEntities = @()
if (Test-Path $entDir) {
    $allCs = @(Get-ChildItem $BackendRoot -Recurse -Filter "*.cs" -EA SilentlyContinue |
               Where-Object { $_.FullName -notmatch '\\(obj|bin)\\' })
    $cache = @{}
    foreach ($f in $allCs) { $cache[$f.FullName] = Get-Content $f.FullName -Raw -EA SilentlyContinue }
    Get-ChildItem $entDir -Filter "*.cs" | ForEach-Object {
        $entFile = $_.FullName
        $name = $_.BaseName
        $pattern = "\b$([regex]::Escape($name))\b"
        $refs = 0
        foreach ($kv in $cache.GetEnumerator()) {
            if ($kv.Key -eq $entFile) { continue }
            if ($kv.Value -match $pattern) { $refs++ }
        }
        if ($refs -eq 0) { _E "  $name -> 0 refs (UNUSED)"; $unusedEntities += $name }
        elseif ($refs -le 2) { _W "  $name -> $refs refs" }
        else { _S "  $name -> $refs refs" }
    }
}
if ($unusedEntities.Count -gt 0) {
    [void]$issues.Add("$($unusedEntities.Count) unused entities: $($unusedEntities -join ', ')")
}

_S ""; _S "[F] Program.cs:"
$prog = Join-Path $BackendRoot "LabTrack.Api\Program.cs"
$needsBind = $false
if (Test-Path $prog) {
    $raw = Get-Content $prog -Raw
    if ($raw -match 'UseUrls\s*\(|0\.0\.0\.0') { _OK "0.0.0.0 bind present" }
    else { _W "0.0.0.0 bind MISSING"; $needsBind = $true; [void]$issues.Add("0.0.0.0 bind missing") }
    if (($raw -match 'AddCors') -and ($raw -match 'UseCors')) { _OK "CORS configured" }
    else { _W "CORS incomplete" }
}

_S ""; _S "[G] Secrets in appsettings:"
$apiDir = Join-Path $BackendRoot "LabTrack.Api"
if (Test-Path $apiDir) {
    Get-ChildItem $apiDir -Filter "appsettings*.json" -EA SilentlyContinue | ForEach-Object {
        $raw = Get-Content $_.FullName -Raw -EA SilentlyContinue
        if ($raw -match 'Password=') { _W "$($_.Name) has hardcoded password"; [void]$issues.Add("$($_.Name) password") }
    }
}

_S ""; _S "[H] .gitignore:"
$gitignore = "C:\labtrack\backend\.gitignore"
if (Test-Path $gitignore) { _OK "exists" }
else { _W "MISSING"; [void]$issues.Add(".gitignore missing") }

# ==================== 3. CLEANUP (additive, safe) ====================
_H "PHASE 3: CLEANUP"

_S ""; _S "[3.1] Delete empty folders:"
if ($emptyFolders.Count -eq 0) { _OK "Nothing" }
else {
    $deleted = 0
    foreach ($f in $emptyFolders) {
        try { Remove-Item -LiteralPath $f -Recurse -Force -EA Stop; $deleted++ }
        catch { _W "Failed: $f" }
    }
    _OK "Deleted: $deleted folders"
}

_S ""; _S "[3.2] .gitignore:"
$required = @('bin/','obj/','*.user','.vs/','appsettings.Development.json','appsettings.Local.json','*.db','*.sqlite','*.log')
if (-not (Test-Path $gitignore)) {
    $required | Out-File $gitignore -Encoding UTF8
    _OK "Created"
} else {
    $existing = Get-Content $gitignore -Raw
    $added = 0
    foreach ($r in $required) {
        if ($existing -notmatch [regex]::Escape($r)) { Add-Content $gitignore $r; $added++ }
    }
    if ($added -gt 0) { _OK "Appended $added lines" } else { _OK "Already complete" }
}

# ==================== 4. MVC FOLDERS ====================
_H "PHASE 4: MVC FOLDERS"
$api = Join-Path $BackendRoot "LabTrack.Api"
$app = Join-Path $BackendRoot "LabTrack.Application"
$dom = Join-Path $BackendRoot "LabTrack.Domain"
$inf = Join-Path $BackendRoot "LabTrack.Infrastructure"

$needed = @(
    (Join-Path $api "Models")
    (Join-Path $api "ViewModels")
    (Join-Path $app "Interfaces")
    (Join-Path $app "DTOs")
    (Join-Path $dom "Interfaces")
    (Join-Path $inf "Repositories")
)
$created = 0
foreach ($f in $needed) {
    if (-not (Test-Path $f)) {
        New-Item -ItemType Directory -Path $f -Force | Out-Null
        _OK "Created: $($f.Replace($BackendRoot,'.'))"
        $created++
    } else {
        _S "Exists: $($f.Replace($BackendRoot,'.'))"
    }
}
if ($created -eq 0) { _OK "All MVC folders exist" }

# ==================== 5. INTERFACE STUBS ====================
_H "PHASE 5: INTERFACE STUBS"
$ifaceDir = Join-Path $app "Interfaces"
$stubsCreated = 0
$stubsSkipped = 0

foreach ($row in $inlineIfaces) {
    $ifName = $row.Interface
    $target = Join-Path $ifaceDir "$ifName.cs"
    if (Test-Path $target) { _S "Exists: $ifName.cs"; $stubsSkipped++; continue }
    $stub = "// Auto-generated stub`r`n// Source: $($row.Controller).cs`r`n// TODO: Copy method signatures from controller, then remove from controller`r`nnamespace LabTrack.Application.Interfaces;`r`n`r`npublic interface $ifName`r`n{`r`n    // methods go here`r`n}`r`n"
    try {
        $stub | Out-File $target -Encoding UTF8
        _OK "Created: $ifName.cs (from $($row.Controller))"
        $stubsCreated++
    } catch {
        _E "Failed: $ifName.cs - $_"
    }
}
_S "Total: $stubsCreated created, $stubsSkipped skipped"

# ==================== 6. DEVICE FOLDERS ====================
if (-not $SkipDeviceFolders) {
    _H "PHASE 6: DEVICE FOLDERS"
    $devices = @(
        @{ N="01-iPhone";           D="iPhone 12-15 - iOS 16+, Safari+PWA" }
        @{ N="02-iPad";             D="iPad Air/Pro - iOS 16+" }
        @{ N="03-Android-Phone";    D="Pixel/Samsung - Android 12+" }
        @{ N="04-Android-Tablet";   D="Galaxy Tab - Android 12+" }
        @{ N="05-Web-Desktop";      D="1920x1080, 1440x900 - Chrome/Edge/FF" }
        @{ N="06-Web-Mobile";       D="Responsive 375/390/414" }
        @{ N="07-Mac-Safari";       D="macOS Safari 16+" }
        @{ N="08-Smart-TV";         D="Android TV / WebOS / Tizen" }
        @{ N="09-Shared";           D="Shared assets" }
        @{ N="10-Test-Screenshots"; D="Bug evidence" }
    )
    if (-not (Test-Path $DeviceRoot)) { New-Item -ItemType Directory -Path $DeviceRoot -Force | Out-Null }
    $devCreated = 0
    foreach ($d in $devices) {
        $p = Join-Path $DeviceRoot $d.N
        if (-not (Test-Path $p)) {
            New-Item -ItemType Directory -Path $p -Force | Out-Null
            foreach ($sub in @('Screenshots','Assets','Reports','Configs')) {
                New-Item -ItemType Directory -Path (Join-Path $p $sub) -Force | Out-Null
            }
            $d.D | Out-File (Join-Path $p 'README.md') -Encoding UTF8
            _OK "Created: $($d.N)"
            $devCreated++
        } else {
            _S "Exists: $($d.N)"
        }
    }
    _S "Total: $devCreated new"
}

# ==================== 7. REPORT ====================
_H "PHASE 7: FINAL REPORT"
$reportTxt = Join-Path $OutDir "organize-report-$stamp.txt"
$r = @()
$r += "LabTrack Backend Organize Report"
$r += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$r += "Backend: $BackendRoot"
$r += ""
$r += "SUMMARY"
$r += "  Empty folders: $($emptyFolders.Count)"
$r += "  Duplicate services: $($dupServices.Count)"
$r += "  Inline interfaces: $($inlineIfaces.Count)"
$r += "  Unused entities: $($unusedEntities.Count)"
$r += "  Stubs created: $stubsCreated"
$r += ""
if ($unusedEntities.Count -gt 0) {
    $r += "UNUSED ENTITIES (verify before delete):"
    foreach ($e in $unusedEntities) { $r += "  - $e" }
    $r += ""
}
if ($dupServices.Count -gt 0) {
    $r += "DUPLICATE SERVICES (manual merge):"
    foreach ($s in $dupServices) {
        $action = if ($s.Identical) { "DELETE Api copy" }
                 elseif ($s.AppLines -gt $s.ApiLines) { "KEEP App" }
                 else { "REVIEW" }
        $r += "  - $($s.Name): Api=$($s.ApiLines)L App=$($s.AppLines)L -> $action"
    }
    $r += ""
}
$r | Out-File $reportTxt -Encoding UTF8
_OK "Report: $reportTxt"

_S ""
_S "Manual follow-ups:"
if ($dupServices.Count -gt 0)    { _W "  - Merge $($dupServices.Count) duplicate services" }
if ($stubsCreated -gt 0)         { _W "  - Fill $stubsCreated stubs with method signatures" }
if ($unusedEntities.Count -gt 0) { _W "  - Verify unused: $($unusedEntities -join ', ')" }
if ($needsBind) {
    _W "  - Add to Program.cs after CreateBuilder:"
    _S '      builder.WebHost.UseUrls("http://0.0.0.0:5000");'
}

Write-Host ""
Write-Host ("="*72) -ForegroundColor Green
Write-Host "  ORGANIZE COMPLETE" -ForegroundColor Green
Write-Host ("="*72) -ForegroundColor Green
if ($zipPath)   { Write-Host "  Backup: $zipPath" -ForegroundColor Cyan }
Write-Host "  Report: $reportTxt" -ForegroundColor Cyan
Write-Host ""
