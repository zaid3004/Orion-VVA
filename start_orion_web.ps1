# Orion Voice Assistant - Web Interface Launcher
# PowerShell script to start the Orion web interface

Write-Host "Orion Voice Assistant - Web Interface" -ForegroundColor Blue
Write-Host "=======================================" -ForegroundColor Cyan

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found. Please install Python first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Flask is installed
try {
    python -c "import flask" 2>&1 | Out-Null
    Write-Host "Flask is available" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Flask not found. Installing Flask..." -ForegroundColor Yellow
    pip install -r web_requirements.txt
}

Write-Host ""
Write-Host "Starting Orion Web Interface..." -ForegroundColor Blue
Write-Host "Open your browser to: http://localhost:5000" -ForegroundColor Yellow
Write-Host "Use your microphone to communicate with Orion!" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host "=======================================" -ForegroundColor Cyan

# Start the web server
try {
    python web_server.py
} catch {
    Write-Host ""
    Write-Host "ERROR: Error starting Aurora web server" -ForegroundColor Red
    Write-Host "Make sure all dependencies are installed:" -ForegroundColor Yellow
    Write-Host "pip install -r web_requirements.txt" -ForegroundColor Gray
    Write-Host "pip install -r requirements.txt" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Aurora web interface stopped." -ForegroundColor Blue
Read-Host "Press Enter to close"