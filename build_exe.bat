@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Construyendo OCRNominas.exe...
echo.

REM Build the exe
python build_launcher.py

if %ERRORLEVEL% == 0 (
    echo.
    echo LISTO! Exe creado en: dist\OCRNominas\OCRNominas.exe
) else (
    echo.
    echo ERROR: Fallo la construccion
)

pause
