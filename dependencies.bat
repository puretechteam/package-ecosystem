@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo ============================================
echo  Package Ecosystem Visualizer - Dependencies
echo ============================================
echo.

set PASS=0
set FAIL=0

echo [1] Checking Python on PATH...
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   [OK] Python is available
    set /a PASS+=1
) else (
    echo   [FAIL] Python not found on PATH
    set /a FAIL+=1
)

echo.
echo [2] Checking pip availability...
pip --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   [OK] pip is available
    set /a PASS+=1
) else (
    echo   [FAIL] pip not found on PATH
    set /a FAIL+=1
)

echo.
echo [3] Installing requirements from requirements.txt...
pip install -r requirements.txt >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   [OK] Requirements installed successfully
    set /a PASS+=1
) else (
    echo   [FAIL] Could not install requirements
    set /a FAIL+=1
)

echo.
echo ============================================
echo  Summary: !PASS! passed, !FAIL! failed
echo ============================================

if !FAIL! GTR 0 (
    echo  Some checks failed. Review the output above.
    endlocal
    exit /b 1
)

echo  All dependencies are ready.

endlocal