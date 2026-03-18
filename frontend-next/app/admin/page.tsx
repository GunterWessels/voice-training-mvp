'use client'
import { useEffect, useState, useCallback } from 'react'
import { createClient } from '@/lib/supabase'
import CCEHeader from '@/components/CCEHeader'
import AdminUserTable, { AdminUser } from '@/components/AdminUserTable'
import AdminUploadFlow from '@/components/AdminUploadFlow'

type Tab = 'users' | 'sessions' | 'metrics'

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
  const [activeTab, setActiveTab] = useState<Tab>('users')

  // --- Users tab state ---
  const [users, setUsers] = useState<AdminUser[]>([])
  const [usersLoading, setUsersLoading] = useState(false)
  const [usersError, setUsersError] = useState<string | null>(null)
  const [authToken, setAuthToken] = useState<string>('')

  // --- Metrics tab state ---
  const [data, setData] = useState<AdminData>({
    metrics: { sessions: 0, cost_usd: 0, flagged: 0, cert_rate: null },
    flagged_sessions: [],
  })

  // Resolve auth token once on mount
  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getSession().then(({ data: { session } }) => {
      setAuthToken(session?.access_token ?? '')
    })
  }, [])

  // Fetch users whenever token is available and Users tab is active
  const fetchUsers = useCallback(async (token: string) => {
    setUsersLoading(true)
    setUsersError(null)
    try {
      const headers: Record<string, string> = token
        ? { Authorization: `Bearer ${token}` }
        : {}
      const res = await fetch(`${API}/api/admin/users`, { headers })
      if (!res.ok) throw new Error(`Failed to load users (${res.status})`)
      const json = await res.json()
      setUsers(Array.isArray(json) ? json : json.users ?? [])
    } catch (err) {
      setUsersError(err instanceof Error ? err.message : 'Failed to load users')
    } finally {
      setUsersLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeTab === 'users' && authToken !== undefined) {
      fetchUsers(authToken)
    }
  }, [activeTab, authToken, fetchUsers])

  // Fetch metrics when Metrics tab becomes active
  useEffect(() => {
    if (activeTab !== 'metrics') return
    const supabase = createClient()
    supabase.auth.getSession().then(({ data: { session } }) => {
      const headers: Record<string, string> = session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {}
      fetch(`${API}/api/admin/metrics`, { headers })
        .then(r => (r.ok ? r.json() : null))
        .then(d => { if (d) setData(d) })
        .catch(() => {/* silent */})
    })
  }, [activeTab])

  const authHeader: Record<string, string> = authToken
    ? { Authorization: `Bearer ${authToken}` }
    : {}

  // --- User CRUD handlers ---
  async function handleAdd(form: { email: string; first_name: string; last_name: string; role: string }) {
    const res = await fetch(`${API}/api/admin/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader },
      body: JSON.stringify(form),
    })
    if (!res.ok) throw new Error(`Add user failed (${res.status})`)
    await fetchUsers(authToken)
  }

  async function handleUpdate(id: string, updates: Partial<AdminUser>) {
    const res = await fetch(`${API}/api/admin/users/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeader },
      body: JSON.stringify(updates),
    })
    if (!res.ok) throw new Error(`Update user failed (${res.status})`)
    await fetchUsers(authToken)
  }

  async function handleDelete(id: string) {
    const res = await fetch(`${API}/api/admin/users/${id}`, {
      method: 'DELETE',
      headers: { ...authHeader },
    })
    if (!res.ok) throw new Error(`Delete user failed (${res.status})`)
    await fetchUsers(authToken)
  }

  async function handleInvite(id: string) {
    const res = await fetch(`${API}/api/admin/users/${id}/invite`, {
      method: 'POST',
      headers: { ...authHeader },
    })
    if (!res.ok) throw new Error(`Invite failed (${res.status})`)
  }

  const { metrics, flagged_sessions } = data

  const tabs: { key: Tab; label: string }[] = [
    { key: 'users', label: 'Users' },
    { key: 'sessions', label: 'Sessions' },
    { key: 'metrics', label: 'Metrics' },
  ]

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <CCEHeader />

      <main className="flex-1 p-4 space-y-3 max-w-4xl mx-auto w-full">
        {/* Tab switcher */}
        <div className="flex gap-2">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={
                activeTab === tab.key
                  ? 'bg-[#0073CF] text-white text-sm font-semibold px-4 py-2 rounded-lg'
                  : 'bg-white text-[#4a5568] border border-[#e2e8f0] text-sm font-semibold px-4 py-2 rounded-lg hover:bg-[#f8fafc]'
              }
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Users tab */}
        {activeTab === 'users' && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <AdminUploadFlow
                authHeader={authHeader}
                onImportComplete={() => fetchUsers(authToken)}
              />
            </div>
            {usersLoading && (
              <p className="text-sm text-[#718096] text-center py-4">Loading…</p>
            )}
            {usersError && (
              <p className="text-sm text-red-600 text-center py-4">{usersError}</p>
            )}
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

        {/* Sessions tab */}
        {activeTab === 'sessions' && (
          <div className="text-center py-12 text-[#718096] text-sm">
            Session history coming soon.
          </div>
        )}

        {/* Metrics tab */}
        {activeTab === 'metrics' && (
          <div className="space-y-3">
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
          </div>
        )}
      </main>
    </div>
  )
}
