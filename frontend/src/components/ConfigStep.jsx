import { useState } from 'react'

function today() {
  return new Date().toISOString().split('T')[0]
}
function oneYearAgo() {
  const d = new Date()
  d.setFullYear(d.getFullYear() - 1)
  return d.toISOString().split('T')[0]
}

export default function ConfigStep({ onBack, onStart }) {
  const [form, setForm] = useState({
    startDate: oneYearAgo(),
    endDate: today(),
  })
  const [error, setError] = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleStart = () => {
    if (form.startDate > form.endDate) {
      setError('La date de début doit être antérieure à la date de fin.')
      return
    }
    setError('')
    onStart(form)
  }

  return (
    <div className="max-w-md mx-auto">
      <div className="card">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">📅</div>
          <h2 className="text-xl font-bold text-gray-800">Période à analyser</h2>
          <p className="text-sm text-gray-500 mt-1">
            Les montants et catégories sont extraits directement depuis Amazon,
            sans téléchargement de fichiers.
          </p>
        </div>

        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Date de début</label>
              <input
                type="date"
                className="input"
                value={form.startDate}
                max={form.endDate}
                onChange={e => set('startDate', e.target.value)}
              />
            </div>
            <div>
              <label className="label">Date de fin</label>
              <input
                type="date"
                className="input"
                value={form.endDate}
                min={form.startDate}
                max={today()}
                onChange={e => set('endDate', e.target.value)}
              />
            </div>
          </div>

          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="rounded-lg bg-blue-50 border border-blue-100 p-4 text-sm text-blue-800">
            <p className="font-semibold mb-1">⚡ Mode rapide</p>
            <p>
              L'analyse se lance dès que le scraping est terminé —
              pas de téléchargement, résultat en quelques secondes par page.
            </p>
          </div>

          <div className="flex gap-3">
            <button className="btn-secondary flex-1" onClick={onBack}>← Retour</button>
            <button className="btn-primary flex-grow-[2]" onClick={handleStart}>
              Lancer le scraping 🚀
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
