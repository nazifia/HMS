@echo off
echo ========================================
echo HMS Server - Clear Cache and Start
echo ========================================
echo.

echo Step 1: Clearing Python cache...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc 2>nul
echo Cache cleared!
echo.

echo Step 2: Setting environment variables...
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONLEGACYWINDOWSSTDIO=0
echo Environment configured!
echo.

echo Step 3: Creating logs directory...
if not exist logs mkdir logs
echo Logs directory ready!
echo.

echo Step 4: Starting Django server...
echo Server will be available at: http://127.0.0.1:8000/
echo Login page: http://127.0.0.1:8000/accounts/login/
echo.
echo Press CTRL+C to stop the server
echo ========================================
echo.

python manage.py runserver

