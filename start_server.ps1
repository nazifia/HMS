# PowerShell script to start Django server with proper encoding
# This prevents OSError [Errno 22] on Windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting HMS Django Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set environment variables for UTF-8 encoding
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:PYTHONLEGACYWINDOWSSTDIO = "0"

# Set console to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

Write-Host "✓ Environment configured for UTF-8" -ForegroundColor Green
Write-Host ""

# Clear Python cache
Write-Host "Clearing Python cache..." -ForegroundColor Yellow
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "✓ Cache cleared" -ForegroundColor Green
Write-Host ""

# Create logs directory
if (!(Test-Path -Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
}

Write-Host "Starting Django development server..." -ForegroundColor Yellow
Write-Host "Server will be available at: http://127.0.0.1:8000/" -ForegroundColor Cyan
Write-Host "Login page: http://127.0.0.1:8000/accounts/login/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press CTRL+C to stop the server" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start the server with safe runserver command
Write-Host "Note: Using custom runserver_safe command to prevent OSError" -ForegroundColor Cyan
Write-Host "All logs will be written to logs\hms.log" -ForegroundColor Cyan
Write-Host ""
python manage.py runserver_safe

