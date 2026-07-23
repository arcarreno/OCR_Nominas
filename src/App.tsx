import { useState, useCallback, useRef, useEffect } from 'react'
import * as XLSX from 'xlsx'
import './App.css'

interface Recibo {
  pagina: number
  no_control: string
  nombre: string
  rfc: string
  curp: string
  fecha_pago: string
  puesto: string
  periodicidad: string
  periodo: string
  nss: string
  dias: string
  cp: string
  folio: string
  secretaria: string
  percepciones: number
  deducciones: number
  neto_pagado: number
}

interface OCRResult {
  filename: string
  total_pages: number
  processed: number
  elapsed_seconds: number
  stats: {
    total: number
    no_control: number
    nombre: number
    rfc: number
    curp: number
    puesto: number
    neto: number
  }
  total_neto: number
  recibos: Recibo[]
}

interface ValidationIssue {
  pagina: number
  campo: string
  problema: string
}

interface ValidationResult {
  total_registros: number
  paginas_con_problema: number
  total_incidencias: number
  porcentaje_problema: number
  conteo_por_campo: Record<string, number>
  incidencias: ValidationIssue[]
}

interface ProgressInfo {
  percent: number
  message: string
  pagesProcessed: number
  totalPages: number
}

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [pages, setPages] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<OCRResult | null>(null)
  const [validation, setValidation] = useState<ValidationResult | null>(null)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'results' | 'validation' | 'raw' | 'compare'>('results')
  const [search, setSearch] = useState('')
  const [progress, setProgress] = useState<ProgressInfo | null>(null)
  const [excelControls, setExcelControls] = useState<string[]>([])
  const [excelFileName, setExcelFileName] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort()
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected && selected.type === 'application/pdf') {
      setFile(selected)
      setError('')
      setResult(null)
      setValidation(null)
      setProgress(null)
    } else {
      setError('Selecciona un archivo PDF valido')
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const dropped = e.dataTransfer.files[0]
    if (dropped && dropped.type === 'application/pdf') {
      setFile(dropped)
      setError('')
      setResult(null)
      setValidation(null)
      setProgress(null)
    }
  }, [])

  const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '')

  const processPDF = async () => {
    if (!file) return
    setLoading(true)
    setError('')
    setResult(null)
    setValidation(null)
    abortRef.current = new AbortController()

    setProgress({
      percent: 0,
      message: 'Enviando archivo al servidor...',
      pagesProcessed: 0,
      totalPages: 0,
    })

    try {
      const formData = new FormData()
      formData.append('file', file)

      const apiBase = API_URL || window.location.origin
      const url = new URL('/api/ocr/process', apiBase)
      if (pages.trim()) url.searchParams.set('pages', pages.trim())

      const response = await fetch(url.toString(), {
        method: 'POST',
        body: formData,
        signal: abortRef.current.signal,
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Error al procesar el PDF')
      }

      const data: OCRResult = await response.json()

      setProgress({
        percent: 100,
        message: `OCR completado. ${data.processed} paginas procesadas en ${data.elapsed_seconds}s`,
        pagesProcessed: data.processed,
        totalPages: data.total_pages,
      })

      setResult(data)

      const valResponse = await fetch(new URL('/api/ocr/validate', apiBase).toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data.recibos),
      })

      if (valResponse.ok) {
        const valData: ValidationResult = await valResponse.json()
        setValidation(valData)
      }

      setTimeout(() => setProgress(null), 4000)

    } catch (err: any) {
      if (err.name === 'AbortError') {
        setError('Proceso cancelado')
      } else {
        setError(err.message || 'Error al conectar con el servidor')
      }
      setProgress(null)
    } finally {
      setLoading(false)
    }
  }

  const cancelProcess = () => {
    if (abortRef.current) {
      abortRef.current.abort()
      setLoading(false)
      setProgress(null)
    }
  }

  const filteredRecibos = result?.recibos.filter(r => {
    if (!search.trim()) return true
    const q = search.toLowerCase()
    return (
      r.no_control?.toLowerCase().includes(q) ||
      r.nombre?.toLowerCase().includes(q) ||
      r.rfc?.toLowerCase().includes(q)
    )
  }) || []

  const downloadJSON = () => {
    if (!result) return
    const blob = new Blob([JSON.stringify(result.recibos, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${result.filename.replace('.pdf', '')}_ocr.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadCSV = () => {
    if (!result) return
    const headers = ['pagina', 'no_control', 'nombre', 'rfc', 'curp', 'fecha_pago', 'puesto', 'periodicidad', 'periodo', 'nss', 'dias', 'cp', 'folio', 'secretaria', 'percepciones', 'deducciones', 'neto_pagado']
    const rows = result.recibos.map(r => headers.map(h => {
      const val = (r as any)[h]
      return typeof val === 'string' && val.includes(',') ? `"${val}"` : val
    }).join(','))
    const csv = [headers.join(','), ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${result.filename.replace('.pdf', '')}_ocr.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleExcelUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (!selected) return
    setExcelFileName(selected.name)
    const reader = new FileReader()
    reader.onload = (evt) => {
      const wb = XLSX.read(evt.target?.result, { type: 'binary' })
      const ws = wb.Sheets[wb.SheetNames[0]]
      const data = XLSX.utils.sheet_to_json<string[]>(ws, { header: 1 })
      const controls: string[] = []
      for (const row of data) {
        const val = row[1]
        if (val !== undefined && val !== null) {
          const str = String(val).trim()
          if (str && /^\d+$/.test(str)) {
            controls.push(str)
          }
        }
      }
      setExcelControls(controls)
    }
    reader.readAsBinaryString(selected)
  }, [])

  const controlsEnOCRnoEnExcel = result?.recibos.filter(r => {
    if (!r.no_control) return false
    const normalized = r.no_control.replace(/^0+/, '')
    return !excelControls.some(ec => ec.replace(/^0+/, '') === normalized)
  }) || []

  return (
    <div className="app">
      <header className="header">
        <h1>OCR Recibos de Nomina</h1>
      </header>

      <main className="main">
        <section className="upload-section">
          <div
            className={`dropzone ${file ? 'has-file' : ''}`}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
          >
            <input
              type="file"
              id="file-input"
              accept=".pdf"
              onChange={handleFileChange}
              hidden
            />
            <label htmlFor="file-input" className="dropzone-label">
              {file ? (
                <>
                  <span className="file-name">{file.name}</span>
                  <span className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                </>
              ) : (
                <span>Arrastra un PDF o haz clic para seleccionar</span>
              )}
            </label>
          </div>

          <div className="options">
            <div className="option-group">
              <label htmlFor="pages-input">Paginas (opcional):</label>
              <input
                id="pages-input"
                type="text"
                placeholder="Ej: 1-10, 15, 20-30"
                value={pages}
                onChange={(e) => setPages(e.target.value)}
                className="pages-input"
                disabled={loading}
              />
            </div>
            {loading ? (
              <button className="process-btn" onClick={cancelProcess}>
                Cancelar
              </button>
            ) : (
              <button
                className="process-btn"
                onClick={processPDF}
                disabled={!file}
              >
                Procesar PDF
              </button>
            )}
          </div>

          {progress && (
            <div className="progress-container">
              <div className="progress-info">
                <span className="progress-label">{progress.message}</span>
                {progress.totalPages > 0 && (
                  <span className="progress-percent">{Math.round(progress.percent)}%</span>
                )}
              </div>
              <div className="progress-bar-track">
                <div
                  className={`progress-bar-fill ${progress.percent === 0 ? 'indeterminate' : ''}`}
                  style={{ width: progress.totalPages > 0 ? `${Math.max(progress.percent, 5)}%` : '100%' }}
                />
              </div>
              {progress.totalPages > 0 && (
                <div className="progress-detail">
                  {progress.pagesProcessed} / {progress.totalPages} paginas procesadas
                </div>
              )}
            </div>
          )}

          {error && <div className="error-message">{error}</div>}
        </section>

        {result && (
          <section className="results-section">
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{result.processed}</div>
                <div className="stat-label">Paginas procesadas</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{result.elapsed_seconds}s</div>
                <div className="stat-label">Tiempo total</div>
              </div>
              <div className="stat-card accent">
                <div className="stat-value">${result.total_neto.toLocaleString()}</div>
                <div className="stat-label">Neto total</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{result.stats.nombre}/{result.stats.total}</div>
                <div className="stat-label">Nombres extraidos</div>
              </div>
            </div>

            {validation && (
              <div className={`quality-badge ${validation.porcentaje_problema > 50 ? 'bad' : validation.porcentaje_problema > 20 ? 'warn' : 'good'}`}>
                <span className="quality-label">Calidad OCR:</span>
                <span className="quality-value">{100 - validation.porcentaje_problema}%</span>
                <span className="quality-detail">
                  ({validation.paginas_con_problema} paginas con issues de {validation.total_registros})
                </span>
              </div>
            )}

            <div className="tabs-row">
              <div className="tabs">
                <button
                  className={`tab ${activeTab === 'results' ? 'active' : ''}`}
                  onClick={() => setActiveTab('results')}
                >
                  Resultados
                </button>
                <button
                  className={`tab ${activeTab === 'validation' ? 'active' : ''}`}
                  onClick={() => setActiveTab('validation')}
                >
                  Validacion
                </button>
                <button
                  className={`tab ${activeTab === 'raw' ? 'active' : ''}`}
                  onClick={() => setActiveTab('raw')}
                >
                  Datos Crudos
                </button>
                <button
                  className={`tab ${activeTab === 'compare' ? 'active' : ''}`}
                  onClick={() => setActiveTab('compare')}
                >
                  Comparacion
                </button>
              </div>
              {activeTab === 'results' && (
                <div className="search-box">
                  <input
                    type="text"
                    placeholder="Buscar por No.Control, Nombre o RFC..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="search-input"
                  />
                  {search && (
                    <span className="search-count">{filteredRecibos.length} / {result!.recibos.length}</span>
                  )}
                </div>
              )}
            </div>

            <div className="tab-content">
              {activeTab === 'results' && (
                <div className="results-table-container">
                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>Pag</th>
                        <th>No. Control</th>
                        <th>Nombre</th>
                        <th>RFC</th>
                        <th>CURP</th>
                        <th>Puesto</th>
                        <th>Neto</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRecibos.map((r, i) => (
                        <tr key={i}>
                          <td>{r.pagina}</td>
                          <td className="mono">{r.no_control}</td>
                          <td>{r.nombre}</td>
                          <td className="mono">{r.rfc}</td>
                          <td className="mono">{r.curp}</td>
                          <td>{r.puesto}</td>
                          <td className="number">${r.neto_pagado.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {activeTab === 'validation' && validation && (
                <div className="validation-section">
                  <div className="validation-summary">
                    <h3>Incidencias por Campo</h3>
                    <div className="field-bars">
                      {Object.entries(validation.conteo_por_campo).map(([campo, count]) => (
                        <div key={campo} className="field-bar">
                          <span className="field-name">{campo}</span>
                          <div className="bar-container">
                            <div
                              className="bar-fill"
                              style={{ width: `${(count / validation.total_registros) * 100}%` }}
                            ></div>
                          </div>
                          <span className="field-count">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="validation-details">
                    <h3>Detalle de Incidencias</h3>
                    <table className="validation-table">
                      <thead>
                        <tr>
                          <th>Pag</th>
                          <th>Campo</th>
                          <th>Problema</th>
                        </tr>
                      </thead>
                      <tbody>
                        {validation.incidencias.slice(0, 100).map((inc, i) => (
                          <tr key={i}>
                            <td>{inc.pagina}</td>
                            <td><span className={`campo-badge ${inc.campo}`}>{inc.campo}</span></td>
                            <td>{inc.problema}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {validation.incidencias.length > 100 && (
                      <p className="more-issues">
                        ... y {validation.incidencias.length - 100} incidencias mas
                      </p>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'raw' && (
                <div className="raw-section">
                  <pre className="raw-json">
                    {JSON.stringify(result.recibos, null, 2)}
                  </pre>
                </div>
              )}

              {activeTab === 'compare' && (
                <div className="compare-section">
                  <div className="compare-upload">
                    <label htmlFor="excel-input" className="compare-label">
                      Selecciona el Excel de referencia:
                    </label>
                    <input
                      type="file"
                      id="excel-input"
                      accept=".xlsx,.xls"
                      onChange={handleExcelUpload}
                      hidden
                    />
                    <label htmlFor="excel-input" className="compare-file-btn">
                      Seleccionar archivo
                    </label>
                    {excelFileName && (
                      <span className="compare-file-name">{excelFileName} ({excelControls.length} controles cargados)</span>
                    )}
                  </div>

                  {excelControls.length > 0 && (
                    <>
                      <div className="compare-summary">
                        <span className="compare-total">
                          {controlsEnOCRnoEnExcel.length} controles en OCR pero no en el Excel
                        </span>
                      </div>
                      <table className="results-table">
                        <thead>
                          <tr>
                            <th>Pag</th>
                            <th>No. Control</th>
                            <th>Nombre</th>
                            <th>RFC</th>
                          </tr>
                        </thead>
                        <tbody>
                          {controlsEnOCRnoEnExcel.map((r, i) => (
                            <tr key={i}>
                              <td>{r.pagina}</td>
                              <td className="mono">{r.no_control}</td>
                              <td>{r.nombre}</td>
                              <td className="mono">{r.rfc}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="export-buttons">
              <button className="export-btn" onClick={downloadJSON}>
                Descargar JSON
              </button>
              <button className="export-btn" onClick={downloadCSV}>
                Descargar CSV
              </button>
            </div>
          </section>
        )}
      </main>

      <footer className="footer">
        <p>Reconocimiento OCR v2.0 Angel Armando Carreno Gonzalez</p>
      </footer>
    </div>
  )
}

export default App
