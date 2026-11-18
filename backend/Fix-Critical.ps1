$ErrorActionPreference = "Continue"
$root = "C:\labtrack\backend\LabTrack.CSharp\src"

Write-Host ""
Write-Host ("=" * 72) -ForegroundColor Cyan
Write-Host "  STEP 1: DIAGNOSE DbContext.cs" -ForegroundColor Cyan
Write-Host ("=" * 72) -ForegroundColor Cyan

$dcPath = Join-Path $root "LabTrack.Infrastructure\Persistence\DbContext\LabTrackDbContext.cs"
if (-not (Test-Path $dcPath)) {
    $found = Get-ChildItem $root -Recurse -Filter "LabTrackDbContext.cs" -EA SilentlyContinue | Select-Object -First 1
    if ($found) { $dcPath = $found.FullName }
    else { Write-Host "  [ERR] DbContext not found" -ForegroundColor Red; exit 1 }
}
Write-Host "  File: $dcPath" -ForegroundColor Gray

$lines = @(Get-Content $dcPath)
Write-Host "  Lines: $($lines.Count)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Lines 250-266:" -ForegroundColor Cyan
for ($i = 250; $i -le [Math]::Min(266, $lines.Count); $i++) {
    $color = if ($lines[$i - 1] -match '^\\') { "Red" } else { "Gray" }
    Write-Host ("  {0,4}| {1}" -f $i, $lines[$i - 1]) -ForegroundColor $color
}
Write-Host ""

$content = Get-Content $dcPath -Raw
$openC = ([regex]::Matches($content, '\{')).Count
$closeC = ([regex]::Matches($content, '\}')).Count
Write-Host "  Braces: open=$openC close=$closeC diff=$($openC - $closeC)" -ForegroundColor Cyan

$badLines = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^\\') { $badLines += ($i + 1) }
}
if ($badLines.Count -gt 0) {
    Write-Host "  [WARN] Line(s) starting with '\': $($badLines -join ', ')" -ForegroundColor Yellow
}

Write-Host ""
Write-Host ("=" * 72) -ForegroundColor Cyan
Write-Host "  STEP 2: BACKUP DbContext" -ForegroundColor Cyan
Write-Host ("=" * 72) -ForegroundColor Cyan
$dcBak = "$dcPath.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item $dcPath $dcBak
Write-Host "  [OK] $dcBak" -ForegroundColor Green

Write-Host ""
Write-Host ("=" * 72) -ForegroundColor Cyan
Write-Host "  STEP 3: FIX DbContext.cs" -ForegroundColor Cyan
Write-Host ("=" * 72) -ForegroundColor Cyan

$lines2 = @(Get-Content $dcPath)
$newLines = @()
$removed = 0
for ($i = 0; $i -lt $lines2.Count; $i++) {
    if ($lines2[$i] -match '^\\') {
        Write-Host "  [REMOVE L$($i+1)] $($lines2[$i])" -ForegroundColor Yellow
        $removed++
    } else {
        $newLines += $lines2[$i]
    }
}
$lines2 = $newLines

$content2 = $lines2 -join "`r`n"
$openC2 = ([regex]::Matches($content2, '\{')).Count
$closeC2 = ([regex]::Matches($content2, '\}')).Count
$diff = $openC2 - $closeC2
if ($diff -gt 0) {
    Write-Host "  [ADD] $diff closing brace(s) at end" -ForegroundColor Yellow
    for ($i = 0; $i -lt $diff; $i++) { $lines2 += "}" }
} elseif ($diff -lt 0) {
    Write-Host "  [WARN] $(-$diff) extra closing brace(s) - may need manual fix" -ForegroundColor Yellow
}

$lines2 | Set-Content $dcPath -Encoding UTF8
Write-Host "  [OK] DbContext saved (removed $removed line(s), added $([Math]::Max(0,$diff)) brace(s))" -ForegroundColor Green

