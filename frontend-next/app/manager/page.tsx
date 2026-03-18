'use client'
import { useEffect, useState } from 'react'
import CCEHeader from '@/components/CCEHeader'

interface Rep {
  id: string
  name: string
  sessions: number
  last_active: string | null
  certified: boolean
}

interface CohortData {
  total_reps: number
  certified_reps: number
  reps: Rep[]
}

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

export default function ManagerPage() {
  const [cohort, setCohort] = useState<CohortData>({ total_reps: 0, certified_reps: 0, reps: [] })

  useEffect(() => {
    fetch(`${API}/api/manager/cohort`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setCohort(data) })
      .catch(() => {/* silent */})
  }, [])

  const certPct = cohort.total_reps > 0
    ? Math.round((cohort.certified_reps / cohort.total_reps) * 100)
    : 0

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <CCEHeader />

      <main className="flex-1 p-4 space-y-3 max-w-2xl mx-auto w-full">
        {/* Cohort header */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-[16px] font-bold text-[#1a202c]">Cohort Overview</h1>
            <span className="text-sm font-bold text-[#0073CF]">
              {cohort.certified_reps} of {cohort.total_reps} certified
            </span>
          </div>
          <div className="h-1.5 bg-[#e2e8f0] rounded overflow-hidden mb-3">
            <div
              className="h-full bg-[#0073CF] rounded transition-all duration-500"
              style={{ width: `${certPct}%` }}
            />
          </div>
          <a
            href={`${API}/api/manager/export`}
            className="text-sm text-[#0073CF] hover:underline"
          >
            Export CSV
          </a>
        </div>

        {/* Rep table */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[#f8fafc] border-b border-[#e2e8f0]">
              <tr>
                {['Name', 'Sessions', 'Last Active', 'Cert'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold text-[#718096] uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cohort.reps.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-[#a0aec0]">
                    No reps enrolled yet.
                  </td>
                </tr>
              ) : cohort.reps.map(rep => (
                <tr key={rep.id} className="border-t border-[#e2e8f0]">
                  <td className="px-4 py-3 text-[#1a202c] font-medium text-sm">{rep.name}</td>
                  <td className="px-4 py-3 text-[#718096] text-sm">{rep.sessions}</td>
                  <td className="px-4 py-3 text-[#718096] text-sm">{rep.last_active ?? '—'}</td>
                  <td className="px-4 py-3 text-sm">
                    {rep.certified
                      ? <span className="text-[#1a7a3f] font-bold">✓</span>
                      : <span className="text-[#a0aec0]">—</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}
