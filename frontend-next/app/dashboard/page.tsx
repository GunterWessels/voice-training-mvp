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
    <div className="bg-[#10141a] min-h-screen flex flex-col">
      <CCEHeader userInitials={initials || undefined} />

      <main className="flex-1 p-4 space-y-3 max-w-lg mx-auto w-full">
        {/* Certification Progress */}
        <div className="bg-[#1c2026] rounded-xl p-4" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold">
              Certification Progress
            </span>
            <span className="text-[11px] font-bold text-[#2ddbde]">
              {completions.certs_earned} / {certsTotal} complete
            </span>
          </div>
          <div className="h-1.5 bg-[#31353c] rounded overflow-hidden">
            <div
              className="h-full bg-[#2ddbde] rounded transition-all duration-500"
              style={{ width: `${certPct}%` }}
            />
          </div>
        </div>

        {/* Scenario card */}
        {scenario && (
          <div
            className="bg-[#1c2026] rounded-xl p-4 shadow-[0px_20px_40px_rgba(45,219,222,0.08)]"
            style={{ border: '1px solid rgba(255,255,255,0.08)', borderLeft: '2px solid #2ddbde' }}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <span className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold">
                  Required
                </span>
                <p className="text-[13px] font-bold text-[#e8eaed] mt-0.5 leading-snug">
                  {scenario.name}
                </p>
                <p className="text-[12px] text-[#5f6368] mt-0.5">
                  {scenario.stage_count} stages · {statusLabel(scenario.status)}
                </p>
              </div>
              <div className="flex flex-col gap-1.5 flex-shrink-0">
                {scenario.status === 'complete' ? (
                  <span className="text-[11px] font-bold text-[#1a7a3f] bg-[#e6f4ea] px-3 py-1.5 rounded-lg text-center">
                    ✓ Complete
                  </span>
                ) : (
                  <a
                    href={`/session/new?series=${scenario.id}`}
                    className="btn-primary-gradient rounded-lg px-4 py-2 text-sm font-semibold whitespace-nowrap text-center"
                  >
                    Practice →
                  </a>
                )}
                <a
                  href={`/session/new?series=${scenario.id}&mode=demo`}
                  className="bg-amber-500 text-white text-[11px] px-3 py-1.5 rounded-lg font-semibold whitespace-nowrap text-center"
                >
                  Demo
                </a>
              </div>
            </div>
          </div>
        )}

        {/* Recent Sessions */}
        <div>
          <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold mb-2">
            Recent Sessions
          </p>
          <div className="bg-[#1c2026] rounded-xl divide-y divide-[#31353c]" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
            {recentSessions.length === 0 ? (
              <p className="text-[12px] text-[#5f6368] text-center py-6">No sessions yet</p>
            ) : (
              recentSessions.map((s) => (
                <div key={s.session_id} className="px-4 py-3 flex items-center justify-between gap-3 hover:bg-[#353940] transition-colors">
                  <div className="min-w-0">
                    <p className="text-[12px] font-semibold text-[#e8eaed] truncate">{s.scenario_name}</p>
                    <p className="text-[10px] text-[#5f6368] mt-0.5">
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
          <div className="bg-[#1c2026] rounded-xl p-3 text-center" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
            <p className="text-[24px] font-bold text-[#e8eaed]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>{completions.sessions_completed}</p>
            <p className="text-[10px] text-[#9aa0a6] mt-0.5">Sessions</p>
          </div>
          <div className="bg-[#1c2026] rounded-xl p-3 text-center" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
            <p className="text-[24px] font-bold text-[#e8eaed]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
              {completions.avg_score > 0 ? completions.avg_score : '—'}
            </p>
            <p className="text-[10px] text-[#9aa0a6] mt-0.5">Avg Score</p>
          </div>
          <div className="bg-[#1c2026] rounded-xl p-3 text-center" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
            <p className="text-[24px] font-bold text-[#e8eaed]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>{completions.certs_earned}</p>
            <p className="text-[10px] text-[#9aa0a6] mt-0.5">Certs</p>
          </div>
        </div>
      </main>
    </div>
  )
}
