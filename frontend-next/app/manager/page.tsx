export default function ManagerPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-4 space-y-6">
      <div className="bg-white rounded-lg shadow-sm p-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Cohort Overview</h1>
          <p className="text-sm text-gray-500 mt-1">0 reps enrolled</p>
        </div>
        <a
          href="/api/manager/export"
          className="text-sm text-blue-600 hover:underline"
        >
          Export CSV
        </a>
      </div>

      {/* Rep table */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              {['Name', 'Sessions', 'Last Active', 'Cert'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-400">
                No reps enrolled yet.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
