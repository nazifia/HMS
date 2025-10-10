@echo off
echo ========================================
echo FINAL CLEANUP - Removing ALL Cache
echo ========================================
echo.

echo Step 1: Stopping all Python processes...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul
echo Done!
echo.

echo Step 2: Deleting ALL __pycache__ directories...
for /d /r . %%d in (__pycache__) do @if exist "%%d" (
    echo Deleting: %%d
    rd /s /q "%%d" 2>nul
)
echo Done!
echo.

echo Step 3: Deleting ALL .pyc files...
del /s /q *.pyc 2>nul
echo Done!
echo.

echo Step 4: Verifying accounts\backends.py...
if exist "accounts\backends.py" (
    echo ✓ backends.py exists
) else (
    echo ✗ ERROR: backends.py missing!
    pause
    exit /b 1
)
echo.

echo Step 5: Verifying no backup files exist...
if exist "accounts\backends_backup.py" (
    echo ✗ WARNING: Deleting backends_backup.py
    del "accounts\backends_backup.py"
) else (
    echo ✓ No backup files found
)
echo.

echo Step 6: Creating logs directory...
if not exist logs mkdir logs
echo ✓ Logs directory ready
echo.

echo Step 7: Setting environment variables...
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONLEGACYWINDOWSSTDIO=0
echo ✓ Environment configured
echo.

echo ========================================
echo Starting Django Server
echo ========================================
echo.
echo Server will be available at:
echo   http://127.0.0.1:8000/
echo.
echo Login page:
echo   http://127.0.0.1:8000/accounts/login/
echo.
echo Press CTRL+C to stop the server
echo ========================================
echo.

python manage.py runserver

