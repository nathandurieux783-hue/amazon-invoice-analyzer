import { useState, useRef, useCallback } from 'react'
import LoginStep from './components/LoginStep'
import ConfigStep from './components/ConfigStep'
import ProgressStep from './components/ProgressStep'
import AnalysisStep from './components/AnalysisStep'

const STEPS = ['Connexion', 'Configuration', 'Téléchargement', 'Analyse']

function Stepper({ current }) {
  return (
    <div className="flex items-center justify-center gap-0 mb-10">
      {STEPS.map((label, i) => (
        <div key={i} className="flex items-center">
          <div className="flex flex-col items-center">
            <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-colors
              ${i < current ? 'bg-green-500 text-white' :
                i === current ? 'bg-amazon-orange text-amazon-dark' :
                'bg-gray-200 text-gray-400'}`}>
              {i < current ? '✓' : i + 1}
            </div>
            <span className={`mt-1.5 text-xs font-medium whitespace-nowrap
              ${i === current ? 'text-amazon-orange' : 'text-gray-400'}`}>
              {label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`w-16 h-0.5 mx-1 mb-5 transition-colors
              ${i < current ? 'bg-green-500' : 'bg-gray-200'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

export default function App() {
  const [step, setStep] = useState(0)
  const [credentials, setCredentials] = useState(null)
  const [config, setConfig] = useState(null)
  const [messages, setMessages] = useState([])
  const [downloadCount, setDownloadCount] = useState(0)
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const [analysisData, setAnalysisData] = useState(null)
  const [otpRequired, setOtpRequired] = useState(false)

  const wsRef = useRef(null)
  const addMsg = useCallback((msg) => setMessages(prev => [...prev, msg]), [])

  const startScraping = useCallback((creds, cfg) => {
    setCredentials(creds)
    setConfig(cfg)
    setMessages([])
    setDownloadCount(0)
    setProgress({ current: 0, total: 0 })
    setOtpRequired(false)
    setStep(2)

    const ws = new WebSocket('ws://localhost:8000/ws')
    wsRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify({
        type: 'start',
        email: creds.email,
        password: creds.password,
        marketplace: creds.marketplace,
        start_date: cfg.startDate,
        end_date: cfg.endDate,
        download_path: cfg.downloadPath,
      }))
    }

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)

      if (data.type === 'otp_required') {
        setOtpRequired(true)
        addMsg({ type: 'info', text: 'Code de vérification requis.' })

      } else if (data.type === 'captcha_required') {
        addMsg({ type: 'warning', text: data.message })

      } else if (data.type === 'status') {
        addMsg({ type: 'info', text: data.message })
        if (data.total) setProgress(p => ({ ...p, total: data.total }))

      } else if (data.type === 'orders_found') {
        addMsg({ type: 'info', text: `${data.count} commande(s) trouvée(s) en ${data.year}` })

      } else if (data.type === 'progress') {
        setProgress({ current: data.current, total: data.total })
        setDownloadCount(data.current)
        addMsg({ type: 'success', text: data.message })

      } else if (data.type === 'warning') {
        addMsg({ type: 'warning', text: data.message })

      } else if (data.type === 'error') {
        addMsg({ type: 'error', text: data.message })

      } else if (data.type === 'completed') {
        setDownloadCount(data.count)
        addMsg({
          type: 'success',
          text: `Terminé ! ${data.count} facture(s) téléchargée(s).`
        })
      }
    }

    ws.onerror = () => addMsg({ type: 'error', text: 'Erreur de connexion WebSocket.' })
    ws.onclose = () => {}
  }, [addMsg])

  const sendOtp = useCallback((code) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'otp', code }))
      setOtpRequired(false)
      addMsg({ type: 'info', text: 'Code OTP envoyé…' })
    }
  }, [addMsg])

  const launchAnalysis = useCallback(async () => {
    if (!config?.downloadPath) return
    try {
      addMsg({ type: 'info', text: 'Analyse en cours…' })
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ download_path: config.downloadPath }),
      })
      const data = await res.json()
      if (data.error) {
        addMsg({ type: 'error', text: data.error })
      } else {
        setAnalysisData(data)
        setStep(3)
      }
    } catch {
      addMsg({ type: 'error', text: 'Impossible de contacter le serveur d\'analyse.' })
    }
  }, [config, addMsg])

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-amazon-dark text-white shadow-lg">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <span className="text-3xl">📦</span>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Amazon Invoice Analyzer</h1>
            <p className="text-gray-400 text-xs">Téléchargez et analysez vos factures Amazon</p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <Stepper current={step} />

        {step === 0 && (
          <LoginStep onNext={(creds) => { setCredentials(creds); setStep(1) }} />
        )}
        {step === 1 && (
          <ConfigStep
            onBack={() => setStep(0)}
            onStart={(cfg) => startScraping(credentials, cfg)}
          />
        )}
        {step === 2 && (
          <ProgressStep
            messages={messages}
            progress={progress}
            downloadCount={downloadCount}
            otpRequired={otpRequired}
            onOtp={sendOtp}
            downloadPath={config?.downloadPath}
            onAnalyze={launchAnalysis}
          />
        )}
        {step === 3 && analysisData && (
          <AnalysisStep data={analysisData} downloadPath={config?.downloadPath} />
        )}
      </main>

      <footer className="text-center py-6 text-xs text-gray-400">
        Usage local uniquement — vos identifiants ne sont jamais stockés
      </footer>
    </div>
  )
}
