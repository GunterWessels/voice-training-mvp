'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'
import CCEHeader from '@/components/CCEHeader'

interface Completions {
  sessions_completed: number
  certs_earned: number
  avg_score: number
  streak_days: number | null
}

interface SessionRecord {
  session_id: string
  scenario_name: string
  score: number
  arc_stage: number
  cof_clinical: boolean
  cof_operational: boolean
  cof_financial: boolean
  cert_issued: boolean
  completed_at: string | null
}

interface SeriesItem {
  id: string
  name: string
  stage_count: number
  status: 'not_started' | 'in_progress' | 'complete'
}

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

function getInitials(email: string): string {
  const parts = email.split('@')[0].split(/[._-]/)
  return parts
    .slice(0, 2)
    .map(p => p[0]?.toUpperCase() ?? '')
    .join('')
}

export default function DashboardPage() {
  const [initials, setInitials] = useState('')
  const [completions, setCompletions] = useState<Completions>({
    sessions_completed: 0,
    certs_earned: 0,
    avg_score: 0,
    streak_days: null,
  })
  const [series, setSeries] = useState<SeriesItem[]>([])
  const [recentSessions, setRecentSessions] = useState<SessionRecord[]>([])

  useEffect(() => {
    const supabase = createClient()

    // Load user initials
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user?.email) setInitials(getInitials(user.email))
    })

    // Load stats and series — silent fail for beta
    supabase.auth.getSession().then(({ data: { session } }) => {
      const headers: Record<string, string> = session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {}

      Promise.all([
        fetch(`${API}/api/completions`, { headers }).then(r => r.ok ? r.json() : null),
        fetch(`${API}/api/series`, { headers }).then(r => r.ok ? r.json() : null),
        fetch(`${API}/api/sessions`, { headers }).then(r => r.ok ? r.json() : null),
      ]).then(([comp, ser, sessions]) => {
        if (comp) setCompletions(comp)
        if (ser?.series) setSeries(ser.series)
        if (Array.isArray(sessions)) setRecentSessions(sessions)
      }).catch(() => {/* silent */})
    })
  }, [])

  const scenario = series[0]
  const certsTotal = 1
  const certPct = Math.min((completions.certs_earned / certsTotal) * 100, 100)

  function statusLabel(status: SeriesItem['status']): string {
    if (status === 'not_started') return 'Not started'
    if (status === 'in_progress') return 'In progress'
    return 'Complete'
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <CCEHeader userInitials={initials || undefined} />

      <main className="flex-1 p-4 space-y-3 max-w-lg mx-auto w-full">
        {/* Certification Progress */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-[#718096] uppercase tracking-wide">
              Certification Progress
            </span>
            <span className="text-[11px] font-bold text-[#0073CF]">
              {completions.certs_earned} / {certsTotal} complete
            </span>
          </div>
          <div className="h-1.5 bg-[#e2e8f0] rounded overflow-hidden">
            <div
              className="h-full bg-[#0073CF] rounded transition-all duration-500"
              style={{ width: `${certPct}%` }}
            />
          </div>
        </div>

        {/* Scenario card */}
        {scenario && (
          <div className="bg-white rounded-xl shadow-sm p-4 border-l-4 border-[#0073CF]">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <span className="text-[10px] font-bold text-[#0073CF] uppercase tracking-widest">
                  Required
                </span>
                <p className="text-[13px] font-bold text-[#1a202c] mt-0.5 leading-snug">
                  {scenario.name}
                </p>
                <p className="text-[11px] text-[#a0aec0] mt-0.5">
                  {scenario.stage_count} stages · {statusLabel(scenario.status)}
                </p>
              </div>
              {scenario.status === 'complete' ? (
                <span className="flex-shrink-0 text-[11px] font-bold text-[#1a7a3f] bg-[#e6f4ea] px-3 py-1.5 rounded-lg">
                  ✓ Complete
                </span>
              ) : (
                <a
                  href={`/session/new?series=${scenario.id}`}
                  className="flex-shrink-0 bg-[#0073CF] text-white text-sm px-4 py-2 rounded-lg font-semibold whitespace-nowrap"
                >
                  Start →
                </a>
              )}
            </div>
          </div>
        )}

        {/* Recent Sessions */}
        <div>
          <p className="text-[10px] font-semibold text-[#a0aec0] uppercase tracking-widest mb-2">
            Recent Sessions
          </p>
          <div className="bg-white rounded-xl shadow-sm divide-y divide-[#f0f4f8]">
            {recentSessions.length === 0 ? (
              <p className="text-[12px] text-[#a0aec0] text-center py-6">No sessions yet</p>
            ) : (
              recentSessions.map((s) => (
                <div key={s.session_id} className="px-4 py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[12px] font-semibold text-[#1a202c] truncate">{s.scenario_name}</p>
                    <p className="text-[10px] text-[#a0aec0] mt-0.5">
                      Stage {s.arc_stage} ·{' '}
                      {s.completed_at
                        ? new Date(s.completed_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                        : 'In progress'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {/* COF flags */}
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${s.cof_clinical ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-400'}`}>C</span>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${s.cof_operational ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-400'}`}>O</span>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${s.cof_financial ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-400'}`}>F</span>
                    {/* Score */}
                    <span className={`text-[13px] font-bold min-w-[36px] text-right ${
                      s.score >= 80 ? 'text-emerald-600' : s.score >= 60 ? 'text-amber-500' : 'text-red-500'
                    }`}>{s.score}</span>
                    {s.cert_issued && <span className="text-[11px]" title="Certificate earned">🏅</span>}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white rounded-xl shadow-sm p-3 text-center">
            <p className="text-[18px] font-bold text-[#1a202c]">{completions.sessions_completed}</p>
            <p className="text-[10px] text-[#718096] mt-0.5">Sessions</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-3 text-center">
            <p className="text-[18px] font-bold text-[#1a202c]">
              {completions.avg_score > 0 ? completions.avg_score : '—'}
            </p>
            <p className="text-[10px] text-[#718096] mt-0.5">Avg Score</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-3 text-center">
            <p className="text-[18px] font-bold text-[#1a202c]">{completions.certs_earned}</p>
            <p className="text-[10px] text-[#718096] mt-0.5">Certs</p>
          </div>
        </div>
      </main>
    </div>
  )
}
