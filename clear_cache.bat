@echo off
echo Clearing cache files...

:: Remove Python cache files
if exist __pycache__ rmdir /s /q __pycache__

:: Remove template cache
if exist templates\__pycache__ rmdir /s /q templates\__pycache__
if exist pharmacy\templates\__pycache__ rmdir /s /q pharmacy\templates\__pycache__

:: Remove Django migrations cache
if exist */migrations\__pycache__ rmdir /s /q */migrations\__pycache__

:: Clear staticfiles and recollect
python manage.py collectstatic --noinput --clear

echo Cache cleared successfully!
echo.
echo Please restart the Django development server if it's running.
pause
