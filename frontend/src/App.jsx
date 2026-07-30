import { useState, useRef, useCallback } from 'react'

const STEPS = {
  IDLE: 'idle',
  UPLOADING: 'uploading',
  PROCESSING: 'processing',
  DONE: 'done',
  ERROR: 'error',
}

const ACCEPTED = ['.pdf', '.docx', '.doc']

export default function App() {
  const [step, setStep] = useState(STEPS.IDLE)
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)   // { filename, blob }
  const [error, setError] = useState(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef()

  const reset = () => {
    setStep(STEPS.IDLE)
    setFile(null)
    setResult(null)
    setError(null)
  }

  const isValidFile = (f) => {
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    return ACCEPTED.includes(ext)
  }

  const handleFile = useCallback((f) => {
    if (!isValidFile(f)) {
      setError(`Format non supporté. Veuillez uploader un fichier PDF ou DOCX.`)
      setStep(STEPS.ERROR)
      return
    }
    setFile(f)
    setStep(STEPS.IDLE)
    setError(null)
    setResult(null)
  }, [])

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }, [handleFile])

  const onDragOver = (e) => { e.preventDefault(); setDragging(true) }
  const onDragLeave = () => setDragging(false)

  const onInputChange = (e) => {
    const f = e.target.files[0]
    if (f) handleFile(f)
  }

  const generate = async () => {
    if (!file) return
    setStep(STEPS.UPLOADING)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      setStep(STEPS.PROCESSING)
      const res = await fetch('/api/generate', {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Erreur inconnue' }))
        throw new Error(err.detail || `Erreur ${res.status}`)
      }

      const blob = await res.blob()
      const contentDisposition = res.headers.get('Content-Disposition') || ''
      const filenameMatch = contentDisposition.match(/filename="([^"]+)"/)
      const filename = filenameMatch
        ? filenameMatch[1]
        : res.headers.get('X-Filename') || 'Template_Adyton.docx'

      setResult({ filename, blob })
      setStep(STEPS.DONE)
    } catch (e) {
      setError(e.message)
      setStep(STEPS.ERROR)
    }
  }

  const download = () => {
    if (!result) return
    const url = URL.createObjectURL(result.blob)
    const a = document.createElement('a')
    a.href = url
    a.download = result.filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const isLoading = step === STEPS.UPLOADING || step === STEPS.PROCESSING

  return (
    <div style={styles.page}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <span style={styles.logo}>ADYTON</span>
          <span style={styles.logoSub}>CONSEIL</span>
        </div>
        <p style={styles.headerTagline}>Générateur de Templates CV</p>
      </header>

      {/* Main */}
      <main style={styles.main}>
        <div style={styles.card}>
          <h1 style={styles.title}>Templatiser un CV consultant</h1>
          <p style={styles.subtitle}>
            Uploadez un CV au format PDF ou DOCX — le template Adyton Conseil est généré automatiquement.
          </p>

          {/* Drop zone */}
          <div
            style={{
              ...styles.dropzone,
              ...(dragging ? styles.dropzoneDragging : {}),
              ...(file ? styles.dropzoneHasFile : {}),
            }}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onClick={() => !isLoading && inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.doc"
              style={{ display: 'none' }}
              onChange={onInputChange}
              disabled={isLoading}
            />

            {file ? (
              <div style={styles.fileInfo}>
                <span style={styles.fileIcon}>📄</span>
                <div>
                  <p style={styles.fileName}>{file.name}</p>
                  <p style={styles.fileSize}>{(file.size / 1024).toFixed(0)} Ko</p>
                </div>
                {!isLoading && (
                  <button
                    style={styles.removeBtn}
                    onClick={(e) => { e.stopPropagation(); reset() }}
                  >✕</button>
                )}
              </div>
            ) : (
              <div style={styles.dropContent}>
                <span style={styles.dropIcon}>⬆</span>
                <p style={styles.dropText}>Glissez un CV ici ou <span style={styles.link}>parcourir</span></p>
                <p style={styles.dropHint}>PDF, DOCX — max 10 Mo</p>
              </div>
            )}
          </div>

          {/* Status */}
          {isLoading && (
            <div style={styles.statusBox}>
              <div style={styles.spinner} />
              <p style={styles.statusText}>
                {step === STEPS.UPLOADING ? 'Envoi du fichier…' : 'Analyse et génération du template en cours…'}
              </p>
            </div>
          )}

          {step === STEPS.ERROR && (
            <div style={styles.errorBox}>
              <span>⚠️</span>
              <p style={styles.errorText}>{error}</p>
            </div>
          )}

          {step === STEPS.DONE && result && (
            <div style={styles.successBox}>
              <span style={styles.successIcon}>✅</span>
              <div>
                <p style={styles.successTitle}>Template généré avec succès</p>
                <p style={styles.successFile}>{result.filename}</p>
              </div>
            </div>
          )}

          {/* Actions */}
          <div style={styles.actions}>
            {step !== STEPS.DONE ? (
              <button
                style={{
                  ...styles.btnPrimary,
                  ...(!file || isLoading ? styles.btnDisabled : {}),
                }}
                onClick={generate}
                disabled={!file || isLoading}
              >
                {isLoading ? 'Génération…' : 'Générer le template'}
              </button>
            ) : (
              <div style={styles.doneActions}>
                <button style={styles.btnPrimary} onClick={download}>
                  ⬇ Télécharger le .docx
                </button>
                <button style={styles.btnSecondary} onClick={reset}>
                  Nouveau CV
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Info */}
        <div style={styles.infoGrid}>
          {[
            { icon: '🔒', title: 'Zéro contamination', desc: 'Template BASE à placeholders — aucun contenu d\'un autre consultant ne peut se glisser dans le document.' },
            { icon: '⚡', title: 'Génération instantanée', desc: 'Claude analyse le CV et structure les données. Le .docx est prêt en quelques secondes.' },
            { icon: '📋', title: 'Format standard Adyton', desc: 'Compétences, profil, missions, formation — toujours au bon format, prêt à envoyer.' },
          ].map((item) => (
            <div key={item.title} style={styles.infoCard}>
              <span style={styles.infoIcon}>{item.icon}</span>
              <h3 style={styles.infoTitle}>{item.title}</h3>
              <p style={styles.infoDesc}>{item.desc}</p>
            </div>
          ))}
        </div>
      </main>

      <footer style={styles.footer}>
        <p>© {new Date().getFullYear()} Adyton Conseil — Usage interne</p>
      </footer>

      <style>{spinnerCSS}</style>
    </div>
  )
}

const BLUE = '#1B3A6B'
const BLUE_LIGHT = '#2952A3'
const ACCENT = '#E8EFF8'
const GRAY = '#6B7280'
const BORDER = '#E5E7EB'

const styles = {
  page: {
    fontFamily: "'Inter', system-ui, sans-serif",
    minHeight: '100vh',
    background: '#F9FAFB',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    background: BLUE,
    padding: '24px 40px 20px',
    color: 'white',
  },
  headerContent: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '6px',
  },
  logo: {
    fontSize: '22px',
    fontWeight: '700',
    letterSpacing: '3px',
    color: 'white',
  },
  logoSub: {
    fontSize: '13px',
    fontWeight: '400',
    letterSpacing: '2px',
    color: 'rgba(255,255,255,0.7)',
  },
  headerTagline: {
    margin: '4px 0 0',
    fontSize: '13px',
    color: 'rgba(255,255,255,0.6)',
    letterSpacing: '0.5px',
  },
  main: {
    flex: 1,
    maxWidth: '720px',
    width: '100%',
    margin: '0 auto',
    padding: '40px 20px',
  },
  card: {
    background: 'white',
    borderRadius: '12px',
    padding: '40px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.04)',
    marginBottom: '32px',
  },
  title: {
    margin: '0 0 8px',
    fontSize: '22px',
    fontWeight: '700',
    color: BLUE,
  },
  subtitle: {
    margin: '0 0 28px',
    fontSize: '14px',
    color: GRAY,
    lineHeight: '1.6',
  },
  dropzone: {
    border: `2px dashed ${BORDER}`,
    borderRadius: '10px',
    padding: '36px 24px',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
    background: '#FAFAFA',
    marginBottom: '24px',
  },
  dropzoneDragging: {
    borderColor: BLUE_LIGHT,
    background: ACCENT,
  },
  dropzoneHasFile: {
    borderColor: BLUE,
    background: ACCENT,
    cursor: 'default',
  },
  dropContent: {},
  dropIcon: {
    fontSize: '32px',
    display: 'block',
    marginBottom: '12px',
    color: GRAY,
  },
  dropText: {
    margin: '0 0 6px',
    fontSize: '15px',
    color: '#374151',
  },
  link: {
    color: BLUE_LIGHT,
    textDecoration: 'underline',
    cursor: 'pointer',
  },
  dropHint: {
    margin: 0,
    fontSize: '12px',
    color: GRAY,
  },
  fileInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
  },
  fileIcon: {
    fontSize: '28px',
  },
  fileName: {
    margin: '0 0 2px',
    fontWeight: '600',
    fontSize: '14px',
    color: '#111827',
    textAlign: 'left',
  },
  fileSize: {
    margin: 0,
    fontSize: '12px',
    color: GRAY,
    textAlign: 'left',
  },
  removeBtn: {
    marginLeft: 'auto',
    background: 'none',
    border: 'none',
    fontSize: '16px',
    color: GRAY,
    cursor: 'pointer',
    padding: '4px 8px',
    borderRadius: '4px',
  },
  statusBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '14px 16px',
    background: ACCENT,
    borderRadius: '8px',
    marginBottom: '20px',
  },
  spinner: {
    width: '18px',
    height: '18px',
    border: `3px solid ${BORDER}`,
    borderTop: `3px solid ${BLUE}`,
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
    flexShrink: 0,
  },
  statusText: {
    margin: 0,
    fontSize: '14px',
    color: BLUE,
    fontWeight: '500',
  },
  errorBox: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    padding: '14px 16px',
    background: '#FEF2F2',
    border: '1px solid #FECACA',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  errorText: {
    margin: 0,
    fontSize: '14px',
    color: '#B91C1C',
  },
  successBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
    padding: '14px 16px',
    background: '#F0FDF4',
    border: '1px solid #BBF7D0',
    borderRadius: '8px',
    marginBottom: '20px',
  },
  successIcon: {
    fontSize: '22px',
  },
  successTitle: {
    margin: '0 0 2px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#15803D',
  },
  successFile: {
    margin: 0,
    fontSize: '12px',
    color: '#166534',
    fontFamily: 'monospace',
  },
  actions: {
    marginTop: '8px',
  },
  doneActions: {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap',
  },
  btnPrimary: {
    background: BLUE,
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    padding: '12px 24px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'background 0.15s',
    fontFamily: 'inherit',
  },
  btnSecondary: {
    background: 'white',
    color: BLUE,
    border: `1.5px solid ${BORDER}`,
    borderRadius: '8px',
    padding: '12px 24px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    fontFamily: 'inherit',
  },
  btnDisabled: {
    opacity: 0.45,
    cursor: 'not-allowed',
  },
  infoGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '16px',
  },
  infoCard: {
    background: 'white',
    borderRadius: '10px',
    padding: '20px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  },
  infoIcon: {
    fontSize: '22px',
    display: 'block',
    marginBottom: '10px',
  },
  infoTitle: {
    margin: '0 0 6px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#111827',
  },
  infoDesc: {
    margin: 0,
    fontSize: '13px',
    color: GRAY,
    lineHeight: '1.6',
  },
  footer: {
    textAlign: 'center',
    padding: '20px',
    fontSize: '12px',
    color: GRAY,
    borderTop: `1px solid ${BORDER}`,
  },
}

const spinnerCSS = `
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  button:hover:not(:disabled) {
    opacity: 0.9;
  }
  * { box-sizing: border-box; }
  body { margin: 0; }
`
