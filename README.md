# OCR Nominas

Aplicacion de escritorio para extraer y validar datos de recibos de nomina (PDF) mediante OCR.

## Stack

- **Backend**: Python + FastAPI + Uvicorn
- **Frontend**: React + TypeScript + Vite
- **OCR**: Tesseract 5 + pytesseract + OpenCV
- **PDF**: PyPDF2
- **Empaquetado**: PyInstaller + Inno Setup

## Requisitos

- Windows 10/11 64-bit
- Tesseract OCR 5+ con idioma espanol (incluido en el instalador)

## Instalacion

### Opcion 1: Instalador (recomendado)

Ejecutar `OCRNominas-Installer.exe` como administrador y seguir el wizard.
Incluye Tesseract OCR + espanol. No requiere nada adicional.

### Opcion 2: Portable

1. Tener Python 3.10+ y Node.js 18+ instalados
2. Ejecutar `instalar.bat` (configura todo automaticamente)
3. Ejecutar `ejecutar.bat` para iniciar el servidor

### Opcion 3: Desarrollo

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend (otra terminal)
npm install
npm run dev
```

## Uso

1. Abrir `http://localhost:8000`
2. Subir un archivo PDF con recibos de nomina
3. La app extrae automaticamente: nombre, RFC, CURP, fecha de pago, puesto, percepciones, deducciones, neto
4. Validacion contra formato oficial (RFC, CURP, NSS, CP, catalogo de puestos)
5. Exportar resultados a Excel

## Estructura

```
OCR/
  backend/          # API FastAPI
    main.py         # Endpoints y logica OCR
    requirements.txt
  src/              # Frontend React
  launcher.py       # Entry point del .exe
  instalar.bat      # Setup automatico
  ejecutar.bat      # Inicio rapido
  portable.bat      # Build portable
  build_exe.bat     # Build .exe con PyInstaller
  installer.iss     # Script Inno Setup
  dist/
    OCRNominas/     # .exe portable (PyInstaller)
    installer/      # Instalador (Inno Setup)
```

## Credenciales

No requiere autenticacion. Corre unicamente en localhost.
