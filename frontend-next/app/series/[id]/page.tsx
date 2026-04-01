'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import CCEHeader from '@/components/CCEHeader'
import SessionModeSelector, { type SessionMode } from '@/components/SessionModeSelector'

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

interface CofMap {
  product?: string
  clinical_challenge?: string
  operational_consequence?: string
  financial_reality?: string
  solution_bridge?: string
  cof_connection_statement?: string
  quantified_impact?: {
    clinical?: string
    operational?: string
    financial?: string
  }
}

interface GradingDimension {
  id: string
  weight: number
  description: string
}

interface SeriesDetail {
  id: string
  name: string
  description: string
  category: string
  scenario_id: string
  scenario_name: string
  persona_id?: string
  cof_map: CofMap
  grading_criteria: { dimensions: GradingDimension[] }
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-[#1c2026] border border-white/[0.06] rounded-xl p-5">
      <h2 className="text-[11px] font-semibold text-[#2ddbde] uppercase tracking-widest mb-4">
        {title}
      </h2>
      {children}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] text-[#5f6368] uppercase tracking-wide">{label}</span>
      <span className="text-[13px] text-[#e8eaed] font-medium">{value}</span>
    </div>
  )
}

export default function SeriesDetailPage() {
  const router = useRouter()
  const params = useParams()
  const seriesId = params.id as string

  const [detail, setDetail] = useState<SeriesDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<SessionMode>('practice')
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!session) { router.replace('/auth/login'); return }
      try {
        const res = await fetch(`${API}/api/series/${seriesId}`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        setDetail(data)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load')
      } finally {
        setLoading(false)
      }
    })
  }, [router, seriesId])

  async function beginSession() {
    if (!detail) return
    setStarting(true)
    setStartError(null)
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) { router.replace('/auth/login'); return }
    try {
      const res = await fetch(`${API}/api/series/${seriesId}/sessions`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mode, persona_id: detail.persona_id ?? null }),
      })
      if (!res.ok) {
        const body = await res.text().catch(() => res.status.toString())
        throw new Error(`${res.status}: ${body}`)
      }
      const { session_id, persona_id: resolvedPersona } = await res.json()
      router.replace(
        `/session/${session_id}?persona=${resolvedPersona}&mode=${mode}&series=${seriesId}`
      )
    } catch (err: unknown) {
      setStartError(err instanceof Error ? err.message : 'Could not start session')
      setStarting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#10141a] flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-[#2ddbde]/30 border-t-[#2ddbde] rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="min-h-screen bg-[#10141a] flex items-center justify-center">
        <p className="text-[#9aa0a6] text-sm">{error ?? 'Series not found'}</p>
      </div>
    )
  }

  const cof = detail.cof_map ?? {}
  const qi = cof.quantified_impact ?? {}
  const dims = detail.grading_criteria?.dimensions ?? []

  return (
    <div className="min-h-screen bg-[#10141a] flex flex-col">
      <CCEHeader />

      <main className="flex-1 p-4 max-w-2xl mx-auto w-full space-y-4 pb-10">

        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <button
              onClick={() => router.back()}
              className="text-[11px] text-[#5f6368] hover:text-[#9aa0a6] transition-colors"
            >
              ← Back
            </button>
          </div>
          <h1
            className="text-xl font-bold text-[#e8eaed] leading-tight"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            {detail.name}
          </h1>
          {detail.description && (
            <p className="text-[13px] text-[#9aa0a6] mt-1 leading-relaxed">
              {detail.description}
            </p>
          )}
        </div>

        {/* What this conversation is about */}
        {(cof.clinical_challenge || cof.solution_bridge) && (
          <Section title="What This Conversation Is About">
            {cof.clinical_challenge && (
              <div className="mb-3">
                <p className="text-[11px] text-[#5f6368] uppercase tracking-wide mb-1">The Problem</p>
                <p className="text-[13px] text-[#e8eaed] leading-relaxed">{cof.clinical_challenge}</p>
              </div>
            )}
            {cof.solution_bridge && (
              <div className="mb-3">
                <p className="text-[11px] text-[#5f6368] uppercase tracking-wide mb-1">The Bridge</p>
                <p className="text-[13px] text-[#e8eaed] leading-relaxed">{cof.solution_bridge}</p>
              </div>
            )}
            {cof.cof_connection_statement && (
              <div className="bg-[#2ddbde]/5 border border-[#2ddbde]/20 rounded-lg p-3">
                <p className="text-[12px] text-[#2ddbde] italic leading-relaxed">
                  &ldquo;{cof.cof_connection_statement}&rdquo;
                </p>
              </div>
            )}
          </Section>
        )}

        {/* Key numbers */}
        {(qi.clinical || qi.operational || qi.financial) && (
          <Section title="Key Numbers to Know">
            <div className="space-y-3">
              {qi.clinical && <Stat label="Clinical" value={qi.clinical} />}
              {qi.operational && <Stat label="Operational" value={qi.operational} />}
              {qi.financial && <Stat label="Financial" value={qi.financial} />}
            </div>
          </Section>
        )}

        {/* COF frame */}
        {(cof.operational_consequence || cof.financial_reality) && (
          <Section title="COF Frame">
            <div className="space-y-3">
              {cof.operational_consequence && (
                <Stat label="Operational Consequence" value={cof.operational_consequence} />
              )}
              {cof.financial_reality && (
                <Stat label="Financial Reality" value={cof.financial_reality} />
              )}
            </div>
          </Section>
        )}

        {/* What you are graded on */}
        {dims.length > 0 && (
          <Section title="What You Are Graded On">
            <div className="space-y-2">
              {dims.map(d => (
                <div key={d.id} className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-10 text-right">
                    <span className="text-[11px] font-semibold text-[#2ddbde]">
                      {Math.round(d.weight * 100)}%
                    </span>
                  </div>
                  <p className="text-[12px] text-[#9aa0a6] leading-relaxed">{d.description}</p>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Mode selector + Begin */}
        <div className="space-y-4 pt-2">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold mb-3">
              Session Mode
            </p>
            <SessionModeSelector value={mode} onChange={setMode} />
          </div>
          {startError && (
            <p className="text-[11px] text-red-400 font-mono">{startError}</p>
          )}
          <button
            onClick={beginSession}
            disabled={starting}
            className="w-full py-4 rounded-xl font-semibold text-[#0a1a1a] text-[15px] transition-all disabled:opacity-50"
            style={{
              background: mode === 'certification'
                ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
                : 'linear-gradient(135deg, #2ddbde 0%, #1bb8bc 100%)',
              fontFamily: 'var(--font-space-grotesk)',
            }}
          >
            {starting ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 rounded-full border-2 border-[#0a1a1a]/30 border-t-[#0a1a1a] animate-spin" />
                Starting...
              </span>
            ) : mode === 'certification' ? 'Begin Certification' : 'Begin Practice'}
          </button>
        </div>

      </main>
    </div>
  )
}
