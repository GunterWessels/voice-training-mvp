'use client'
import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import SessionModeSelector, { type SessionMode } from '@/components/SessionModeSelector'

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

const PERSONAS = [
  { id: 'urologist', name: 'Urologist (Proceduralist)', description: 'High-volume procedural physician focused on clinical outcomes and device performance.' },
  { id: 'urology_nurse', name: 'Urology Nurse / OR Coordinator', description: 'Manages scheduling, device prep, and staff training in the urology OR.' },
  { id: 'hospital_admin', name: 'Hospital Administrator', description: 'Service line owner balancing budget, throughput, and strategic program growth.' },
  { id: 'vac_member', name: 'Value Analysis Committee Member', description: 'Reviews purchase requests through a clinical, operational, and financial lens.' },
  { id: 'asc_director', name: 'ASC Director / Ambulatory Buyer', description: 'Runs an ambulatory surgery center -- cost containment is a primary constraint.' },
  { id: 'cfo', name: 'CFO / Finance Analyst', description: 'Evaluates capital requests through ROI, TCO, and budget cycle alignment.' },
] as const

type PersonaId = typeof PERSONAS[number]['id']

const PERSONA_COLORS: Record<PersonaId, string> = {
  urologist: '#2ddbde',
  urology_nurse: '#34d399',
  hospital_admin: '#818cf8',
  vac_member: '#f59e0b',
  asc_director: '#fb923c',
  cfo: '#e879f9',
}

function PersonaIcon({ id }: { id: PersonaId }) {
  const c = PERSONA_COLORS[id] ?? '#2ddbde'
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8" r="4" stroke={c} strokeWidth="1.5"/>
      <path d="M4 20c0-4.418 3.582-8 8-8s8 3.582 8 8" stroke={c} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}

function StepLabel({ n, active, done }: { n: number; active: boolean; done: boolean }) {
  return (
    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold flex-shrink-0 transition-colors ${
      done ? 'bg-[#2ddbde] text-[#0a1a1a]' : active ? 'bg-[#2ddbde]/20 text-[#2ddbde]' : 'bg-[#31353c] text-[#5f6368]'
    }`}>
      {done ? (
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M2 5l2.5 2.5L8 2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ) : n}
    </div>
  )
}

function SessionNewContent() {
  const router = useRouter()
  const params = useSearchParams()
  const seriesId = params.get('series')

  const [persona, setPersona] = useState<PersonaId | null>(null)
  const [mode, setMode] = useState<SessionMode>('practice')
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) router.replace('/auth/login')
    })
  }, [router])

  function beginSession() {
    if (!persona) return
    setStarting(true)
    setError(null)
    const supabase = createClient()
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!session) { router.replace('/auth/login'); return }
      const endpoint = seriesId
        ? `${API}/api/series/${seriesId}/sessions`
        : `${API}/api/sessions`
      try {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ mode, persona_id: persona }),
        })
        if (!res.ok) {
          const body = await res.text().catch(() => res.status.toString())
          throw new Error(`${res.status}: ${body}`)
        }
        const { session_id } = await res.json()
        router.replace(
          `/session/${session_id}?persona=${persona}&mode=${mode}${seriesId ? `&series=${seriesId}` : ''}`
        )
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Could not start session')
        setStarting(false)
      }
    })
  }

  const selectedPersona = PERSONAS.find(p => p.id === persona)

  return (
    <div className="min-h-screen bg-[#10141a] flex flex-col">
      <div className="bg-[#1c2026] border-b border-white/[0.06] px-4 py-3">
        <div className="max-w-xl mx-auto flex items-center justify-between">
          <span className="text-sm font-semibold text-[#e8eaed]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
            New Session
          </span>
          <a href="/dashboard" className="text-[11px] text-[#9aa0a6] hover:text-[#e8eaed] transition-colors">
            Back
          </a>
        </div>
      </div>

      <main className="flex-1 p-4 max-w-xl mx-auto w-full space-y-4">

        {/* Step 1: Persona */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <StepLabel n={1} active={!persona} done={!!persona} />
            <span className="text-sm font-semibold text-[#e8eaed]">Choose a Persona</span>
          </div>
          <div className="grid grid-cols-2 gap-2.5">
            {PERSONAS.map(p => (
              <button
                key={p.id}
                type="button"
                onClick={() => setPersona(p.id)}
                className={`rounded-lg p-3 text-left transition-all ${
                  persona === p.id
                    ? 'bg-[#1c2026] outline outline-2 outline-[#2ddbde]'
                    : 'bg-[#181c22] hover:bg-[#1c2026]'
                }`}
              >
                <PersonaIcon id={p.id} />
                <p className={`text-[12px] font-semibold mt-2 transition-colors ${
                  persona === p.id ? 'text-[#2ddbde]' : 'text-[#e8eaed]'
                }`}>
                  {p.name}
                </p>
                <p className="text-[10px] text-[#5f6368] mt-0.5 leading-relaxed">{p.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Step 2: Mode */}
        {persona && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <StepLabel n={2} active done={false} />
              <span className="text-sm font-semibold text-[#e8eaed]">Choose Mode</span>
            </div>
            <SessionModeSelector value={mode} onChange={setMode} />
          </div>
        )}

        {/* Step 3: Begin */}
        {persona && (
          <div className="bg-[#1c2026] rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <StepLabel n={3} active done={false} />
              <span className="text-sm font-semibold text-[#e8eaed]">Begin</span>
            </div>
            <p className="text-[12px] text-[#9aa0a6]">
              {`You're ${mode === 'practice' ? 'practicing' : 'certifying'} with `}
              <span className="text-[#e8eaed] font-medium">{selectedPersona?.name}</span>
              {mode === 'certification' && ' using approved content only'}.
            </p>
            {error && (
              <p className="text-[11px] text-red-400 font-mono">{error}</p>
            )}
            <button
              onClick={beginSession}
              disabled={starting}
              className="btn-primary-gradient w-full rounded-lg py-3 text-sm font-semibold disabled:opacity-50 transition-opacity"
            >
              {starting ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 rounded-full border-2 border-[#0a1a1a]/40 border-t-[#0a1a1a] animate-spin" />
                  Starting...
                </span>
              ) : 'Begin Session'}
            </button>
          </div>
        )}
      </main>
    </div>
  )
}

export default function SessionNewPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-[#10141a]">
        <div className="w-8 h-8 rounded-full border-2 border-[#31353c] border-t-[#2ddbde] animate-spin" />
      </div>
    }>
      <SessionNewContent />
    </Suspense>
  )
}
