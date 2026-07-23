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
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Tesseract OCR no esta instalado
    echo Descarga: https://github.com/UB-Mannheim/tesseract/wiki
    echo IMPORTANTE: Instala el paquete de idioma "Spanish"
    pause
    exit /b 1
)
echo [OK] Tesseract encontrado

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
echo ========================================
echo   INSTALACION COMPLETADA
echo ========================================
echo.
echo Para usar la aplicacion, doble clic en "ejecutar.bat"
echo.
pause
