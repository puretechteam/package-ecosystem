@echo off
setlocal

cd /d "%~dp0"

for /f "usebackq delims=" %%v in (`type VERSION`) do set VERSION=%%v

echo Building package-ecosystem version %VERSION%...

pyinstaller --noconfirm ^
    --name "package-ecosystem-%VERSION%" ^
    --add-data "data;data" ^
    --add-data "static;static" ^
    --distpath=dist ^
    --workpath=build ^
    app.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo BUILD SUCCESS: package-ecosystem-%VERSION% created in dist/
) else (
    echo.
    echo BUILD FAILED with error %ERRORLEVEL%
    endlocal
    exit /b %ERRORLEVEL%
)

endlocal