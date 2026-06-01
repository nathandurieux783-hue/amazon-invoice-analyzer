import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  LineChart, Line, Area, AreaChart,
} from 'recharts'

const COLORS = [
  '#FF9900', '#146EB4', '#37A6E0', '#2ECC71', '#E74C3C',
  '#9B59B6', '#F39C12', '#1ABC9C', '#E67E22', '#3498DB',
  '#EC407A', '#26C6DA',
]

const fmt = (n) => `${Number(n).toFixed(2)} €`

function StatCard({ icon, label, value, sub }) {
  return (
    <div className="card text-center">
      <div className="text-3xl mb-2">{icon}</div>
      <p className="text-2xl font-bold text-gray-800">{value}</p>
      <p className="text-sm font-medium text-gray-600 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

function CustomTooltipEuro({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-sm">
      <p className="font-semibold text-gray-700">{label}</p>
      <p className="text-amazon-orange font-bold">{fmt(payload[0].value)}</p>
    </div>
  )
}

function CustomPieTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0]
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-sm">
      <p className="font-semibold text-gray-700">{p.name}</p>
      <p className="text-amazon-orange font-bold">{fmt(p.value)}</p>
      <p className="text-gray-400">{p.payload.pct}%</p>
    </div>
  )
}

function formatMonthLabel(m) {
  // "2024-03" → "Mar 24"
  try {
    const [y, mo] = m.split('-')
    const names = ['Jan','Fév','Mar','Avr','Mai','Juin','Juil','Aoû','Sep','Oct','Nov','Déc']
    return `${names[parseInt(mo, 10) - 1]} ${y.slice(2)}`
  } catch {
    return m
  }
}

