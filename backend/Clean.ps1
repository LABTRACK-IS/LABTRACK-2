#Requires -Version 5.1
param([switch]$SkipBackup)

$ErrorActionPreference = 'Continue'
$BackendRoot = 'C:\labtrack\backend\LabTrack.CSharp\src'
$BackupDir   = "$env:USERPROFILE\Desktop\LabTrack-Backups"
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

Write-Host '==============================================================' -ForegroundColor Magenta
Write-Host '  LABTRACK BACKEND CLEANUP' -ForegroundColor Magenta
Write-Host '==============================================================' -ForegroundColor Magenta

# [1] BACKUP
if (-not $SkipBackup) {
    Write-Host "`n[1/6] Backup..." -ForegroundColor Cyan
    $zipPath = Join-Path $BackupDir "backend-$stamp.zip"
    Compress-Archive -Path $BackendRoot -DestinationPath $zipPath -Force
    $sizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
    Write-Host "  OK: $zipPath ($sizeMB MB)" -ForegroundColor Green
} else {
    Write-Host "`n[1/6] Backup SKIPPED" -ForegroundColor Yellow
}

# [2] EMPTY FOLDERS
Write-Host "`n[2/6] Removing empty folders..." -ForegroundColor Cyan
$emptyCount = 0
Get-ChildItem $BackendRoot -Recurse -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch '\\(obj|bin|\.vs)\\' } |
    ForEach-Object {
        $files = @(Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue |
                   Where-Object { $_.FullName -notmatch '\\(obj|bin)\\' })
        if ($files.Count -eq 0) {
            Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            $emptyCount++
        }
    }
Write-Host "  Deleted: $emptyCount folders" -ForegroundColor Green

# [3] MVC FOLDERS
Write-Host "`n[3/6] Creating MVC folders..." -ForegroundColor Cyan
$api = Join-Path $BackendRoot 'LabTrack.Api'
$app = Join-Path $BackendRoot 'LabTrack.Application'
$dom = Join-Path $BackendRoot 'LabTrack.Domain'
$inf = Join-Path $BackendRoot 'LabTrack.Infrastructure'

$folders = @(
    (Join-Path $api 'Models'),
    (Join-Path $api 'ViewModels'),
    (Join-Path $app 'Interfaces'),
    (Join-Path $app 'DTOs'),
    (Join-Path $dom 'Interfaces'),
    (Join-Path $inf 'Repositories')
)
$created = 0
foreach ($f in $folders) {
    if (-not (Test-Path $f)) {
        New-Item -ItemType Directory -Path $f -Force | Out-Null
        Write-Host "  Created: $($f.Replace($BackendRoot, '.'))" -ForegroundColor Green
        $created++
    }
}
Write-Host "  Total: $created new folders" -ForegroundColor Green

# [4] INTERFACE STUBS
Write-Host "`n[4/6] Extracting inline interfaces..." -ForegroundColor Cyan
$ifaceDir = Join-Path $app 'Interfaces'
$ctrlDir = Join-Path $api 'Controllers'
$stubsCreated = 0

if (Test-Path $ctrlDir) {
    $controllers = Get-ChildItem $ctrlDir -Filter '*Controller.cs'
    foreach ($ctrl in $controllers) {
        $content = Get-Content $ctrl.FullName -Raw
        $regex = [regex]'public\s+interface\s+(I\w+Service)'
        $found = $regex.Matches($content)
        foreach ($m in $found) {
            $ifName = $m.Groups[1].Value
            $target = Join-Path $ifaceDir "$ifName.cs"
            if (Test-Path $target) { continue }
            $stubLines = @(
                "// Auto-generated stub",
                "// Source: $($ctrl.Name)",
                "// TODO: Copy method signatures from controller, then remove from controller",
                "namespace LabTrack.Application.Interfaces;",
                "",
                "public interface $ifName",
                "{",
                "    // methods go here",
                "}"
            )
            $stubLines | Out-File $target -Encoding UTF8
            Write-Host "  Stub: $ifName.cs" -ForegroundColor Green
            $stubsCreated++
        }
    }
}
Write-Host "  Total: $stubsCreated stubs" -ForegroundColor Green

# [5] GITIGNORE
Write-Host "`n[5/6] Ensuring .gitignore..." -ForegroundColor Cyan
$gitignore = 'C:\labtrack\backend\.gitignore'
$required = @('bin/','obj/','*.user','.vs/','appsettings.Development.json','appsettings.Local.json','*.db','*.sqlite','*.log')
if (-not (Test-Path $gitignore)) {
    $required | Out-File $gitignore -Encoding UTF8
    Write-Host "  Created: $gitignore" -ForegroundColor Green
} else {
    $existing = Get-Content $gitignore -Raw
    $added = 0
    foreach ($r in $required) {
        if ($existing -notmatch [regex]::Escape($r)) {
            Add-Content $gitignore $r
            $added++
        }
    }
    Write-Host "  Added: $added lines" -ForegroundColor Green
}

# [6] BIND CHECK
Write-Host "`n[6/6] Checking 0.0.0.0 bind..." -ForegroundColor Cyan
$prog = Join-Path $api 'Program.cs'
if (Test-Path $prog) {
    $progContent = Get-Content $prog -Raw
    if ($progContent -match '0\.0\.0\.0|UseUrls') {
        Write-Host "  Already configured" -ForegroundColor Green
    } else {
        Write-Host "  MISSING 0.0.0.0 (manual edit needed)" -ForegroundColor Yellow
        Write-Host "  Add this after 'var builder = WebApplication.CreateBuilder(args);':" -ForegroundColor Yellow
        Write-Host '    builder.WebHost.UseUrls("http://0.0.0.0:5000");' -ForegroundColor White
    }
}

Write-Host ''
Write-Host '==============================================================' -ForegroundColor Magenta
Write-Host '  CLEANUP COMPLETE' -ForegroundColor Green
Write-Host '==============================================================' -ForegroundColor Magenta
Write-Host "  Backup: $zipPath" -ForegroundColor Cyan
Write-Host ''
