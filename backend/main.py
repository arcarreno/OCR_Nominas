"""
Backend FastAPI para OCR de recibos de nómina
Pipeline de preprocesamiento mejorado con OpenCV
"""
import os
import io
import re
import json
import time
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import asyncio

import cv2
import numpy as np
import pytesseract
from PIL import Image
from PyPDF2 import PdfReader
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

_tesseract = shutil.which('tesseract')
if _tesseract:
    pytesseract.pytesseract.tesseract_cmd = _tesseract
else:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ── TESSDATA / idioma ─────────────────────────────────────────────────────────
_TESSDATA_CANDIDATES = [
    os.environ.get('TESSDATA_PREFIX', ''),
    os.path.join(os.path.dirname(pytesseract.pytesseract.tesseract_cmd), 'tessdata'),
    r'C:\Program Files\Tesseract-OCR\tessdata',
    r'C:\Program Files (x86)\Tesseract-OCR\tessdata',
    '/usr/share/tesseract-ocr/4.00/tessdata',
    '/usr/share/tesseract-ocr/5.00/tessdata',
]
_OCR_LANG = 'spa'
for d in _TESSDATA_CANDIDATES:
    if d and os.path.isfile(os.path.join(d, f'{_OCR_LANG}.traineddata')):
        os.environ['TESSDATA_PREFIX'] = d
        break
else:
    for d in _TESSDATA_CANDIDATES:
        if d and os.path.isfile(os.path.join(d, 'eng.traineddata')):
            os.environ['TESSDATA_PREFIX'] = d
            _OCR_LANG = 'eng'
            break

