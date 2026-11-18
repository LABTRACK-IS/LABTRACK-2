$prog = "C:\labtrack\backend\LabTrack.CSharp\src\LabTrack.Api\Program.cs"

Write-Host ""
Write-Host ("="*72) -ForegroundColor Cyan
Write-Host "  FIX: Program.cs 0.0.0.0 bind" -ForegroundColor Cyan
Write-Host ("="*72) -ForegroundColor Cyan

if (-not (Test-Path $prog)) {
    Write-Host "  [ERR] Program.cs not found" -ForegroundColor Red
    exit 1
}

$raw = Get-Content $prog -Raw

if ($raw -match 'builder\.WebHost\.UseUrls') {
    Write-Host "  [OK] Already has UseUrls - skip" -ForegroundColor Green
} else {
    # Backup
    $bak = "$prog.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $prog $bak
    Write-Host "  [OK] Backup: $bak" -ForegroundColor Green

    # Find builder line
    $pattern = '(var\s+builder\s*=\s*WebApplication\.CreateBuilder\([^;]*\);)'
    if ($raw -match $pattern) {
        $insert = "`$1`r`n`r`n// Bind to all interfaces (device access)`r`nbuilder.WebHost.UseUrls(`"http://0.0.0.0:5000`", `"https://0.0.0.0:5001`");"
        $new = $raw -replace $pattern, $insert
        $new | Set-Content $prog -Encoding UTF8
        Write-Host "  [OK] Patched Program.cs" -ForegroundColor Green
        Write-Host "  Added:" -ForegroundColor Gray
        Write-Host "    builder.WebHost.UseUrls(`"http://0.0.0.0:5000`", `"https://0.0.0.0:5001`");" -ForegroundColor Yellow
    } else {
        Write-Host "  [WARN] CreateBuilder line not matched - manual edit needed" -ForegroundColor Yellow
        Write-Host "  Open: $prog" -ForegroundColor Gray
        Write-Host "  Add after 'var builder = WebApplication.CreateBuilder(args);':" -ForegroundColor Gray
        Write-Host '    builder.WebHost.UseUrls("http://0.0.0.0:5000", "https://0.0.0.0:5001");' -ForegroundColor White
    }
}

Write-Host ""
Write-Host ("="*72) -ForegroundColor Cyan
Write-Host "  BUILD VERIFY" -ForegroundColor Cyan
Write-Host ("="*72) -ForegroundColor Cyan

$sln = Get-ChildItem "C:\labtrack\backend" -Filter "*.sln" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
$target = if ($sln) { $sln.FullName } else { "C:\labtrack\backend\LabTrack.CSharp\src\LabTrack.Api\LabTrack.Api.csproj" }

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
    Write-Host ("="*72) -ForegroundColor Green
    Write-Host "  BUILD SUCCEEDED" -ForegroundColor Green
    Write-Host ("="*72) -ForegroundColor Green
    Write-Host "  Next: test from phone using your PC's LAN IP" -ForegroundColor Cyan
    Write-Host "  Find IP:  ipconfig | Select-String 'IPv4'" -ForegroundColor Gray
    Write-Host "  Then open:  http://<YOUR-PC-IP>:5000/swagger" -ForegroundColor Gray
} else {
    Write-Host ("="*72) -ForegroundColor Red
    Write-Host "  BUILD FAILED (exit $exit)" -ForegroundColor Red
    Write-Host ("="*72) -ForegroundColor Red
    Write-Host "  Restore Program.cs backup if needed:" -ForegroundColor Yellow
    Write-Host "    Copy-Item '$prog.bak-*' $prog -Force" -ForegroundColor Gray
}
Write-Host ""
