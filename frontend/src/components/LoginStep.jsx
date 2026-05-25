import { useState } from 'react'

const MARKETPLACES = [
  { value: 'amazon.fr', label: '🇫🇷 amazon.fr' },
  { value: 'amazon.com', label: '🇺🇸 amazon.com' },
  { value: 'amazon.de', label: '🇩🇪 amazon.de' },
  { value: 'amazon.co.uk', label: '🇬🇧 amazon.co.uk' },
  { value: 'amazon.es', label: '🇪🇸 amazon.es' },
  { value: 'amazon.it', label: '🇮🇹 amazon.it' },
]

export default function LoginStep({ onNext }) {
  const [form, setForm] = useState({
    email: '',
    password: '',
    marketplace: 'amazon.fr',
  })
  const [showPwd, setShowPwd] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const valid = form.email.includes('@') && form.password.length >= 3

  return (
    <div className="max-w-md mx-auto">
      <div className="card">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🔐</div>
          <h2 className="text-xl font-bold text-gray-800">Connexion Amazon</h2>
          <p className="text-sm text-gray-500 mt-1">
            Vos identifiants sont utilisés localement et ne sont jamais stockés.
          </p>
        </div>

        <div className="space-y-5">
          <div>
            <label className="label">Marketplace</label>
            <select
              className="input bg-white"
              value={form.marketplace}
              onChange={e => set('marketplace', e.target.value)}
            >
              {MARKETPLACES.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Adresse e-mail</label>
            <input
              type="email"
              className="input"
              placeholder="votre@email.com"
              value={form.email}
              onChange={e => set('email', e.target.value)}
              autoComplete="email"
            />
          </div>

          <div>
            <label className="label">Mot de passe</label>
            <div className="relative">
              <input
                type={showPwd ? 'text' : 'password'}
                className="input pr-10"
                placeholder="••••••••"
                value={form.password}
                onChange={e => set('password', e.target.value)}
                autoComplete="current-password"
                onKeyDown={e => e.key === 'Enter' && valid && onNext(form)}
              />
              <button
                type="button"
                onClick={() => setShowPwd(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showPwd ? '🙈' : '👁️'}
              </button>
            </div>
          </div>

          <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">
            <strong>Note :</strong> Si votre compte utilise la double authentification (OTP),
            un code vous sera demandé à l'étape suivante. Un navigateur s'ouvrira automatiquement.
          </div>

          <button
            className="btn-primary w-full mt-2"
            disabled={!valid}
            onClick={() => onNext(form)}
          >
            Suivant →
          </button>
        </div>
      </div>
    </div>
  )
}