export default function AnalysisStep({ data, downloadPath }) {
  if (!data) return null

  const {
    total_spent, invoice_count, valid_count,
    by_category, by_month, cumulative,
    top_invoices, commentary,
  } = data

  const avg = valid_count > 0 ? total_spent / valid_count : 0

  // Pie data with percentage
  const pieData = by_category.map(d => ({
    ...d,
    pct: total_spent > 0 ? ((d.value / total_spent) * 100).toFixed(1) : '0',
  }))

  const barData = by_month.map(d => ({
    ...d,
    label: formatMonthLabel(d.month),
  }))

  const areaData = cumulative.map(d => ({
    ...d,
    label: formatMonthLabel(d.month),
  }))

  return (
    <div className="space-y-8">
      {/* KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard icon="💰" label="Total dépensé" value={fmt(total_spent)} />
        <StatCard icon="📄" label="Factures" value={invoice_count}
          sub={valid_count < invoice_count ? `${valid_count} parsées` : undefined} />
        <StatCard icon="🛒" label="Panier moyen" value={fmt(avg)} />
        <StatCard
          icon="🏷️"
          label="Top catégorie"
          value={by_category[0]?.name ?? '—'}
          sub={by_category[0] ? fmt(by_category[0].value) : undefined}
        />
      </div>

      {/* Commentary */}
      {commentary?.length > 0 && (
        <div>
          <h2 className="text-lg font-bold text-gray-800 mb-3">💬 Interprétations & Commentaires</h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {commentary.map((c, i) => (
              <div key={i} className="card border-l-4 border-amazon-orange">
                <p className="font-semibold text-gray-800 text-sm mb-1">
                  {c.icon} {c.title}
                </p>
                <p className="text-sm text-gray-600 leading-relaxed">{c.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Charts row 1: Pie + Bar */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Pie – by category */}
        <div className="card">
          <h3 className="font-bold text-gray-700 mb-4">Dépenses par catégorie</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  dataKey="value"
                  nameKey="name"
                  label={({ name, pct }) => `${pct}%`}
                  labelLine={false}
                >
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomPieTooltip />} />
                <Legend
                  formatter={(v) => <span className="text-xs text-gray-600">{v}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-sm text-center py-10">Pas de données</p>
          )}
        </div>

        {/* Bar – by month */}
        <div className="card">
          <h3 className="font-bold text-gray-700 mb-4">Dépenses mensuelles</h3>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={v => `${v}€`} tick={{ fontSize: 11 }} width={55} />
                <Tooltip content={<CustomTooltipEuro />} />
                <Bar dataKey="amount" fill="#FF9900" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-sm text-center py-10">Pas de données mensuelles</p>
          )}
        </div>
      </div>

      {/* Area – cumulative */}
      {areaData.length > 1 && (
        <div className="card">
          <h3 className="font-bold text-gray-700 mb-4">Dépenses cumulées dans le temps</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={areaData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <defs>
                <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#FF9900" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#FF9900" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={v => `${v}€`} tick={{ fontSize: 11 }} width={60} />
              <Tooltip content={<CustomTooltipEuro />} />
              <Area
                type="monotone"
                dataKey="total"
                stroke="#FF9900"
                strokeWidth={2.5}
                fill="url(#grad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Category breakdown table */}
      {by_category.length > 0 && (
        <div className="card">
          <h3 className="font-bold text-gray-700 mb-4">Détail par catégorie</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2 text-gray-500 font-medium">Catégorie</th>
                  <th className="text-right py-2 text-gray-500 font-medium">Montant</th>
                  <th className="text-right py-2 text-gray-500 font-medium">Part</th>
                  <th className="py-2 pl-4">Répartition</th>
                </tr>
              </thead>
              <tbody>
                {by_category.map((cat, i) => {
                  const pct = total_spent > 0 ? (cat.value / total_spent * 100) : 0
                  return (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                      <td className="py-2.5">
                        <span className="inline-block w-2.5 h-2.5 rounded-full mr-2"
                              style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                        {cat.name}
                      </td>
                      <td className="py-2.5 text-right font-semibold text-gray-800">
                        {fmt(cat.value)}
                      </td>
                      <td className="py-2.5 text-right text-gray-500">
                        {pct.toFixed(1)}%
                      </td>
                      <td className="py-2.5 pl-4 w-32">
                        <div className="w-full bg-gray-100 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full"
                            style={{
                              width: `${pct}%`,
                              backgroundColor: COLORS[i % COLORS.length],
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Top invoices */}
      {top_invoices?.length > 0 && (
        <div className="card">
          <h3 className="font-bold text-gray-700 mb-4">Top 10 commandes les plus chères</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left py-2 text-gray-500 font-medium">#</th>
                  <th className="text-left py-2 text-gray-500 font-medium">Commande</th>
                  <th className="text-left py-2 text-gray-500 font-medium">Date</th>
                  <th className="text-left py-2 text-gray-500 font-medium">Catégorie</th>
                  <th className="text-right py-2 text-gray-500 font-medium">Montant</th>
                </tr>
              </thead>
              <tbody>
                {top_invoices.map((inv, i) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                    <td className="py-2.5 text-gray-400">{i + 1}</td>
                    <td className="py-2.5 font-mono text-xs text-gray-600">{inv.id}</td>
                    <td className="py-2.5 text-gray-500 text-xs">{inv.date}</td>
                    <td className="py-2.5 text-xs">
                      <span className="inline-block bg-gray-100 text-gray-600 rounded px-1.5 py-0.5 mb-0.5">
                        {inv.category}
                      </span>
                      {inv.products?.length > 0 && (
                        <p className="text-gray-400 text-xs truncate max-w-xs mt-0.5">
                          {inv.products.join(' · ')}
                        </p>
                      )}
                    </td>
                    <td className="py-2.5 text-right font-bold text-amazon-orange">
                      {fmt(inv.total)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Export note */}
      {downloadPath && (
        <div className="rounded-lg bg-green-50 border border-green-200 p-4 text-sm text-green-800 flex items-start gap-3">
          <span className="text-xl">📁</span>
          <div>
            <p className="font-semibold">Factures disponibles localement</p>
            <p className="text-green-700 mt-0.5 font-mono text-xs">{downloadPath}</p>
          </div>
        </div>
      )}
    </div>
  )
}
