export default function Dashboard() {
  return (
    <div className="min-h-screen bg-gray-50 p-4 space-y-6">
      <div className="bg-white rounded-lg shadow-sm p-4">
        <h1 className="text-xl font-bold text-gray-900">My Training</h1>
        <p className="text-sm text-gray-500 mt-1">Complete your assigned simulations to earn certification.</p>
      </div>

      {/* Practice Queue */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Practice Queue</h2>
        <div className="bg-white rounded-lg shadow-sm p-4 flex items-center justify-between">
          <div>
            <p className="font-medium text-gray-900 text-sm">VAC Stakeholder — Tria Stents</p>
            <p className="text-xs text-gray-500 mt-0.5">VAC Buyer · 6 stages</p>
          </div>
          <a
            href="/session/new?series=tria-stents"
            className="bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            Start
          </a>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Sessions', value: '0' },
          { label: 'Certs', value: '0' },
          { label: 'Streak', value: '0d' },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-lg shadow-sm p-3 text-center">
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
