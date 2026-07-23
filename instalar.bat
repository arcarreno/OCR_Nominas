@echo off
title Instalador OCR Recibos
echo ========================================
echo   INSTALADOR - OCR Recibos de Nomina
echo ========================================
echo.

echo Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado
    echo Descarga: https://www.python.org/downloads/
    echo IMPORTANTE: Marca "Add Python to PATH"
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i

echo Verificando Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js no esta instalado
    echo Descarga: https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo [OK] Node.js %%i

echo Verificando Tesseract...
set "TESS_FOUND=0"
tesseract --version >nul 2>&1
if not errorlevel 1 (
    set "TESS_FOUND=1"
)
if "%TESS_FOUND%"=="0" (
    if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        set "TESS_FOUND=1"
        set "PATH=C:\Program Files\Tesseract-OCR;%PATH%"
    )
)
if "%TESS_FOUND%"=="0" (
    if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
        set "TESS_FOUND=1"
        set "PATH=C:\Program Files (x86)\Tesseract-OCR;%PATH%"
    )
)
if "%TESS_FOUND%"=="0" (
    echo [ERROR] Tesseract OCR no esta instalado
    echo Descarga: https://github.com/UB-Mannheim/tesseract/wiki
    echo IMPORTANTE: Instala el paquete de idioma "Spanish"
    pause
    exit /b 1
)
echo [OK] Tesseract encontrado

echo Verificando idioma espanol...
set "SPA_FOUND=0"
if exist "C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata" set "SPA_FOUND=1"
if exist "C:\Program Files (x86)\Tesseract-OCR\tessdata\spa.traineddata" set "SPA_FOUND=1"
if "%SPA_FOUND%"=="1" (
    echo [OK] Idioma espanol disponible
) else (
    echo [AVISO] Idioma espanol no encontrado - el OCR usara ingles como respaldo
)

echo.
echo Todos los prerequisitos OK
echo.

echo Instalando paquetes Python...
pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de paquetes Python
    pause
    exit /b 1
)
echo [OK] Paquetes Python listos

echo.
echo Instalando paquetes npm...
cd /d "%~dp0"
call npm install
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de paquetes npm
    pause
    exit /b 1
)
echo [OK] Paquetes npm listos

echo.
echo Construyendo frontend...
call npm run build
if errorlevel 1 (
    echo [ERROR] Fallo al construir el frontend
    pause
    exit /b 1
)
echo [OK] Frontend construido

echo.
echo Copiando frontend al backend...
if exist "backend\static" rmdir /s /q "backend\static"
xcopy /e /i /q dist backend\static >nul
if errorlevel 1 (
    echo [ERROR] Fallo al copiar archivos al backend
    pause
    exit /b 1
)
echo [OK] Frontend copiado a backend/static

echo.
echo ========================================
echo   INSTALACION COMPLETADA
echo ========================================
echo.
echo Para usar la aplicacion, doble clic en "ejecutar.bat"
echo.
pause
