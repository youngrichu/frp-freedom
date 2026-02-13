<#
Detect device and generate device report for FRP Freedom on Windows
- Ensures platform-tools (adb) are installed (calls install_adb_windows.ps1)
- Waits for a connected device (authorized) up to a timeout
- If authorized device found, runs Python DeviceManager scan and writes device_report.json

Run:
  PowerShell -ExecutionPolicy Bypass -File .\scripts\detect_and_report_windows.ps1
#>

$ErrorActionPreference = 'Stop'
$timeoutSeconds = 120
$pollInterval = 3

Write-Host "== FRP Freedom: Detect Device & Generate Report (Windows) ==" -ForegroundColor Cyan

# Ensure adb installed
try {
    Write-Host "Ensuring platform-tools (adb) is installed..." -ForegroundColor Yellow
    & PowerShell -ExecutionPolicy Bypass -File .\scripts\install_adb_windows.ps1
}
catch {
    Write-Host "Warning: install script reported an error: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Check adb availability
try {
    $adbVer = & adb version 2>&1
    Write-Host "adb version output:`n$adbVer" -ForegroundColor Green
}
catch {
    Write-Host "Error: adb not available even after install. Please re-run the install script or add C:\\platform-tools to PATH." -ForegroundColor Red
    exit 1
}

# Wait for authorized device
Write-Host "Waiting for an authorized device (timeout: $timeoutSeconds s)..." -ForegroundColor Cyan
$elapsed = 0
$deviceSerial = $null
$deviceState = $null
while ($elapsed -lt $timeoutSeconds) {
    $lines = & adb devices -l 2>&1 | Where-Object { $_ -and ($_ -notmatch "List of devices") }
    if ($lines) {
        foreach ($line in $lines) {
            if ($line -match "^([^\s]+)\s+(device|unauthorized|offline|unauthorized)\b") {
                $deviceSerial = $Matches[1]; $deviceState = $Matches[2]
                Write-Host "Found device: $deviceSerial ($deviceState)" -ForegroundColor Green
                break
            }
        }
    }
    if ($deviceState -eq 'device') { break }
    if ($deviceState -eq 'unauthorized') {
        Write-Host "Device is unauthorized. Please accept USB debugging prompt on the phone (if shown), then press Enter to continue polling..." -ForegroundColor Yellow
        Read-Host -Prompt "If you've accepted the prompt on the phone, press Enter to continue polling (or Ctrl+C to abort)"
        # Restart adb server to re-evaluate
        & adb kill-server; Start-Sleep -Seconds 1; & adb start-server
    }
    Start-Sleep -Seconds $pollInterval
    $elapsed += $pollInterval
}

if (-not $deviceSerial) {
    Write-Host "No device detected within timeout. Please check USB connection, drivers, and USB Debugging on the device." -ForegroundColor Red
    exit 2
}

if ($deviceState -ne 'device') {
    Write-Host "Device found but not authorized: state=$deviceState. Please authorize on the phone and re-run this script." -ForegroundColor Red
    exit 3
}

Write-Host "Authorized device detected: $deviceSerial. Generating JSON device report..." -ForegroundColor Cyan

# Run Python scan and output device_report.json
try {
    $pythonCmd = "import sys, json; sys.path.insert(0,'src'); from core.config import Config; from core.device_manager import DeviceManager; cfg=Config(); dm=DeviceManager(cfg); devices=dm.scan_devices(); print(json.dumps([d.to_dict() for d in devices], indent=2))"
    $out = & python -c $pythonCmd 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error running python scan: $out" -ForegroundColor Red
        exit 4
    }
    $reportPath = Join-Path -Path (Get-Location) -ChildPath "device_report.json"
    $out | Out-File -FilePath $reportPath -Encoding UTF8
    Write-Host "Device report written to: $reportPath" -ForegroundColor Green
    Write-Host "Report preview:" -ForegroundColor Cyan
    Get-Content $reportPath -TotalCount 60 | Write-Host
}
catch {
    Write-Host "Failed to generate device report: $($_.Exception.Message)" -ForegroundColor Red
    exit 5
}

Write-Host "== Done ==" -ForegroundColor Cyan
