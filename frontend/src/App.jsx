import { useState, useRef, useCallback } from 'react'
import LoginStep from './components/LoginStep'
import ConfigStep from './components/ConfigStep'
import ProgressStep from './components/ProgressStep'
import AnalysisStep from './components/AnalysisStep'

const STEPS = ['Connexion', 'Configuration', 'Scraping', 'Analyse']

function Stepper({ current }) {
  return (
    <div className="flex items-center justify-center gap-0 mb-10">
      {STEPS.map((label, i) => (
        <div key={i} className="flex items-center">
          <div className="flex flex-col items-center">
            <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-colors
              ${i < current  ? 'bg-green-500 text-white' :
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
  const [messages, setMessages] = useState([])
  const [orderCount, setOrderCount] = useState(0)
  const [scrapedOrders, setScrapedOrders] = useState([])
  const [otpRequired, setOtpRequired] = useState(false)
  const [analysisData, setAnalysisData] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)

  const wsRef = useRef(null)
  const addMsg = useCallback((msg) => setMessages(prev => [...prev, msg]), [])

  const startScraping = useCallback((creds, cfg) => {
    setCredentials(creds)
    setMessages([])
    setOrderCount(0)
    setScrapedOrders([])
    setOtpRequired(false)
    setAnalysisData(null)
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

      } else if (data.type === 'orders_found') {
        setOrderCount(data.count)
        addMsg({ type: 'info', text: `${data.count} commande(s) trouvée(s) en ${data.year}` })

      } else if (data.type === 'warning') {
        addMsg({ type: 'warning', text: data.message })

      } else if (data.type === 'error') {
        addMsg({ type: 'error', text: data.message })

      } else if (data.type === 'completed') {
        const orders = data.orders || []
        setOrderCount(orders.length)
        setScrapedOrders(orders)
        addMsg({
          type: 'success',
          text: `Terminé ! ${orders.length} commande(s) récupérée(s).`,
        })
      }
    }

    ws.onerror = () => addMsg({ type: 'error', text: 'Erreur de connexion WebSocket.' })
  }, [addMsg])

  const sendOtp = useCallback((code) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'otp', code }))
      setOtpRequired(false)
      addMsg({ type: 'info', text: 'Code OTP envoyé…' })
    }
  }, [addMsg])

  const launchAnalysis = useCallback(async () => {
    if (!scrapedOrders.length) return
    setAnalyzing(true)
    try {
      const res = await fetch('/api/analyze-orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ orders: scrapedOrders }),
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
    } finally {
      setAnalyzing(false)
    }
  }, [scrapedOrders, addMsg])

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <header className="bg-amazon-dark text-white shadow-lg">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <span className="text-3xl">📦</span>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Amazon Invoice Analyzer</h1>
            <p className="text-gray-400 text-xs">Analysez vos dépenses Amazon en quelques secondes</p>
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
            orderCount={orderCount}
            otpRequired={otpRequired}
            onOtp={sendOtp}
            onAnalyze={launchAnalysis}
            analyzing={analyzing}
          />
        )}
        {step === 3 && analysisData && (
          <AnalysisStep data={analysisData} />
        )}
      </main>

      <footer className="text-center py-6 text-xs text-gray-400">
        Usage local uniquement — vos identifiants ne sont jamais stockés
      </footer>
    </div>
  )
}