Write-Host ""
Write-Host ("=" * 72) -ForegroundColor Cyan
Write-Host "  STEP 4: REMOVE EMPTY STUBS (safe check)" -ForegroundColor Cyan
Write-Host ("=" * 72) -ForegroundColor Cyan

$ifaceDir = Join-Path $root "LabTrack.Application\Interfaces"
$ctrlDir  = Join-Path $root "LabTrack.Api\Controllers"

$map = @{
    "IAnalyticsService"     = "AnalyticsController"
    "IAssetService"         = "AssetController"
    "IAuditLogService"      = "AuditController"
    "ICommunicationService" = "CommunicationController"
    "IFinancialService"     = "FinancialController"
    "ILaboratoriesService"  = "LaboratoriesController"
    "IMaintenanceService"   = "MaintenanceController"
    "INetworkService"       = "NetworkController"
    "INotificationService"  = "NotificationController"
    "IPcUsageService"       = "PcUsageController"
    "IProblemReportService" = "ProblemReportController"
    "IQrService"            = "QrController"
    "IRepairTicketService"  = "RepairTicketController"
    "IReplacementService"   = "ReplacementController"
    "IReservationService"   = "ReservationController"
    "IUserService"          = "UsersController"
}

$moved = 0
$skipped = 0
foreach ($ifaceName in $map.Keys) {
    $stubPath = Join-Path $ifaceDir "$ifaceName.cs"
    if (-not (Test-Path $stubPath)) { continue }

    $stub = Get-Content $stubPath -Raw
    $stubHasMethods = $stub -match '\w+\s+\w+\s*\([^)]*\)\s*;'

    $ctrlName = $map[$ifaceName]
    $ctrlPath = Join-Path $ctrlDir "$ctrlName.cs"
    $ctrlHasInline = $false
    if (Test-Path $ctrlPath) {
        $ctrlHasInline = (Get-Content $ctrlPath -Raw) -match "public\s+interface\s+$ifaceName\b"
    }

    if (-not $ctrlHasInline -and -not $stubHasMethods) {
        Write-Host "  [SKIP] $ifaceName - NO inline in $ctrlName AND stub empty (KEEP)" -ForegroundColor Red
        $skipped++
        continue
    }
    if ($stubHasMethods) {
        Write-Host "  [KEEP] $ifaceName (stub has methods)" -ForegroundColor Gray
        continue
    }

    Move-Item $stubPath "$stubPath.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Force
    Write-Host "  [MOVED] $ifaceName.cs (inline exists in $ctrlName)" -ForegroundColor Green
    $moved++
}
Write-Host "  Moved: $moved | Skipped: $skipped" -ForegroundColor Cyan

Write-Host ""
Write-Host ("=" * 72) -ForegroundColor Cyan
Write-Host "  STEP 5: REBUILD" -ForegroundColor Cyan
Write-Host ("=" * 72) -ForegroundColor Cyan

$sln = Get-ChildItem "C:\labtrack\backend" -Filter "*.sln*" -Recurse -EA SilentlyContinue | Select-Object -First 1
$target = if ($sln) { $sln.FullName } else { (Join-Path $root "LabTrack.Api\LabTrack.Api.csproj") }
Write-Host "  $target" -ForegroundColor Gray
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
    Write-Host "  BUILD SUCCEEDED" -ForegroundColor Green
    Write-Host ("=" * 72) -ForegroundColor Green
    Write-Host "  Next: per-controller migration (isa-isa)" -ForegroundColor Cyan
} else {
    Write-Host ("=" * 72) -ForegroundColor Red
    Write-Host "  BUILD FAILED" -ForegroundColor Red
    Write-Host ("=" * 72) -ForegroundColor Red
    Write-Host ""
    Write-Host "  DbContext backup: $dcBak" -ForegroundColor Yellow
    Write-Host "  Restore: Copy-Item '$dcBak' '$dcPath' -Force" -ForegroundColor Gray
}
Write-Host ""
