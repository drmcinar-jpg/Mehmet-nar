@echo off
REM Windows: bu dosyaya CIFT TIKLAYIN.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Python bulunamadi. https://www.python.org/downloads/ adresinden kurun
  echo   ve kurulumda "Add python.exe to PATH" secenegini isaretleyin.
  echo.
  pause
  exit /b 1
)

python calistir.py %*
echo.
pause
