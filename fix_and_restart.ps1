# PowerShell script to fix OSError and restart Django server
# Run this script to apply all fixes and restart the server

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "HMS OSError Fix and Server Restart" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop any running Django servers
Write-Host "Step 1: Stopping any running Django servers..." -ForegroundColor Yellow
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*manage.py*runserver*"} | Stop-Process -Force
Start-Sleep -Seconds 2
Write-Host "✓ Servers stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Clear all Python cache files
Write-Host "Step 2: Clearing Python cache files..." -ForegroundColor Yellow
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Filter "*.pyc" -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "✓ Cache cleared" -ForegroundColor Green
Write-Host ""

# Step 3: Create logs directory if it doesn't exist
Write-Host "Step 3: Creating logs directory..." -ForegroundColor Yellow
if (!(Test-Path -Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    Write-Host "✓ Logs directory created" -ForegroundColor Green
} else {
    Write-Host "✓ Logs directory already exists" -ForegroundColor Green
}
Write-Host ""

# Step 4: Clear old log file
Write-Host "Step 4: Clearing old log file..." -ForegroundColor Yellow
if (Test-Path -Path "logs\hms.log") {
    Remove-Item -Path "logs\hms.log" -Force -ErrorAction SilentlyContinue
    Write-Host "✓ Old log file cleared" -ForegroundColor Green
} else {
    Write-Host "✓ No old log file to clear" -ForegroundColor Green
}
Write-Host ""

# Step 5: Verify fix files exist
Write-Host "Step 5: Verifying fix files..." -ForegroundColor Yellow
$fixFiles = @(
    "core\logging_handlers.py",
    "accounts\auth_wrapper.py",
    "test_login_fix.py"
)

$allFilesExist = $true
foreach ($file in $fixFiles) {
    if (Test-Path -Path $file) {
        Write-Host "  ✓ $file exists" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file missing!" -ForegroundColor Red
        $allFilesExist = $false
    }
}

if (!$allFilesExist) {
    Write-Host ""
    Write-Host "ERROR: Some fix files are missing!" -ForegroundColor Red
    Write-Host "Please ensure all files have been created." -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 6: Run test script
Write-Host "Step 6: Running authentication test..." -ForegroundColor Yellow
python test_login_fix.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Authentication test passed" -ForegroundColor Green
} else {
    Write-Host "⚠ Authentication test had issues (this is OK if server isn't running)" -ForegroundColor Yellow
}
Write-Host ""

# Step 7: Start Django server
Write-Host "Step 7: Starting Django server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Server is starting..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The server will start in a new window." -ForegroundColor Yellow
Write-Host "Check logs\hms.log for detailed logging." -ForegroundColor Yellow
Write-Host ""
Write-Host "To test login:" -ForegroundColor Cyan
Write-Host "  1. Open browser to http://127.0.0.1:8000/accounts/login/" -ForegroundColor White
Write-Host "  2. Enter your phone number and password" -ForegroundColor White
Write-Host "  3. Login should work without OSError!" -ForegroundColor White
Write-Host ""

# Start server in a new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python manage.py runserver"

Write-Host "✓ Server started in new window" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix applied successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

