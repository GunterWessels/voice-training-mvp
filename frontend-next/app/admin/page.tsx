'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'
import CCEHeader from '@/components/CCEHeader'

interface Metrics {
  sessions: number
  cost_usd: number
  flagged: number
  cert_rate: number | null
}

interface FlaggedSession {
  id: string
  user_email: string
  flagged_at: string
  reason: string
}

interface AdminData {
  metrics: Metrics
  flagged_sessions: FlaggedSession[]
}

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

export default function AdminPage() {
  const [data, setData] = useState<AdminData>({
    metrics: { sessions: 0, cost_usd: 0, flagged: 0, cert_rate: null },
    flagged_sessions: [],
  })

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getSession().then(({ data: { session } }) => {
      const headers: Record<string, string> = session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {}

      fetch(`${API}/api/admin/metrics`, { headers })
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setData(d) })
        .catch(() => {/* silent */})
    })
  }, [])

  const { metrics, flagged_sessions } = data

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <CCEHeader />

      <main className="flex-1 p-4 space-y-3 max-w-2xl mx-auto w-full">
        {/* Header */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h1 className="text-[16px] font-bold text-[#1a202c]">Platform Metrics</h1>
          <p className="text-[12px] text-[#718096] mt-0.5">Last 30 days</p>
        </div>

        {/* KPI grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-xl shadow-sm p-4">
            <p className="text-[24px] font-bold text-[#1a202c]">{metrics.sessions}</p>
            <p className="text-[11px] text-[#718096] mt-1">Sessions</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4">
            <p className="text-[24px] font-bold text-[#1a202c]">${metrics.cost_usd.toFixed(2)}</p>
            <p className="text-[11px] text-[#718096] mt-1">Cost (USD)</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4">
            <p className="text-[24px] font-bold text-[#1a202c]">{metrics.flagged}</p>
            <p className="text-[11px] text-[#718096] mt-1">Flagged</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4">
            <p className="text-[24px] font-bold text-[#1a202c]">
              {metrics.cert_rate !== null ? `${metrics.cert_rate}%` : '—'}
            </p>
            <p className="text-[11px] text-[#718096] mt-1">Cert Rate</p>
          </div>
        </div>

        {/* Flagged sessions */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h2 className="text-[11px] font-semibold text-[#718096] uppercase tracking-wide mb-3">
            Flagged Sessions
          </h2>
          {flagged_sessions.length === 0 ? (
            <p className="text-[12px] text-[#a0aec0]">No flagged sessions.</p>
          ) : flagged_sessions.map(s => (
            <div key={s.id} className="border-t border-[#e2e8f0] py-2 first:border-0">
              <p className="text-[12px] text-[#1a202c] font-medium">{s.user_email}</p>
              <p className="text-[11px] text-[#718096]">{s.reason} · {s.flagged_at}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
