import { useState, useEffect, useCallback } from 'react'

export default function FolderBrowser({ onSelect, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [newFolderMode, setNewFolderMode] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [creating, setCreating] = useState(false)

  const navigate = useCallback(async (path = '') => {
    setLoading(true)
    setError('')
    setNewFolderMode(false)
    try {
      const url = '/api/browse' + (path ? `?path=${encodeURIComponent(path)}` : '')
      const res = await fetch(url)
      const json = await res.json()
      if (json.error) setError(json.error)
      else setData(json)
    } catch {
      setError('Impossible de contacter le serveur.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { navigate() }, [navigate])

  const createFolder = async () => {
    if (!newFolderName.trim() || !data) return
    setCreating(true)
    try {
      const res = await fetch('/api/mkdir', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: data.path, name: newFolderName.trim() }),
      })
      const json = await res.json()
      if (json.ok) {
        setNewFolderName('')
        setNewFolderMode(false)
        await navigate(data.path)
      } else {
        setError(json.error || 'Erreur lors de la création.')
      }
    } finally {
      setCreating(false)
    }
  }

  // Build breadcrumb segments from path
  const breadcrumbs = data
    ? data.path.split('/').filter(Boolean).map((seg, i, arr) => ({
        label: seg,
        path: '/' + arr.slice(0, i + 1).join('/'),
      }))
    : []

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg flex flex-col"
           style={{ maxHeight: '80vh' }}>

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h3 className="font-bold text-gray-800 text-base">Choisir un dossier</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >×</button>
        </div>

        {/* Breadcrumb */}
        {data && (
          <div className="px-5 py-2.5 bg-gray-50 border-b border-gray-100 flex items-center gap-1 flex-wrap text-xs">
            <button
              onClick={() => navigate('')}
              className="text-amazon-blue hover:underline font-medium"
            >~</button>
            {breadcrumbs.map((b, i) => (
              <span key={i} className="flex items-center gap-1">
                <span className="text-gray-300">/</span>
                {i < breadcrumbs.length - 1 ? (
                  <button
                    onClick={() => navigate(b.path)}
                    className="text-amazon-blue hover:underline"
                  >{b.label}</button>
                ) : (
                  <span className="text-gray-700 font-semibold">{b.label}</span>
                )}
              </span>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-3 py-3">
          {loading && (
            <div className="flex items-center justify-center py-12 text-gray-400 gap-2">
              <div className="w-4 h-4 border-2 border-amazon-orange border-t-transparent rounded-full animate-spin" />
              Chargement…
            </div>
          )}

          {error && (
            <div className="text-red-500 text-sm text-center py-4">{error}</div>
          )}

          {!loading && !error && data && (
            <div className="space-y-0.5">
              {/* Parent folder */}
              {data.parent && (
                <button
                  onClick={() => navigate(data.parent)}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-100 text-sm text-gray-500 transition-colors"
                >
                  <span className="text-lg">⬆️</span>
                  <span className="italic">Dossier parent</span>
                </button>
              )}

              {/* Subdirectories */}
              {data.dirs.length === 0 && (
                <p className="text-center text-gray-400 text-sm py-6 italic">
                  Dossier vide (aucun sous-dossier)
                </p>
              )}
              {data.dirs.map((dir) => (
                <button
                  key={dir.path}
                  onClick={() => navigate(dir.path)}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-blue-50 text-sm text-gray-700 transition-colors text-left group"
                >
                  <span className="text-xl shrink-0">📁</span>
                  <span className="truncate flex-1">{dir.name}</span>
                  <span className="text-gray-300 group-hover:text-gray-400 shrink-0">›</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* New folder */}
        {!loading && data && (
          <div className="px-4 py-3 border-t border-gray-100">
            {newFolderMode ? (
              <div className="flex gap-2">
                <input
                  autoFocus
                  type="text"
                  className="input flex-1 text-sm"
                  placeholder="Nom du nouveau dossier"
                  value={newFolderName}
                  onChange={e => setNewFolderName(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') createFolder()
                    if (e.key === 'Escape') { setNewFolderMode(false); setNewFolderName('') }
                  }}
                />
                <button
                  className="btn-primary text-sm py-1.5 px-3"
                  onClick={createFolder}
                  disabled={creating || !newFolderName.trim()}
                >
                  {creating ? '…' : 'Créer'}
                </button>
                <button
                  className="btn-secondary text-sm py-1.5 px-3"
                  onClick={() => { setNewFolderMode(false); setNewFolderName('') }}
                >
                  Annuler
                </button>
              </div>
            ) : (
              <button
                onClick={() => setNewFolderMode(true)}
                className="text-xs text-amazon-blue hover:underline flex items-center gap-1"
              >
                <span>＋</span> Nouveau dossier ici
              </button>
            )}
          </div>
        )}

        {/* Footer */}
        {data && (
          <div className="px-5 py-4 border-t border-gray-100 flex items-center justify-between gap-3 bg-gray-50 rounded-b-2xl">
            <p className="text-xs text-gray-500 truncate flex-1 font-mono">{data.path}</p>
            <div className="flex gap-2 shrink-0">
              <button className="btn-secondary text-sm py-1.5" onClick={onClose}>
                Annuler
              </button>
              <button
                className="btn-primary text-sm py-1.5"
                onClick={() => onSelect(data.path)}
              >
                Sélectionner ce dossier ✓
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
