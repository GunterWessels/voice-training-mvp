'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'
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
  const [authHeader, setAuthHeader] = useState<Record<string, string>>({})

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getSession().then(({ data: { session } }) => {
      const headers: Record<string, string> = session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {}
      setAuthHeader(headers)

      fetch(`${API}/api/manager/cohort`, { headers })
        .then(r => r.ok ? r.json() : null)
        .then(data => { if (data) setCohort(data) })
        .catch(() => {/* silent */})
    })
  }, [])

  const certPct = cohort.total_reps > 0
    ? Math.round((cohort.certified_reps / cohort.total_reps) * 100)
    : 0

  async function handleExportCSV() {
    const res = await fetch(`${API}/api/manager/export`, { headers: authHeader })
    if (!res.ok) return
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'cohort.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="bg-[#10141a] min-h-screen flex flex-col">
      <CCEHeader />

      <main className="flex-1 p-4 space-y-3 max-w-2xl mx-auto w-full">
        {/* Cohort header */}
        <div className="bg-[#1c2026] rounded-xl p-4" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-[16px] font-bold text-[#e8eaed]">Cohort Overview</h1>
            <span className="text-sm font-bold text-[#2ddbde]">
              {cohort.certified_reps} of {cohort.total_reps} certified
            </span>
          </div>
          <div className="h-1.5 bg-[#31353c] rounded overflow-hidden mb-3">
            <div
              className="h-full bg-[#2ddbde] rounded transition-all duration-500"
              style={{ width: `${certPct}%` }}
            />
          </div>
          <button
            onClick={handleExportCSV}
            className="text-sm text-[#2ddbde] hover:underline"
          >
            Export CSV
          </button>
        </div>

        {/* Rep table */}
        <div className="bg-[#1c2026] rounded-xl overflow-hidden" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
          <table className="w-full text-sm">
            <thead className="bg-[#10141a]" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
              <tr>
                {['Name', 'Sessions', 'Last Active', 'Cert'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cohort.reps.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-[#5f6368]">
                    No reps enrolled yet.
                  </td>
                </tr>
              ) : cohort.reps.map(rep => (
                <tr key={rep.id} className="hover:bg-[#353940] transition-colors" style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                  <td className="px-4 py-3 text-[#e8eaed] font-medium text-sm">{rep.name}</td>
                  <td className="px-4 py-3 text-[#9aa0a6] text-sm">{rep.sessions}</td>
                  <td className="px-4 py-3 text-[#9aa0a6] text-sm">{rep.last_active ?? '—'}</td>
                  <td className="px-4 py-3 text-sm">
                    {rep.certified
                      ? <span className="text-[#1a7a3f] font-bold">✓</span>
                      : <span className="text-[#5f6368]">—</span>
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
