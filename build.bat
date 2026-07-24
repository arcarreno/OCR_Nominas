@echo off
title Build OCR Nominas - Generar .exe
cd /d "%~dp0"

echo ========================================
echo   BUILD - OCR Recibos de Nomina (.exe)
echo ========================================
echo.

:: ── 1. Build frontend ────────────────────────────────────────────────────
echo [1/4] Construyendo frontend...
call npm install >nul 2>&1
call npm run build
if errorlevel 1 (
    echo [ERROR] Fallo al construir frontend
    pause
    exit /b 1
)
echo [OK] Frontend construido

:: ── 2. Copy static to backend ────────────────────────────────────────────
echo [2/4] Copiando archivos estaticos al backend...
if exist "backend\static" rmdir /s /q "backend\static"
xcopy /e /i /q dist backend\static >nul
echo [OK] Archivos copiados

:: ── 3. Build exe ─────────────────────────────────────────────────────────
echo [3/4] Generando ejecutable con PyInstaller...
pyinstaller --onedir ^
    --name "OCRNominas" ^
    --add-data "backend\static;static" ^
    --add-data "backend\requirements.txt;." ^
    --noconfirm ^
    --log-level WARN ^
    launcher.py
if errorlevel 1 (
    echo [ERROR] Fallo al generar el ejecutable
    pause
    exit /b 1
)
echo [OK] Ejecutable generado

:: ── 4. Bundle Tesseract ──────────────────────────────────────────────────
echo [4/4] Empaquetando Tesseract...
set "TESS_SRC="
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set "TESS_SRC=C:\Program Files\Tesseract-OCR"
if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" set "TESS_SRC=C:\Program Files (x86)\Tesseract-OCR"

if not "%TESS_SRC%"=="" (
    mkdir "dist\OCRNominas\tesseract" >nul 2>&1
    xcopy /e /i /q "%TESS_SRC%" "dist\OCRNominas\tesseract\" >nul 2>&1
    echo [OK] Tesseract empaquetado

    :: Download Spanish language if missing
    if not exist "dist\OCRNominas\tesseract\tessdata\spa.traineddata" (
        echo Descargando idioma espanol...
        powershell -Command "Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata' -OutFile 'dist\OCRNominas\tesseract\tessdata\spa.traineddata'" >nul 2>&1
        if exist "dist\OCRNominas\tesseract\tessdata\spa.traineddata" (
            echo [OK] Idioma espanol descargado
        ) else (
            echo [AVISO] No se pudo descargar idioma espanol
        )
    )
) else (
    echo [AVISO] Tesseract no encontrado en el sistema
    echo El usuario debera instalar Tesseract manualmente
)

:: ── Clean spec ──────────────────────────────────────────────────────────
if exist "OCRNominas.spec" del "OCRNominas.spec"

echo.
echo ========================================
echo   BUILD COMPLETADO
echo ========================================
echo.
echo El ejecutable esta en: dist\OCRNominas\
echo.
echo Para distribuir: comprime la carpeta completa
echo   dist\OCRNominas\  +  tesseract\
echo.
pause
