'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'
import CCEHeader from '@/components/CCEHeader'

interface Completions {
  sessions_completed: number
  certs_earned: number
  avg_score: number
  streak_days: number | null
  framework_mastery?: {
    cof: number
    spin: number
    sales: number
    challenger: number
  }
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
  session_mode?: 'practice' | 'certification'
  persona?: string
}

interface SeriesItem {
  id: string
  name: string
  stage_count: number
  status: 'not_started' | 'in_progress' | 'complete'
  due_date?: string
  persona?: string
}

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

function getInitials(email: string): string {
  const parts = email.split('@')[0].split(/[._-]/)
  return parts.slice(0, 2).map(p => p[0]?.toUpperCase() ?? '').join('')
}

function DonutRing({ pct, label }: { pct: number; label: string }) {
  const r = 22
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ
  const color = pct >= 80 ? '#2ddbde' : pct >= 60 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex flex-col items-center gap-1.5">
      <svg width="56" height="56" viewBox="0 0 56 56" className="-rotate-90">
        <circle cx="28" cy="28" r={r} fill="none" stroke="#31353c" strokeWidth="5" />
        <circle
          cx="28" cy="28" r={r}
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
        <text
          x="28" y="28"
          textAnchor="middle"
          dominantBaseline="central"
          fill={color}
          fontSize="11"
          fontWeight="700"
          fontFamily="var(--font-space-grotesk)"
          style={{ transform: 'rotate(90deg)', transformOrigin: '28px 28px' }}
        >
          {pct}
        </text>
      </svg>
      <span className="text-[10px] font-semibold uppercase tracking-wider text-[#9aa0a6]">{label}</span>
    </div>
  )
}

function ModeBadge({ mode }: { mode?: 'practice' | 'certification' }) {
  if (mode === 'certification') {
    return (
      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide"
        style={{ background: 'rgba(251,191,36,0.12)', color: '#fbbf24' }}>
        Cert
      </span>
    )
  }
  return (
    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide"
      style={{ background: 'rgba(45,219,222,0.1)', color: '#2ddbde' }}>
      Practice
    </span>
  )
}