app = FastAPI(title="OCR Recibos API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Preprocesamiento ──────────────────────────────────────────────────────────

def preprocess_for_ocr(img_pil: Image.Image) -> Image.Image:
    return img_pil


# ── Extracción de campos ──────────────────────────────────────────────────────

def extract_fields(text: str) -> dict:
    def gx(pat, grp=1, default=''):
        m = re.search(pat, text)
        return m.group(grp).strip() if m else default

    no_control = gx(r'CONTROL:\s*(\d+)')
    nombre = gx(r'NOMBRE:\s*([A-Za-z\u00C0-\u024F\s]+?)(?:RFC|\||\d|SECRETARIA)')
    rfc_raw = gx(r'RFC:\s*([A-Za-z0-9]{10,13})')
    rfc = rfc_raw.replace('O', '0').replace('I', '1') if rfc_raw else ''
    curp_raw = gx(r'CURP:\s*([A-Za-z0-9]{17,18})')
    curp = curp_raw.replace('O', '0').replace('I', '1') if curp_raw else ''
    fecha_pago = gx(r'FECHA PAGO[^:]*:\s*([\d\.,]+)').replace(',', '.')
    puesto = gx(r'PUESTO:\s*([A-Za-z\u00C0-\u024F\s]+?)(?:\n|PERIODICIDAD)', 1)
    periodicidad = gx(r'PERIODICIDAD\s*:\s*(\S+)')
    periodo = gx(r'PERIODO:(\d+/\d+)')
    nss = gx(r'N\.?S\.?S\.?:\s*(\d+)')
    dias = gx(r'DIAS:\s*([\d,\.]+)')
    cp = gx(r'CODIGO POSTAL:\s*(\d+)')
    folio = gx(r'FOLIO INTERNO:\s*(\d+)')
    secretaria = gx(r'SECRETARIA:\s*(\d+\s*\S+)')

    m_perc = re.search(r'TOTAL PERCEPCIONES[^\d]*([\d,]+\.\d{2})', text)
    perc = float(m_perc.group(1).replace(',', '')) if m_perc else 0.0

    m_ded = re.search(r'TOTAL DEDUCCIONES[^\d]*([\d,]+\.\d{2})', text)
    ded = float(m_ded.group(1).replace(',', '')) if m_ded else 0.0

    neto_num = 0.0
    for pat in [
        r'NETO PAGADO[^)]*\)\s*([\d,]+\.\d{2})',
        r'NETO PAGADO.*?\([^)]*\)\s*([\d,]+\.\d{2})\)',
        r'NETO PAGADO.*?\([^)]*\)\s*([\d,]+\.\d{2})\|',
        r'NETO PAGADO.*?([\d,]+\.\d{2})\)',
        r'NETO PAGADO.*?([\d,]+\.\d{2})\|',
    ]:
        m_neto = re.search(pat, text)
        if m_neto:
            try:
                neto_num = float(m_neto.group(1).replace(',', ''))
                break
            except:
                pass

    return {
        'no_control': no_control,
        'nombre': nombre,
        'rfc': rfc,
        'curp': curp,
        'fecha_pago': fecha_pago,
        'puesto': puesto,
        'periodicidad': periodicidad,
        'periodo': periodo,
        'nss': nss,
        'dias': dias,
        'cp': cp,
        'folio': folio,
        'secretaria': secretaria,
        'percepciones': perc,
        'deducciones': ded,
        'neto_pagado': neto_num,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    tesseract_path = pytesseract.pytesseract.tesseract_cmd
    exists = os.path.isfile(tesseract_path)
    return {"status": "ok", "tesseract_path": tesseract_path, "tesseract_exists": exists}


@app.post("/api/ocr/process")
async def process_pdf(
    file: UploadFile = File(...),
    pages: Optional[str] = Query(None),
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Solo se aceptan archivos PDF")

    tmp_dir = tempfile.mkdtemp()
    try:
        pdf_path = os.path.join(tmp_dir, file.filename)
        with open(pdf_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        reader = PdfReader(pdf_path)
        total = len(reader.pages)

        page_range = None
        if pages and pages.strip():
            pages = pages.strip()
            print(f"[DEBUG] pages param received: '{pages}'")
            if '-' in pages:
                parts = pages.split('-', 1)
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                page_range = range(start - 1, min(end, total))
                print(f"[DEBUG] range parsed: {start}-{end} -> pages {[p+1 for p in page_range]}")
            elif ',' in pages:
                page_range = [int(p.strip()) - 1 for p in pages.split(',') if 1 <= int(p.strip()) <= total]
                print(f"[DEBUG] list parsed: {[p+1 for p in page_range]}")
            else:
                val = int(pages.strip())
                page_range = [val - 1]
                print(f"[DEBUG] single page: {val}")

        if page_range is None:
            page_range = range(total)
            print(f"[DEBUG] no pages filter, processing all {total}")

        start_time = time.time()
        recibos = []

        for i in page_range:
            page = reader.pages[i]
            xobj = page['/Resources']['/XObject']
            for k in xobj:
                if xobj[k]['/Subtype'] != '/Image':
                    continue
                data = xobj[k].get_data()
                img = Image.open(io.BytesIO(data))

                img_proc = preprocess_for_ocr(img)
                text = pytesseract.image_to_string(img_proc, lang=_OCR_LANG, config='--psm 6')

                fields = extract_fields(text)
                fields['pagina'] = i + 1
                recibos.append(fields)
                break

        elapsed = time.time() - start_time

        stats = {
            'total': len(recibos),
            'no_control': sum(1 for r in recibos if r['no_control']),
            'nombre': sum(1 for r in recibos if r['nombre']),
            'rfc': sum(1 for r in recibos if r['rfc']),
            'curp': sum(1 for r in recibos if r['curp']),
            'puesto': sum(1 for r in recibos if r['puesto']),
            'neto': sum(1 for r in recibos if r['neto_pagado'] > 0),
        }

        total_neto = sum(r['neto_pagado'] for r in recibos)

        return {
            "filename": file.filename,
            "total_pages": total,
            "processed": len(recibos),
            "elapsed_seconds": round(elapsed, 1),
            "stats": stats,
            "total_neto": round(total_neto, 2),
            "recibos": recibos,
        }

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/api/ocr/process-stream")
async def process_pdf_stream(
    file: UploadFile = File(...),
    pages: Optional[str] = Query(None),
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Solo se aceptan archivos PDF")

    file_bytes = await file.read()

    async def sse_generator():
        tmp_dir = tempfile.mkdtemp()
        try:
            pdf_path = os.path.join(tmp_dir, file.filename)
            with open(pdf_path, "wb") as f:
                f.write(file_bytes)

            reader = PdfReader(pdf_path)
            total = len(reader.pages)

            page_range = None
            if pages and pages.strip():
                p = pages.strip()
                if '-' in p:
                    parts = p.split('-', 1)
                    start = int(parts[0].strip())
                    end = int(parts[1].strip())
                    page_range = range(start - 1, min(end, total))
                elif ',' in p:
                    page_range = [int(x.strip()) - 1 for x in p.split(',') if 1 <= int(x.strip()) <= total]
                else:
                    page_range = [int(p.strip()) - 1]

            if page_range is None:
                page_range = range(total)

            pages_list = list(page_range)
            yield f"data: {json.dumps({'type': 'init', 'total_pages': len(pages_list)})}\n\n"
            await asyncio.sleep(0)

            start_time = time.time()
            recibos = []

            for idx, i in enumerate(pages_list):
                page = reader.pages[i]
                xobj = page['/Resources']['/XObject']
                for k in xobj:
                    if xobj[k]['/Subtype'] != '/Image':
                        continue
                    data = xobj[k].get_data()
                    img = Image.open(io.BytesIO(data))

                    img_proc = preprocess_for_ocr(img)
                    text = pytesseract.image_to_string(img_proc, lang=_OCR_LANG, config='--psm 6')

                    fields = extract_fields(text)
                    fields['pagina'] = i + 1
                    recibos.append(fields)
                    break

                progress_msg = json.dumps({
                    'type': 'progress',
                    'pages_processed': idx + 1,
                    'total_pages': len(pages_list),
                    'percent': round((idx + 1) / len(pages_list) * 100, 1),
                    'current_page': i + 1,
                    'last_control': fields.get('no_control', ''),
                    'last_nombre': fields.get('nombre', ''),
                })
                yield f"data: {progress_msg}\n\n"
                await asyncio.sleep(0)

            elapsed = time.time() - start_time

            stats = {
                'total': len(recibos),
                'no_control': sum(1 for r in recibos if r['no_control']),
                'nombre': sum(1 for r in recibos if r['nombre']),
                'rfc': sum(1 for r in recibos if r['rfc']),
                'curp': sum(1 for r in recibos if r['curp']),
                'puesto': sum(1 for r in recibos if r['puesto']),
                'neto': sum(1 for r in recibos if r['neto_pagado'] > 0),
            }

            total_neto = sum(r['neto_pagado'] for r in recibos)

            result = {
                "filename": file.filename,
                "total_pages": total,
                "processed": len(recibos),
                "elapsed_seconds": round(elapsed, 1),
                "stats": stats,
                "total_neto": round(total_neto, 2),
                "recibos": recibos,
            }

            yield f"data: {json.dumps({'type': 'complete', 'result': result})}\n\n"

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@app.post("/api/ocr/validate")
async def validate_ocr(recibos: list[dict]):
    RFC_FISICA = re.compile(r'^[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}$')
    RFC_MORAL = re.compile(r'^[A-ZÑ&]{3}\d{6}[A-Z0-9]{3}$')
    CURP = re.compile(r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$')
    NSS = re.compile(r'^\d{11}$')
    CP = re.compile(r'^\d{5}$')
    FECHA = re.compile(r'^\d{2}\.\d{2}\.\d{4}$')
    FOLIO = re.compile(r'^\d{4,5}$')
    DIAS_OK = re.compile(r'^15\.00$')
    PUESTOS = {
        "COORDINADOR ESPECIALIZADO", "COORDINADORA ESPECIALIZAD", "COORDINADOR TECNICO",
        "COORDINADORA TECNICA", "ANALISTA A", "ANALISTA B", "ANALISTA CONSULTIVO A",
        "ANALISTA CONSULTIVO B", "ANALISTA CONSULTIVO C", "ANALISTA CONSULTIVA A",
        "ANALISTA CONSULTIVA C", "SUPERVISOR A", "SUPERVISOR D", "SUPERVISORA D",
    }

    issues = []
    for rec in recibos:
        pagina = rec.get('pagina', 0)
        nombre = rec.get('nombre', '')
        rfc = rec.get('rfc', '')
        curp = rec.get('curp', '')
        nss = rec.get('nss', '')
        cp = rec.get('cp', '')
        fecha = rec.get('fecha_pago', '')
        folio = rec.get('folio', '')
        dias = rec.get('dias', '')
        puesto = rec.get('puesto', '')
        periodicidad = rec.get('periodicidad', '')
        no_control = rec.get('no_control', '')
        perc = rec.get('percepciones', 0)
        ded = rec.get('deducciones', 0)
        neto = rec.get('neto_pagado', 0)

        if '\n' in nombre:
            issues.append({'pagina': pagina, 'campo': 'nombre', 'problema': f'texto adicional pegado'})
        if not nombre:
            issues.append({'pagina': pagina, 'campo': 'nombre', 'problema': 'vacío'})
        if rfc and not (RFC_FISICA.match(rfc) or RFC_MORAL.match(rfc)):
            issues.append({'pagina': pagina, 'campo': 'rfc', 'problema': f'formato inválido: {rfc}'})
        if not rfc:
            issues.append({'pagina': pagina, 'campo': 'rfc', 'problema': 'vacío'})
        if curp and not CURP.match(curp):
            issues.append({'pagina': pagina, 'campo': 'curp', 'problema': f'formato inválido: {curp}'})
        if not curp:
            issues.append({'pagina': pagina, 'campo': 'curp', 'problema': 'vacío'})
        if nss and not NSS.match(nss):
            issues.append({'pagina': pagina, 'campo': 'nss', 'problema': f'no tiene 11 dígitos: {nss}'})
        if cp and not CP.match(cp):
            issues.append({'pagina': pagina, 'campo': 'cp', 'problema': f'formato inválido: {cp}'})
        if not cp:
            issues.append({'pagina': pagina, 'campo': 'cp', 'problema': 'vacío'})
        if fecha and not FECHA.match(fecha):
            issues.append({'pagina': pagina, 'campo': 'fecha_pago', 'problema': f'incompleta: {fecha}'})
        if not fecha:
            issues.append({'pagina': pagina, 'campo': 'fecha_pago', 'problema': 'vacío'})
        if folio and not FOLIO.match(folio):
            issues.append({'pagina': pagina, 'campo': 'folio', 'problema': f'formato inesperado: {folio}'})
        if not folio:
            issues.append({'pagina': pagina, 'campo': 'folio', 'problema': 'vacío'})
        if dias and not DIAS_OK.match(dias) and dias:
            issues.append({'pagina': pagina, 'campo': 'dias', 'problema': f'distinto de 15.00: {dias}'})
        if not dias:
            issues.append({'pagina': pagina, 'campo': 'dias', 'problema': 'vacío'})
        if puesto and puesto not in PUESTOS:
            issues.append({'pagina': pagina, 'campo': 'puesto', 'problema': f'no en catálogo: {puesto}'})
        if not puesto:
            issues.append({'pagina': pagina, 'campo': 'puesto', 'problema': 'vacío'})
        if periodicidad and periodicidad != "QUINCENAL":
            issues.append({'pagina': pagina, 'campo': 'periodicidad', 'problema': f'valor inesperado: {periodicidad}'})
        if no_control and not re.match(r'^\d{6,8}$', no_control):
            issues.append({'pagina': pagina, 'campo': 'no_control', 'problema': f'formato inesperado: {no_control}'})
        if not no_control:
            issues.append({'pagina': pagina, 'campo': 'no_control', 'problema': 'vacío'})
        if perc > 0 and ded == 0 and neto == 0:
            issues.append({'pagina': pagina, 'campo': 'montos', 'problema': 'percepciones > 0 pero deducciones y neto en 0'})
        if perc == 0 and ded == 0 and neto == 0:
            issues.append({'pagina': pagina, 'campo': 'montos', 'problema': 'las 3 cifras están en 0'})

    paginas_con_problema = len({r['pagina'] for r in issues})
    conteo = {}
    for r in issues:
        conteo[r['campo']] = conteo.get(r['campo'], 0) + 1

    return {
        'total_registros': len(recibos),
        'paginas_con_problema': paginas_con_problema,
        'total_incidencias': len(issues),
        'porcentaje_problema': round(paginas_con_problema / len(recibos) * 100, 1) if recibos else 0,
        'conteo_por_campo': dict(sorted(conteo.items(), key=lambda x: -x[1])),
        'incidencias': issues,
    }


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.isdir(STATIC_DIR):
    STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "dist")
if not os.path.isdir(STATIC_DIR):
    STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
