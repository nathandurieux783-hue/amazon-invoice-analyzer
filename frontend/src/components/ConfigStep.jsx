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
    downloadPath: '',
  })
  const [pathError, setPathError] = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const validate = () => {
    if (!form.downloadPath.trim()) {
      setPathError('Veuillez indiquer un dossier de téléchargement.')
      return false
    }
    if (form.startDate > form.endDate) {
      setPathError('La date de début doit être antérieure à la date de fin.')
      return false
    }
    setPathError('')
    return true
  }

  const handleStart = () => {
    if (validate()) onStart(form)
  }

  const suggestPath = () => {
    const home = navigator.platform.includes('Mac')
      ? `/Users/${window.location.hostname === 'localhost' ? 'votre_nom' : 'user'}/Downloads/Amazon_Factures`
      : 'C:\\Users\\VotreNom\\Downloads\\Amazon_Factures'
    set('downloadPath', home)
  }

  return (
    <div className="max-w-lg mx-auto">
      <div className="card">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">📅</div>
          <h2 className="text-xl font-bold text-gray-800">Période & Destination</h2>
          <p className="text-sm text-gray-500 mt-1">
            Définissez la période à analyser et où sauvegarder les factures.
          </p>
        </div>

        <div className="space-y-5">
          {/* Date range */}
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

          {/* Download path */}
          <div>
            <label className="label">Dossier de téléchargement</label>
            <div className="flex gap-2">
              <input
                type="text"
                className="input"
                placeholder="/Users/nom/Downloads/Factures_Amazon"
                value={form.downloadPath}
                onChange={e => { set('downloadPath', e.target.value); setPathError('') }}
              />
              <button
                type="button"
                onClick={suggestPath}
                className="btn-secondary text-xs whitespace-nowrap"
                title="Suggérer un chemin"
              >
                Auto
              </button>
            </div>
            {pathError && (
              <p className="text-xs text-red-500 mt-1">{pathError}</p>
            )}
            <p className="text-xs text-gray-400 mt-1">
              Chemin absolu sur votre machine. Le dossier sera créé si inexistant.
            </p>
          </div>

          {/* Summary */}
          <div className="rounded-lg bg-blue-50 border border-blue-100 p-4 text-sm text-blue-800">
            <p className="font-semibold mb-1">Récapitulatif</p>
            <p>Période : <strong>{form.startDate}</strong> → <strong>{form.endDate}</strong></p>
            {form.downloadPath && (
              <p className="mt-0.5 truncate">Dossier : <strong>{form.downloadPath}</strong></p>
            )}
          </div>

          <div className="flex gap-3 mt-2">
            <button className="btn-secondary flex-1" onClick={onBack}>
              ← Retour
            </button>
            <button className="btn-primary flex-2 flex-grow-[2]" onClick={handleStart}>
              Lancer le téléchargement 🚀
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
