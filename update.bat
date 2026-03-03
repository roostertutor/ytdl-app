@echo off
echo ========================================
echo  YouTube Downloader - Update Script
echo ========================================
echo.

:: Check PowerShell is available (it is on all modern Windows)
where powershell >nul 2>&1
if errorlevel 1 (
    echo ERROR: PowerShell not found. Cannot continue.
    pause
    exit /b 1
)

echo Downloading latest version from GitHub...
powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/roostertutor/ytdl-app/main/app.py' -OutFile 'app.py.new'"

if not exist "app.py.new" (
    echo.
    echo ERROR: Download failed. Check your internet connection and try again.
    pause
    exit /b 1
)

:: Back up old version just in case
copy /Y app.py app.py.backup >nul
echo Backed up old app.py to app.py.backup

:: Replace with new version
move /Y app.py.new app.py >nul
echo Updated app.py successfully!

echo.
echo ========================================
echo  Update complete!
echo  Start the app as usual with start.bat
echo ========================================
echo.
pause