<#
One-click installer for Android Platform Tools (adb) on Windows
- Downloads the latest platform-tools zip from Google
- Extracts to %USERPROFILE%\platform-tools
- Adds the folder to the current session PATH and to the user's PATH env var
- Restarts adb server and lists connected devices

Run in PowerShell (recommended):
  1) Open PowerShell (as normal user)
  2) Right-click paste and run, or run: PowerShell -ExecutionPolicy Bypass -File .\install_adb_windows.ps1

Note: If your environment disallows downloads or company policies require admin approval, you may need to run with admin privileges.
#>

$ErrorActionPreference = 'Stop'

Write-Host "== FRP Freedom: Install Platform Tools (adb) for Windows ==" -ForegroundColor Cyan

$zip = "$env:TEMP\platform-tools.zip"
$dl = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"

try {
    Write-Host "Downloading platform-tools..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $dl -OutFile $zip -UseBasicParsing -ErrorAction Stop

    $tmp = "$env:TEMP\platform-tools"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }

    Write-Host "Extracting..." -ForegroundColor Yellow
    Expand-Archive -Path $zip -DestinationPath "$env:TEMP" -Force

    $dest = "$env:USERPROFILE\platform-tools"
    if (Test-Path $dest) {
        Write-Host "Removing existing $dest..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $dest
    }

    Move-Item -Path "$env:TEMP\platform-tools" -Destination $dest -ErrorAction Stop

    Write-Host "Adding $dest to current PATH for this session..." -ForegroundColor Yellow
    $env:Path = $env:Path + ";" + $dest

    $old = [Environment]::GetEnvironmentVariable("Path","User")
    if ($old -notmatch [regex]::Escape($dest)) {
        [Environment]::SetEnvironmentVariable("Path", $old + ";" + $dest, "User")
        Write-Host "Added to user PATH. Restart your terminal windows to apply the change." -ForegroundColor Green
    } else {
        Write-Host "User PATH already contains $dest" -ForegroundColor Green
    }

    Write-Host "\nVerifying adb version..." -ForegroundColor Cyan
    & adb version

    Write-Host "\nRestarting adb server and listing devices..." -ForegroundColor Cyan
    & adb kill-server
    Start-Sleep -Seconds 1
    & adb start-server
    Start-Sleep -Seconds 1
    & adb devices -l

    Write-Host "\nIf devices show as 'unauthorized', please accept the USB debugging prompt on your phone." -ForegroundColor Yellow
    Write-Host "If 'adb' is still not recognized after restarting terminal, close and reopen PowerShell and run: adb devices -l" -ForegroundColor Yellow
}
catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "If you need admin privileges to install, try opening PowerShell as Administrator and re-run this script." -ForegroundColor Yellow
}
finally {
    # Cleanup
    if (Test-Path $zip) { Remove-Item -Force $zip -ErrorAction SilentlyContinue }
}

Write-Host "== Done ==" -ForegroundColor Cyan