export default function DashboardPage() {
  const [initials, setInitials] = useState('')
  const [completions, setCompletions] = useState<Completions>({
    sessions_completed: 0,
    certs_earned: 0,
    avg_score: 0,
    streak_days: null,
    framework_mastery: { cof: 0, spin: 0, sales: 0, challenger: 0 },
  })
  const [series, setSeries] = useState<SeriesItem[]>([])
  const [recentSessions, setRecentSessions] = useState<SessionRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user?.email) setInitials(getInitials(user.email))
    })
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
        if (Array.isArray(sessions)) setRecentSessions(sessions.slice(0, 5))
      }).catch(() => {/* silent */}).finally(() => setLoading(false))
    })
  }, [])

  const assignment = series[0] ?? null
  const mastery = completions.framework_mastery ?? { cof: 0, spin: 0, sales: 0, challenger: 0 }

  return (
    <div className="bg-[#10141a] min-h-screen flex flex-col">
      <CCEHeader userInitials={initials || undefined} />
      <main className="flex-1 p-4 space-y-4 max-w-2xl mx-auto w-full">

        {/* Today's Assignment */}
        {loading ? (
          <div className="bg-[#1c2026] rounded-lg p-6 animate-pulse" style={{ borderLeft: '3px solid #2ddbde' }}>
            <div className="h-3 bg-[#31353c] rounded w-24 mb-3" />
            <div className="h-5 bg-[#31353c] rounded w-48 mb-2" />
            <div className="h-3 bg-[#31353c] rounded w-32" />
          </div>
        ) : assignment ? (
          <div
            className="bg-[#1c2026] rounded-lg p-5 shadow-[0px_20px_40px_rgba(45,219,222,0.08)]"
            style={{ borderLeft: '3px solid #2ddbde' }}
          >
            <p className="text-[10px] uppercase tracking-widest text-[#9aa0a6] font-semibold mb-1">
              {"Today's Assignment"}
            </p>
            <p className="text-lg font-bold text-[#e8eaed] mb-0.5" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
              {assignment.name}
            </p>
            <p className="text-[12px] text-[#5f6368] mb-4">
              {assignment.persona ? `Persona: ${assignment.persona} -- ` : ''}
              {assignment.stage_count} stages
              {assignment.due_date
                ? ` -- Due ${new Date(assignment.due_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`
                : ''}
            </p>
            {assignment.status === 'complete' ? (
              <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-400 bg-emerald-500/10 px-4 py-2 rounded-lg">
                Complete
              </span>
            ) : (
              <a
                href={`/session/new?series=${assignment.id}`}
                className="btn-primary-gradient inline-block rounded-lg px-6 py-2.5 text-sm font-semibold"
              >
                Begin Session
              </a>
            )}
          </div>
        ) : (
          <div className="bg-[#1c2026] rounded-lg p-5" style={{ borderLeft: '3px solid #31353c' }}>
            <p className="text-[10px] uppercase tracking-widest text-[#9aa0a6] font-semibold mb-1">No Assignment</p>
            <p className="text-sm text-[#9aa0a6] mb-4">No assignment scheduled. Practice at your own pace.</p>
            <a
              href="/library"
              className="btn-primary-gradient inline-block rounded-lg px-6 py-2.5 text-sm font-semibold"
            >
              Practice Freely
            </a>
          </div>
        )}

        {/* Framework Mastery Rings */}
        <div className="bg-[#1c2026] rounded-lg p-4">
          <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold mb-4">
            Framework Mastery
          </p>
          <div className="flex justify-around">
            <DonutRing pct={mastery.cof} label="COF" />
            <DonutRing pct={mastery.spin} label="SPIN" />
            <DonutRing pct={mastery.sales} label="SALES" />
            <DonutRing pct={mastery.challenger} label="Challenger" />
          </div>
        </div>

        {/* Recent Sessions */}
        <div>
          <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold mb-2">
            Recent Sessions
          </p>
          <div className="bg-[#1c2026] rounded-lg divide-y divide-[#31353c]/60">
            {loading ? (
              <p className="text-[12px] text-[#5f6368] text-center py-6">Loading</p>
            ) : recentSessions.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <p className="text-sm font-medium text-[#9aa0a6]">No sessions yet</p>
                <p className="text-[12px] text-[#5f6368] mt-1">Complete your first session to see results here.</p>
              </div>
            ) : (
              recentSessions.map((s) => (
                <a
                  key={s.session_id}
                  href={`/session/${s.session_id}/debrief`}
                  className="px-4 py-3 flex items-center justify-between gap-3 hover:bg-[#353940] transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-semibold text-[#e8eaed] truncate">{s.scenario_name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      {s.persona && (
                        <p className="text-[10px] text-[#5f6368] truncate">{s.persona}</p>
                      )}
                      <ModeBadge mode={s.session_mode} />
                    </div>
                  </div>
                  <div className="flex items-center gap-2.5 flex-shrink-0">
                    <span className={`font-mono text-[13px] font-bold ${
                      s.score >= 80 ? 'text-emerald-400' : s.score >= 60 ? 'text-amber-400' : 'text-red-400'
                    }`}>{s.score}</span>
                    {s.cert_issued && (
                      <span title="Certificate earned">
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                          <circle cx="7" cy="7" r="6" stroke="#fbbf24" strokeWidth="1.5"/>
                          <path d="M4.5 7l2 2 3-3" stroke="#fbbf24" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </span>
                    )}
                    <span className="font-mono text-[10px] text-[#5f6368]">
                      {s.completed_at
                        ? new Date(s.completed_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                        : 'In progress'}
                    </span>
                  </div>
                </a>
              ))
            )}
          </div>
        </div>

        {/* Quick Links */}
        <div className="grid grid-cols-2 gap-3">
          <a
            href="/library"
            className="bg-[#1c2026] rounded-lg p-4 hover:bg-[#353940] transition-colors group"
          >
            <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-3"
              style={{ background: 'rgba(45,219,222,0.1)' }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M2 3h5v10H2zM9 3h5v10H9z" stroke="#2ddbde" strokeWidth="1.5" strokeLinejoin="round"/>
              </svg>
            </div>
            <p className="text-sm font-semibold text-[#e8eaed] group-hover:text-[#2ddbde] transition-colors">Browse Library</p>
            <p className="text-[11px] text-[#5f6368] mt-0.5">Scenarios and documents</p>
          </a>
          <a
            href="/session/new"
            className="bg-[#1c2026] rounded-lg p-4 hover:bg-[#353940] transition-colors group"
          >
            <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-3"
              style={{ background: 'rgba(45,219,222,0.1)' }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="6" stroke="#2ddbde" strokeWidth="1.5"/>
                <path d="M6.5 5.5l4 2.5-4 2.5V5.5z" fill="#2ddbde"/>
              </svg>
            </div>
            <p className="text-sm font-semibold text-[#e8eaed] group-hover:text-[#2ddbde] transition-colors">Start Free Practice</p>
            <p className="text-[11px] text-[#5f6368] mt-0.5">No assignment required</p>
          </a>
        </div>

      </main>
    </div>
  )
}
