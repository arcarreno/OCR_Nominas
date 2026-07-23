@echo off
title Build OCR Portable
cd /d "%~dp0"

echo ========================================
echo   BUILD - OCR Nominas Portable
echo ========================================
echo.

set "OUTDIR=dist\OCRNominas-Portable"
set "PYVER=310"
set "PYDIR=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python%PYVER%"

:: ── 1. Build frontend ────────────────────────────────────────────────────
echo [1/5] Construyendo frontend...
call npm run build >nul 2>&1
if errorlevel 1 ( echo [ERROR] Fallo frontend & pause & exit /b 1 )
echo [OK] Frontend listo

:: ── 2. Create output structure ──────────────────────────────────────────
echo [2/5] Creando estructura...
if exist "%OUTDIR%" rmdir /s /q "%OUTDIR%"
mkdir "%OUTDIR%\app\backend" "%OUTDIR%\app\static\assets" "%OUTDIR%\tesseract\tessdata" >nul 2>&1
xcopy /q backend\*.py "%OUTDIR%\app\backend\" >nul
xcopy /q dist\index.html "%OUTDIR%\app\static\" >nul
xcopy /e /i /q dist\assets\* "%OUTDIR%\app\static\assets\" >nul
echo [OK] Estructura creada

:: ── 3. Bundle Python (from system install) ──────────────────────────────
echo [3/5] Empaquetando Python...
if not exist "%PYDIR%\python.exe" (
    echo [ERROR] No se encuentra Python en %PYDIR%
    echo Ejecuta este script en la MAQUINA DEL DESARROLLADOR
    pause & exit /b 1
)

mkdir "%OUTDIR%\python\DLLs" "%OUTDIR%\python\Lib" "%OUTDIR%\python\Scripts" >nul 2>&1

:: copy python executable and core
copy "%PYDIR%\python.exe" "%OUTDIR%\python\" >nul
copy "%PYDIR%\python3.dll" "%OUTDIR%\python\" >nul
copy "%PYDIR%\python%PYVER%.dll" "%OUTDIR%\python\" >nul
copy "%PYDIR%\_tkinter.pyd" "%OUTDIR%\python\" >nul 2>&1
xcopy /e /i /q "%PYDIR%\DLLs\*.pyd" "%OUTDIR%\python\DLLs\" >nul
xcopy /e /i /q "%PYDIR%\Lib" "%OUTDIR%\python\Lib\" >nul

:: copy site-packages
xcopy /e /i /q "%PYDIR%\Lib\site-packages" "%OUTDIR%\python\Lib\site-packages\" >nul
echo [OK] Python empaquetado

:: ── 4. Strip .pyc / __pycache__ ─────────────────────────────────────────
echo [4/5] Limpiando archivos innecesarios...
for /d /r "%OUTDIR%\python" %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
del /s /q "%OUTDIR%\python\Lib\*.pyc" >nul 2>&1
echo [OK] Limpieza hecha

:: ── 5. Copy Tesseract ────────────────────────────────────────────────────
echo [5/5] Empaquetando Tesseract...
set "TESS_SRC="
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set "TESS_SRC=C:\Program Files\Tesseract-OCR"
if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" set "TESS_SRC=C:\Program Files (x86)\Tesseract-OCR"
if "%TESS_SRC%"=="" (
    echo [AVISO] Tesseract no encontrado. Se descargara...
    mkdir "%OUTDIR%\tesseract" >nul 2>&1
    powershell -Command "& {try { Invoke-WebRequest -Uri 'https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0.20241111/tesseract-ocr-w64-setup-5.5.0.20241111.exe' -OutFile '%TEMP%\tesseract_installer.exe' -ErrorAction Stop; Start-Process -Wait '%TEMP%\tesseract_installer.exe' -ArgumentList '/S /D=%OUTDIR%\tesseract' } catch { Write-Host 'No se pudo descargar Tesseract' }}" >nul 2>&1
    if exist "%OUTDIR%\tesseract\tesseract.exe" set "TESS_SRC=%OUTDIR%\tesseract"
)
if not "%TESS_SRC%"=="" (
    xcopy /e /i /q "%TESS_SRC%\*" "%OUTDIR%\tesseract\" >nul
    echo [OK] Tesseract empaquetado
)
if not exist "%OUTDIR%\tesseract\tessdata\spa.traineddata" (
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata' -OutFile '%OUTDIR%\tesseract\tessdata\spa.traineddata'" >nul 2>&1
    if exist "%OUTDIR%\tesseract\tessdata\spa.traineddata" ( echo [OK] Espanol descargado ) else ( echo [AVISO] Sin espanol )
)

:: ── Create launcher .bat ────────────────────────────────────────────────
echo [*] Creando lanzador...
> "%OUTDIR%\Iniciar OCR.bat" (
    echo @echo off
    echo title OCR Nominas
    echo cd /d "%%~dp0"
    echo.
    echo set "PATH=%%~dp0tesseract;%%~dp0python\DLLs;%%~dp0python;%%PATH%%"
    echo set "TESSDATA_PREFIX=%%~dp0tesseract\tessdata"
    echo set "PYTHONHOME=%%~dp0python"
    echo set "PYTHONPATH=%%~dp0python\Lib"
    echo.
    echo echo Iniciando OCR Nominas en http://localhost:8000...
    echo start "OCR Backend" "%%~dp0python\python.exe" "%%~dp0app\backend\main.py"
    echo timeout /t 4 /nobreak ^>nul
    echo start http://localhost:8000
    echo.
    echo echo Presiona cualquier tecla para detener el servidor...
    echo pause ^>nul
    echo taskkill /FI "WINDOWTITLE eq OCR Backend*" /F ^>nul 2^>^&1
)
echo [OK] Lanzador creado

echo.
echo ========================================
echo   BUILD COMPLETADO
echo ========================================
echo.
echo Bundle portatil en: %OUTDIR%
echo Para distribuir: solo comprime la carpeta
echo.
pause
