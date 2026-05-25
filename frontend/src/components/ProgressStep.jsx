import { useState, useRef, useEffect } from 'react'

const MSG_STYLES = {
  info:    'text-blue-700 bg-blue-50 border-blue-200',
  success: 'text-green-700 bg-green-50 border-green-200',
  warning: 'text-amber-700 bg-amber-50 border-amber-200',
  error:   'text-red-700 bg-red-50 border-red-200',
}
const MSG_ICONS = { info: 'ℹ️', success: '✅', warning: '⚠️', error: '❌' }

export default function ProgressStep({
  messages, orderCount, otpRequired, onOtp, onAnalyze, analyzing
}) {
  const [otp, setOtp] = useState('')
  const logRef = useRef(null)

  const isCompleted = messages.some(m => m.type === 'success' && m.text?.startsWith('Terminé'))
  const hasError    = messages.some(m => m.type === 'error')

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [messages])

  const submitOtp = () => {
    if (otp.trim()) { onOtp(otp.trim()); setOtp('') }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      {/* Status card */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-bold text-gray-800 text-lg">
            {isCompleted ? '✅ Scraping terminé' :
             hasError    ? '❌ Erreur' :
                           '⏳ Récupération en cours…'}
          </h2>
          {orderCount > 0 && (
            <span className="text-2xl font-bold text-amazon-orange">
              {orderCount} <span className="text-gray-400 text-sm font-normal">commande(s)</span>
            </span>
          )}
        </div>

        {!isCompleted && !hasError && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <div className="w-4 h-4 border-2 border-amazon-orange border-t-transparent rounded-full animate-spin" />
            Navigation dans l'historique de commandes…
          </div>
        )}
      </div>

      {/* OTP */}
      {otpRequired && (
        <div className="card border-2 border-amazon-orange">
          <h3 className="font-bold text-gray-800 mb-2">🔑 Code de vérification requis</h3>
          <p className="text-sm text-gray-500 mb-3">
            Amazon demande un code de double authentification.
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              className="input text-center text-xl tracking-widest font-mono"
              placeholder="000000"
              maxLength={8}
              value={otp}
              onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
              onKeyDown={e => e.key === 'Enter' && submitOtp()}
              autoFocus
            />
            <button className="btn-primary whitespace-nowrap" onClick={submitOtp} disabled={otp.length < 4}>
              Valider
            </button>
          </div>
        </div>
      )}

      {/* Log */}
      <div className="card">
        <h3 className="font-semibold text-gray-700 mb-3 text-sm">Journal d'activité</h3>
        <div ref={logRef} className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
          {messages.length === 0 && (
            <p className="text-xs text-gray-400 italic">Démarrage…</p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex items-start gap-2 text-xs rounded-md px-2.5 py-1.5 border ${MSG_STYLES[m.type] || MSG_STYLES.info}`}>
              <span className="mt-0.5 shrink-0">{MSG_ICONS[m.type] || 'ℹ️'}</span>
              <span>{m.text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Launch analysis */}
      {isCompleted && orderCount > 0 && (
        <div className="card bg-gradient-to-r from-amazon-dark to-gray-800 text-white text-center">
          <p className="text-lg font-bold mb-1">
            🎉 {orderCount} commande(s) récupérée(s) !
          </p>
          <p className="text-gray-300 text-sm mb-5">
            Montants et catégories extraits directement depuis Amazon.
          </p>
          <button
            className="bg-amazon-orange hover:bg-yellow-400 text-amazon-dark font-bold
                       px-8 py-3 rounded-xl text-base shadow-lg transition-all
                       hover:scale-105 active:scale-95 disabled:opacity-60 disabled:scale-100"
            onClick={onAnalyze}
            disabled={analyzing}
          >
            {analyzing
              ? <span className="flex items-center gap-2 justify-center"><span className="w-4 h-4 border-2 border-amazon-dark border-t-transparent rounded-full animate-spin"/>Analyse…</span>
              : '📊 Lancer l\'analyse →'}
          </button>
        </div>
      )}

      {isCompleted && orderCount === 0 && (
        <div className="card bg-amber-50 border border-amber-200 text-center">
          <p className="text-amber-800 font-medium">Aucune commande trouvée pour cette période.</p>
          <p className="text-sm text-amber-600 mt-1">Vérifiez les dates ou votre compte Amazon.</p>
        </div>
      )}
    </div>
  )
}
