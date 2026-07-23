@echo off
title OCR Recibos de Nomina
cd /d "%~dp0"

echo ========================================
echo   OCR Recibos de Nomina
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Ejecuta "instalar.bat"
    pause
    exit /b 1
)

if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    set "PATH=C:\Program Files\Tesseract-OCR;%PATH%"
)
if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
    set "PATH=C:\Program Files (x86)\Tesseract-OCR;%PATH%"
)

if not exist "backend\main.py" (
    echo [ERROR] No se encuentra backend\main.py
    pause
    exit /b 1
)

echo Iniciando servidor backend en puerto 8000...
start "OCR Backend" python backend\main.py

echo Esperando a que el servidor arranque...
timeout /t 4 /nobreak >nul

echo Abriendo navegador...
start http://localhost:8000

echo.
echo ========================================
echo   APLICACION EN EJECUCION
echo ========================================
echo.
echo   Abre tu navegador en: http://localhost:8000
echo   Arrastra un PDF y presiona "Procesar"
echo.
echo   Presiona CUALQUIER TECLA para detener
echo.

pause >nul

echo Deteniendo servidor...
taskkill /FI "WINDOWTITLE eq OCR Backend*" /F >nul 2>&1
echo Aplicacion detenida.
