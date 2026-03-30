'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import { createClient } from '@/lib/supabase'

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

interface Dimension { id: string; score: number; narrative: string }
interface RagClaim { excerpt: string; source_doc: string; page?: number; approved: boolean }
interface Debrief {
  overall_score: number
  pass: boolean
  session_mode?: 'practice' | 'certification'
  dimensions: Dimension[]
  top_strength: string
  top_improvement: string
  coaching_notes?: Record<string, string>
  rag_claims?: RagClaim[]
  cert_download_url?: string
}

const FRAMEWORK_KEYS = ['cof_coverage', 'spin_questioning', 'argument_coherence', 'challenger_insight']
const FRAMEWORK_LABELS: Record<string, string> = {
  cof_coverage: 'COF',
  spin_questioning: 'SPIN',
  argument_coherence: 'SALES',
  challenger_insight: 'Challenger',
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 80 ? '#34d399' : score >= 60 ? '#f59e0b' : '#ef4444'
  return (
    <div className="w-full h-1.5 bg-[#31353c] rounded-full overflow-hidden mt-2">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${score}%`, background: color }}
      />
    </div>
  )
}

function DebriefContent() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const params = useSearchParams()
  const [debrief, setDebrief] = useState<Debrief | null>(null)
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [claimsOpen, setClaimsOpen] = useState(false)

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!session) { router.replace('/auth/login'); return }
      const headers = { Authorization: `Bearer ${session.access_token}` }
      try {
        const res = await fetch(`${API}/api/sessions/${id}/debrief`, { headers })
        if (!res.ok) throw new Error(`${res.status}`)
        const data = await res.json()
        setDebrief(data)
      } catch (err: unknown) {
        setFetchError(err instanceof Error ? err.message : 'Could not load debrief')
      } finally {
        setLoading(false)
      }
    })
  }, [id, router])

  if (loading) {
    return (
      <div className="min-h-screen bg-[#10141a] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-[#31353c] border-t-[#2ddbde] animate-spin" />
      </div>
    )
  }

  if (fetchError || !debrief) {
    return (
      <div className="min-h-screen bg-[#10141a] flex flex-col items-center justify-center gap-3 p-6">
        <p className="text-sm text-red-400 font-medium">Could not load debrief</p>
        {fetchError && <p className="text-[11px] text-[#5f6368] font-mono">{fetchError}</p>}
        <a href="/dashboard" className="text-sm text-[#2ddbde] hover:underline mt-2">Back to dashboard</a>
      </div>
    )
  }

  const isCertification = debrief.session_mode === 'certification' || params.get('mode') === 'certification'
  const passed = debrief.pass

  const frameworkDims = FRAMEWORK_KEYS
    .map(k => debrief.dimensions.find(d => d.id === k))
    .filter(Boolean) as Dimension[]

  const hasRagClaims = Array.isArray(debrief.rag_claims) && debrief.rag_claims.length > 0

  return (
    <div className="min-h-screen bg-[#10141a] flex flex-col">
      <div className="bg-[#1c2026] border-b border-white/[0.06] px-4 py-3">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <span className="text-sm font-semibold text-[#e8eaed]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
            Session Debrief
          </span>
          <a href="/dashboard" className="text-[11px] text-[#9aa0a6] hover:text-[#e8eaed] transition-colors">
            Dashboard
          </a>
        </div>
      </div>

      <main className="flex-1 p-4 max-w-2xl mx-auto w-full space-y-4">

        {/* Overall Score */}
        <div className="bg-[#1c2026] rounded-lg p-6 text-center">
          <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold mb-2">Overall Score</p>
          <div className="flex items-center justify-center gap-4">
            <span
              className="text-6xl font-bold"
              style={{ fontFamily: 'var(--font-space-grotesk)', color: '#2ddbde' }}
            >
              {debrief.overall_score}
            </span>
            <span className="text-2xl text-[#5f6368]">/100</span>
          </div>
          <div className="mt-3 flex items-center justify-center gap-2">
            {isCertification ? (
              <span
                className="text-[11px] font-bold px-3 py-1 rounded-lg uppercase tracking-wider"
                style={passed
                  ? { background: 'rgba(52,211,153,0.12)', color: '#34d399' }
                  : { background: 'rgba(239,68,68,0.12)', color: '#ef4444' }
                }
              >
                {passed ? 'Pass' : 'Did Not Pass'}
              </span>
            ) : (
              <span
                className="text-[11px] font-bold px-3 py-1 rounded-lg uppercase tracking-wider"
                style={{ background: 'rgba(45,219,222,0.1)', color: '#2ddbde' }}
              >
                Practice
              </span>
            )}
          </div>
        </div>

        {/* Framework Scores */}
        {frameworkDims.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {frameworkDims.map(dim => (
              <div key={dim.id} className="bg-[#1c2026] rounded-lg p-4">
                <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold mb-1">
                  {FRAMEWORK_LABELS[dim.id] ?? dim.id}
                </p>
                <p className={`text-2xl font-bold ${
                  dim.score >= 80 ? 'text-emerald-400' : dim.score >= 60 ? 'text-amber-400' : 'text-red-400'
                }`} style={{ fontFamily: 'var(--font-space-grotesk)' }}>
                  {dim.score}
                </p>
                <ScoreBar score={dim.score} />
              </div>
            ))}
          </div>
        )}

        {/* Strength / Improvement */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[#1c2026] rounded-lg p-4" style={{ border: '1px solid rgba(52,211,153,0.15)' }}>
            <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 mb-1">Top Strength</p>
            <p className="text-[12px] text-[#e8eaed] leading-relaxed">{debrief.top_strength}</p>
          </div>
          <div className="bg-[#1c2026] rounded-lg p-4" style={{ border: '1px solid rgba(251,191,36,0.15)' }}>
            <p className="text-[10px] font-bold uppercase tracking-wider text-amber-400 mb-1">Top Improvement</p>
            <p className="text-[12px] text-[#e8eaed] leading-relaxed">{debrief.top_improvement}</p>
          </div>
        </div>

        {/* Coaching Notes */}
        {debrief.coaching_notes && Object.keys(debrief.coaching_notes).length > 0 && (
          <div className="bg-[#1c2026] rounded-lg p-4 space-y-3">
            <p className="text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold">Coaching Notes</p>
            {Object.entries(debrief.coaching_notes).map(([framework, note]) => (
              <div key={framework} className="pb-3 border-b border-white/[0.06] last:border-0 last:pb-0">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#9aa0a6] mb-1">{framework}</p>
                <p className="text-[12px] text-[#e8eaed] leading-relaxed">{note}</p>
              </div>
            ))}
          </div>
        )}

        {/* Claim Traceability */}
        {hasRagClaims && (
          <div className="bg-[#1c2026] rounded-lg overflow-hidden">
            <button
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-[#353940] transition-colors"
              onClick={() => setClaimsOpen(v => !v)}
            >
              <p className="text-[12px] font-semibold text-[#e8eaed]">Sources Used in This Session</p>
              <svg
                width="16" height="16" viewBox="0 0 16 16" fill="none"
                className="text-[#5f6368] transition-transform"
                style={{ transform: claimsOpen ? 'rotate(180deg)' : undefined }}
              >
                <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            {claimsOpen && (
              <div className="px-4 pb-4">
                <div className="overflow-x-auto">
                  <table className="w-full text-[11px]">
                    <thead>
                      <tr className="border-b border-white/[0.06]">
                        <th className="text-left text-[#5f6368] font-semibold py-2 pr-3">Claim Excerpt</th>
                        <th className="text-left text-[#5f6368] font-semibold py-2 pr-3">Source</th>
                        <th className="text-left text-[#5f6368] font-semibold py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(debrief.rag_claims ?? []).map((claim, i) => (
                        <tr key={i} className="border-b border-white/[0.04] last:border-0">
                          <td className="py-2 pr-3 text-[#9aa0a6] max-w-[200px]">
                            <span className="block truncate" title={claim.excerpt}>{claim.excerpt}</span>
                          </td>
                          <td className="py-2 pr-3 font-mono text-[#9aa0a6] whitespace-nowrap">
                            {claim.source_doc}{claim.page != null ? ` p.${claim.page}` : ''}
                          </td>
                          <td className="py-2">
                            {claim.approved ? (
                              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide"
                                style={{ background: 'rgba(45,219,222,0.1)', color: '#2ddbde' }}>
                                Approved
                              </span>
                            ) : (
                              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide"
                                style={{ background: 'rgba(146,64,14,0.2)', color: '#fbbf24' }}>
                                Unverified
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Cert Download */}
        {isCertification && passed && debrief.cert_download_url && (
          <a
            href={debrief.cert_download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary-gradient block w-full rounded-lg py-3 text-sm font-semibold text-center"
          >
            Download Certificate (PDF)
          </a>
        )}

        <div className="flex flex-col items-center gap-3 pt-2 pb-6">
          <a href="/session/new" className="text-sm text-[#9aa0a6] hover:text-[#2ddbde] transition-colors">
            Start Another Session
          </a>
          <a href="/dashboard" className="text-[11px] text-[#5f6368] hover:text-[#9aa0a6] transition-colors">
            Back to Dashboard
          </a>
        </div>

      </main>
    </div>
  )
}

export default function DebriefPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-[#10141a]">
        <div className="w-8 h-8 rounded-full border-2 border-[#31353c] border-t-[#2ddbde] animate-spin" />
      </div>
    }>
      <DebriefContent />
    </Suspense>
  )
}
