$ErrorActionPreference = "Continue"
$BackupZip = "$env:USERPROFILE\Desktop\LabTrack-Backups\backend-20261111-231524.zip"
$SrcDir = "C:\labtrack\backend\LabTrack.CSharp\src"

Write-Host ""
Write-Host ("=" * 72) -ForegroundColor Cyan
Write-Host "  RESTORE FROM BACKUP" -ForegroundColor Cyan
Write-Host ("=" * 72) -ForegroundColor Cyan

if (-not (Test-Path $BackupZip)) {
    Write-Host "  [ERR] Backup not found: $BackupZip" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Available backups:" -ForegroundColor Yellow
    Get-ChildItem "$env:USERPROFILE\Desktop\LabTrack-Backups" -Filter "*.zip" -EA SilentlyContinue |
        Sort-Object LastWriteTime |
        Format-Table Name, @{N='MB';E={[math]::Round($_.Length/1MB,2)}}, LastWriteTime
    exit 1
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

# Save damaged state
$damagedPath = "$env:USERPROFILE\Desktop\LabTrack-Damaged-$stamp"
Write-Host "  Saving damaged state -> $damagedPath" -ForegroundColor Yellow
Move-Item $SrcDir $damagedPath -Force
Write-Host "  [OK] Damaged saved" -ForegroundColor Green

# Extract
$extractTo = Join-Path $env:TEMP "restore-$stamp"
Write-Host "  Extracting: $BackupZip" -ForegroundColor Gray
Expand-Archive -Path $BackupZip -DestinationPath $extractTo -Force

# Move to src
Write-Host "  Restoring -> $SrcDir" -ForegroundColor Gray
Copy-Item $extractTo $SrcDir -Recurse -Force
Remove-Item $extractTo -Recurse -Force
Write-Host "  [OK] Restored" -ForegroundColor Green

# Verify projects
Write-Host ""
Write-Host "  Restored projects:" -ForegroundColor Cyan
Get-ChildItem $SrcDir -Directory | ForEach-Object { Write-Host "    $($_.Name)" -ForegroundColor Gray }

# Build
Write-Host ""
Write-Host ("=" * 72) -ForegroundColor Cyan
Write-Host "  BUILD VERIFY" -ForegroundColor Cyan
Write-Host ("=" * 72) -ForegroundColor Cyan

$sln = Get-ChildItem "C:\labtrack\backend" -Filter "*.sln*" -Recurse -EA SilentlyContinue | Select-Object -First 1
$target = if ($sln) { $sln.FullName } else { Join-Path $SrcDir "LabTrack.Api\LabTrack.Api.csproj" }

Write-Host "  Building: $target" -ForegroundColor Gray
Write-Host ""

$output = & dotnet build $target --nologo 2>&1
$exit = $LASTEXITCODE

$output | ForEach-Object {
    if ($_ -match '\berror\b')  { Write-Host $_ -ForegroundColor Red }
    elseif ($_ -match '\bwarn') { Write-Host $_ -ForegroundColor Yellow }
    else                        { Write-Host $_ -ForegroundColor Gray }
}

Write-Host ""
if ($exit -eq 0) {
    Write-Host ("=" * 72) -ForegroundColor Green
    Write-Host "  BUILD SUCCEEDED - RESTORED TO WORKING STATE" -ForegroundColor Green
    Write-Host ("=" * 72) -ForegroundColor Green
    Write-Host ""
    Write-Host "  Damaged copy: $damagedPath" -ForegroundColor Yellow
    Write-Host "  (pwede mong i-compare kung may changes na gusto mong i-keep)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Ready for PROPER per-controller migration." -ForegroundColor Cyan
} else {
    Write-Host ("=" * 72) -ForegroundColor Red
    Write-Host "  BUILD FAILED even after restore (exit $exit)" -ForegroundColor Red
    Write-Host ("=" * 72) -ForegroundColor Red
    Write-Host ""
    Write-Host "  Ibig sabihin: ang backup ay na-capture AFTER damage." -ForegroundColor Yellow
    Write-Host "  Check earlier backups:" -ForegroundColor Yellow
    Get-ChildItem "$env:USERPROFILE\Desktop\LabTrack-Backups" -Filter "*.zip" -EA SilentlyContinue |
        Sort-Object LastWriteTime |
        Format-Table Name, LastWriteTime
    Write-Host ""
    Write-Host "  Damaged copy pa rin nandiyan: $damagedPath" -ForegroundColor Gray
}
Write-Host ""
