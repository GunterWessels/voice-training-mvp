export default function AdminPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-4 space-y-6">
      <div className="bg-white rounded-lg shadow-sm p-4">
        <h1 className="text-xl font-bold text-gray-900">Platform Metrics</h1>
        <p className="text-sm text-gray-500 mt-1">Last 30 days</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: 'Sessions', value: '0' },
          { label: 'Cost (USD)', value: '$0.00' },
          { label: 'Flagged', value: '0' },
          { label: 'Cert Rate', value: '—' },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-lg shadow-sm p-4">
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Flagged sessions placeholder */}
      <div className="bg-white rounded-lg shadow-sm p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Flagged Sessions</h2>
        <p className="text-sm text-gray-400">No flagged sessions.</p>
      </div>
    </div>
  )
}
