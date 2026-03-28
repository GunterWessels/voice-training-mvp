'use client'
import { useEffect, useState, useCallback } from 'react'
import { createClient } from '@/lib/supabase'
import CCEHeader from '@/components/CCEHeader'
import AdminUserTable, { AdminUser } from '@/components/AdminUserTable'
import AdminUploadFlow from '@/components/AdminUploadFlow'

type Tab = 'users' | 'sessions' | 'metrics'

interface SessionRow {
  session_id: string
  email: string
  rep_name: string
  scenario_name: string
  score: number
  arc_stage: number
  cof_clinical: boolean
  cof_operational: boolean
  cof_financial: boolean
  cert_issued: boolean
  completed_at: string | null
}

interface LeaderboardRow {
  email: string
  rep_name: string
  sessions: number
  avg_score: number
  certs: number
}

interface Metrics {
  sessions: number
  cost_usd: number
  flagged: number
  cert_rate: number | null
  avg_score: number
  unique_reps: number
  total_sessions: number
  total_certs: number
}

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

function CofBadge({ on, label }: { on: boolean; label: string }) {
  return (
    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
      on ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-400'
    }`}>{label}</span>
  )
}

function ScoreChip({ score }: { score: number }) {
  const color = score >= 80 ? 'text-emerald-600' : score >= 60 ? 'text-amber-500' : 'text-red-500'
  return <span className={`text-[13px] font-bold min-w-[32px] text-right tabular-nums ${color}`}>{score}</span>
}

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>('users')
  const [authToken, setAuthToken] = useState<string>('')

  // Users tab
  const [users, setUsers] = useState<AdminUser[]>([])
  const [usersLoading, setUsersLoading] = useState(false)
  const [usersError, setUsersError] = useState<string | null>(null)

  // Sessions tab
  const [sessions, setSessions] = useState<SessionRow[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(false)

  // Metrics tab
  const [metrics, setMetrics] = useState<Metrics>({
    sessions: 0, cost_usd: 0, flagged: 0, cert_rate: null,
    avg_score: 0, unique_reps: 0, total_sessions: 0, total_certs: 0,
  })
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([])
  const [metricsLoading, setMetricsLoading] = useState(false)

  useEffect(() => {
    createClient().auth.getSession().then(({ data: { session } }) => {
      setAuthToken(session?.access_token ?? '')
    })
  }, [])

  const authHeader = useCallback((): Record<string, string> =>
    authToken ? { Authorization: `Bearer ${authToken}` } : {}
  , [authToken])

  // --- Users ---
  const fetchUsers = useCallback(async () => {
    setUsersLoading(true); setUsersError(null)
    try {
      const res = await fetch(`${API}/api/admin/users`, { headers: authHeader() })
      if (!res.ok) throw new Error(`${res.status}`)
      const json = await res.json()
      setUsers(Array.isArray(json) ? json : json.users ?? [])
    } catch (e) {
      setUsersError(e instanceof Error ? e.message : 'Failed to load users')
    } finally { setUsersLoading(false) }
  }, [authHeader])

  // --- Sessions ---
  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true)
    try {
      const res = await fetch(`${API}/api/admin/sessions`, { headers: authHeader() })
      if (res.ok) setSessions(await res.json())
    } catch { /* silent */ } finally { setSessionsLoading(false) }
  }, [authHeader])

  // --- Metrics ---
  const fetchMetrics = useCallback(async () => {
    setMetricsLoading(true)
    try {
      const res = await fetch(`${API}/api/admin/metrics`, { headers: authHeader() })
      if (res.ok) {
        const d = await res.json()
        setMetrics(d.metrics)
        setLeaderboard(d.leaderboard ?? [])
      }
    } catch { /* silent */ } finally { setMetricsLoading(false) }
  }, [authHeader])

  useEffect(() => {
    if (!authToken) return
    if (activeTab === 'users') fetchUsers()
    if (activeTab === 'sessions') fetchSessions()
    if (activeTab === 'metrics') fetchMetrics()
  }, [activeTab, authToken, fetchUsers, fetchSessions, fetchMetrics])

  async function handleAdd(form: { email: string; first_name: string; last_name: string; role: string }) {
    const res = await fetch(`${API}/api/admin/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify(form),
    })
    if (!res.ok) throw new Error(`Add user failed (${res.status})`)
    await fetchUsers()
  }

  async function handleUpdate(id: string, updates: Partial<AdminUser>) {
    const res = await fetch(`${API}/api/admin/users/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: JSON.stringify(updates),
    })
    if (!res.ok) throw new Error(`Update failed (${res.status})`)
    await fetchUsers()
  }

  async function handleDelete(id: string) {
    const res = await fetch(`${API}/api/admin/users/${id}`, { method: 'DELETE', headers: authHeader() })
    if (!res.ok) throw new Error(`Delete failed (${res.status})`)
    await fetchUsers()
  }

  async function handleInvite(id: string) {
    const res = await fetch(`${API}/api/admin/users/${id}/invite`, { method: 'POST', headers: authHeader() })
    if (!res.ok) throw new Error(`Invite failed (${res.status})`)
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'users', label: 'Users' },
    { key: 'sessions', label: 'Sessions' },
    { key: 'metrics', label: 'Metrics' },
  ]

  return (
    <div className="bg-[#10141a] min-h-screen flex flex-col">
      <CCEHeader />

      <main className="flex-1 p-4 space-y-3 max-w-4xl mx-auto w-full">
        {/* Tab switcher */}
        <div className="flex gap-2">
          {tabs.map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={activeTab === tab.key
                ? 'bg-gradient-to-br from-[#2ddbde] to-[#007e80] text-white text-sm font-semibold px-4 py-2 rounded-lg'
                : 'bg-[#1c2026] text-[#9aa0a6] text-sm font-semibold px-4 py-2 rounded-lg hover:bg-[#353940]'
              }
              style={activeTab !== tab.key ? { border: '1px solid rgba(255,255,255,0.08)' } : undefined}
            >{tab.label}</button>
          ))}
        </div>

        {/* ── Users tab ── */}
        {activeTab === 'users' && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <AdminUploadFlow authHeader={authHeader()} onImportComplete={fetchUsers} />
            </div>
            {usersLoading && <p className="text-sm text-[#9aa0a6] text-center py-4">Loading…</p>}
            {usersError && <p className="text-sm text-red-600 text-center py-4">{usersError}</p>}
            {!usersLoading && (
              <AdminUserTable
                users={users}
                onAdd={handleAdd}
                onUpdate={handleUpdate}
                onDelete={handleDelete}
                onInvite={handleInvite}
              />
            )}
          </div>
        )}

        {/* ── Sessions tab ── */}
        {activeTab === 'sessions' && (
          <div className="space-y-3">
            <div className="bg-[#1c2026] rounded-xl p-4 flex items-center justify-between" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
              <div>
                <h1 className="text-[15px] font-bold text-[#e8eaed]">All Sessions</h1>
                <p className="text-[11px] text-[#9aa0a6] mt-0.5">{sessions.length} records — most recent first</p>
              </div>
              <button onClick={fetchSessions}
                className="text-[11px] text-[#2ddbde] font-semibold hover:underline">
                Refresh
              </button>
            </div>

            {sessionsLoading ? (
              <p className="text-sm text-[#9aa0a6] text-center py-8">Loading…</p>
            ) : sessions.length === 0 ? (
              <div className="bg-[#1c2026] rounded-xl p-8 text-center" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
                <p className="text-[12px] text-[#5f6368]">No sessions yet.</p>
              </div>
            ) : (
              <div className="bg-[#1c2026] rounded-xl divide-y divide-[#31353c]" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
                {/* Header row */}
                <div className="grid grid-cols-[1fr_auto_auto_auto] gap-3 px-4 py-2">
                  <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold">Rep / Scenario</p>
                  <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold">COF</p>
                  <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold text-right">Score</p>
                  <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold text-right">Date</p>
                </div>
                {sessions.map(s => (
                  <div key={s.session_id} className="grid grid-cols-[1fr_auto_auto_auto] gap-3 items-center px-4 py-3 hover:bg-[#353940] transition-colors">
                    <div className="min-w-0">
                      <p className="text-[12px] font-semibold text-[#e8eaed] truncate">{s.rep_name}</p>
                      <p className="text-[10px] text-[#5f6368] truncate">{s.scenario_name} · Stage {s.arc_stage}</p>
                    </div>
                    <div className="flex gap-1">
                      <CofBadge on={s.cof_clinical} label="C" />
                      <CofBadge on={s.cof_operational} label="O" />
                      <CofBadge on={s.cof_financial} label="F" />
                      {s.cert_issued && <span className="text-[11px]" title="Cert">🏅</span>}
                    </div>
                    <ScoreChip score={s.score} />
                    <p className="text-[10px] text-[#5f6368] text-right whitespace-nowrap">
                      {s.completed_at
                        ? new Date(s.completed_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                        : '—'}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Metrics tab ── */}
        {activeTab === 'metrics' && (
          <div className="space-y-3">
            <div className="bg-[#1c2026] rounded-xl p-4 flex items-center justify-between" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
              <div>
                <h1 className="text-[15px] font-bold text-[#e8eaed]">Platform Metrics</h1>
                <p className="text-[11px] text-[#9aa0a6] mt-0.5">Sessions KPI = last 30 days · totals are all-time</p>
              </div>
              <button onClick={fetchMetrics}
                className="text-[11px] text-[#2ddbde] font-semibold hover:underline">
                Refresh
              </button>
            </div>

            {metricsLoading ? (
              <p className="text-sm text-[#9aa0a6] text-center py-8">Loading…</p>
            ) : (
              <>
                {/* KPI grid */}
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { label: 'Sessions (30d)', value: metrics.sessions },
                    { label: 'Avg Score', value: metrics.avg_score || '—' },
                    { label: 'Cert Rate', value: metrics.cert_rate !== null ? `${metrics.cert_rate}%` : '—' },
                    { label: 'Cost (30d)', value: `$${metrics.cost_usd.toFixed(2)}` },
                    { label: 'Total Sessions', value: metrics.total_sessions },
                    { label: 'Total Certs', value: metrics.total_certs },
                    { label: 'Active Reps', value: metrics.unique_reps },
                    { label: 'Flagged', value: metrics.flagged },
                  ].map(k => (
                    <div key={k.label} className="bg-[#1c2026] rounded-xl p-4" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
                      <p className="text-[28px] font-bold text-[#2ddbde]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>{k.value}</p>
                      <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold mt-1">{k.label}</p>
                    </div>
                  ))}
                </div>

                {/* Leaderboard */}
                <div className="bg-[#1c2026] rounded-xl p-4" style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
                  <h2 className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold mb-3">
                    Rep Leaderboard
                  </h2>
                  {leaderboard.length === 0 ? (
                    <p className="text-[12px] text-[#5f6368]">No data yet.</p>
                  ) : (
                    <div className="divide-y divide-[#31353c]">
                      {/* Header */}
                      <div className="grid grid-cols-[1fr_auto_auto_auto] gap-4 pb-2">
                        <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold">Rep</p>
                        <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold text-right">Sessions</p>
                        <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold text-right">Avg</p>
                        <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold text-right">Certs</p>
                      </div>
                      {leaderboard.map((r, i) => (
                        <div key={r.email} className="grid grid-cols-[1fr_auto_auto_auto] gap-4 items-center py-2 hover:bg-[#353940] transition-colors">
                          <div className="min-w-0 flex items-center gap-2">
                            <span className="text-[10px] text-[#5f6368] w-4 text-right flex-shrink-0">{i + 1}</span>
                            <div className="min-w-0">
                              <p className="text-[12px] font-semibold text-[#e8eaed] truncate">{r.rep_name}</p>
                              <p className="text-[10px] text-[#5f6368] truncate">{r.email}</p>
                            </div>
                          </div>
                          <p className="text-[12px] text-[#9aa0a6] text-right">{r.sessions}</p>
                          <ScoreChip score={r.avg_score} />
                          <p className="text-[12px] text-[#9aa0a6] text-right">{r.certs}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
