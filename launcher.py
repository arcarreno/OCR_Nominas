import os
import sys
import time
import webbrowser
import threading

# ── Detect frozen/base paths ──────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE = sys._MEIPASS
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

os.environ['LAUNCHER_BASE'] = BASE

# ── Tesseract path ─────────────────────────────────────────────────────────
_tesseract_cmd = None
_tessdata_dir = None

# 1. next to exe (frozen) or project root (dev)
_tess_exe = os.path.join(BASE, 'tesseract', 'tesseract.exe')
if os.path.isfile(_tess_exe):
    _tesseract_cmd = _tess_exe
    _td = os.path.join(BASE, 'tesseract', 'tessdata')
    if os.path.isdir(_td):
        _tessdata_dir = _td

# 2. system PATH
import shutil
if not _tesseract_cmd:
    _t = shutil.which('tesseract')
    if _t:
        _tesseract_cmd = _t
        _td = os.path.join(os.path.dirname(_t), 'tessdata')
        if os.path.isdir(_td):
            _tessdata_dir = _td

# 3. common install path
if not _tesseract_cmd:
    _t = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.isfile(_t):
        _tesseract_cmd = _t
        _td = r'C:\Program Files\Tesseract-OCR\tessdata'
        if os.path.isdir(_td):
            _tessdata_dir = _td

if _tesseract_cmd:
    os.environ['TESSDATA_PREFIX'] = _tessdata_dir or ''
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd

# ── Import app ────────────────────────────────────────────────────────────
sys.path.insert(0, BASE)
from backend.main import app

# ── Start server ──────────────────────────────────────────────────────────
def _run():
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')

t = threading.Thread(target=_run, daemon=True)
t.start()

time.sleep(2.5)
webbrowser.open('http://localhost:8000')

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
print()
print('  +----------------------------+')
print('  |    OCR Recibos de Nomina   |')
print('  +----------------------------+')
print(f'  |  http://localhost:8000  |')
print('  +----------------------------+')
print()
print('  Presiona Enter para detener el servidor...')
print()

try:
    input()
except:
    pass

os._exit(0)
