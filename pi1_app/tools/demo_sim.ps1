Param(
    [string]$SimSettings = "settings_pi1.json",
    [switch]$NoWebcam
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SimulationDir = Join-Path $ProjectRoot "simulation"
$VenvPython = Join-Path $ProjectRoot "..\.venv\Scripts\python.exe"

Write-Host "[1/4] Docker stack up..."
Set-Location $ProjectRoot
& docker compose up -d --build

Write-Host "[2/4] Cleaning old webcam processes..."
Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match "webcam_stream.py" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

if (-not $NoWebcam) {
    Write-Host "[3/4] Starting webcam stream in new terminal..."
    $webcamCmd = if (Test-Path $VenvPython) {
        "Set-Location '$ProjectRoot'; & '$VenvPython' 'tools/webcam_stream.py'"
    } else {
        "Set-Location '$ProjectRoot'; py tools/webcam_stream.py"
    }

    Start-Process powershell -ArgumentList "-NoExit", "-Command", $webcamCmd | Out-Null
}

Write-Host "[4/4] Starting simulation ($SimSettings) in new terminal..."
$simCmd = "Set-Location '$SimulationDir'; `\$env:SIM_SETTINGS_FILE='$SimSettings'; py main.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $simCmd | Out-Null

Write-Host "Done. Open http://localhost:5000 and http://localhost:3000"
