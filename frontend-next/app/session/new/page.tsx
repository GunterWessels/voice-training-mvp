'use client'
import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { createClient } from '@/lib/supabase'

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

function SessionNewContent() {
  const router = useRouter()
  const params = useSearchParams()
  const seriesId = params.get('series')
  const mode = params.get('mode') ?? 'practice'
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!seriesId) { router.replace('/dashboard'); return }

    const supabase = createClient()
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) { router.replace('/auth/login'); return }

      fetch(`${API}/api/series/${seriesId}/sessions`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      })
        .then(async r => {
          if (!r.ok) {
            const body = await r.text().catch(() => r.status.toString())
            throw new Error(`${r.status}: ${body}`)
          }
          return r.json()
        })
        .then(({ session_id }) => router.replace(`/session/${session_id}?series=${seriesId}&mode=${mode}`))
        .catch((err: Error) => setError(err.message))
    })
  }, [seriesId, mode, router])

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#f8fafc] gap-3">
        <p className="text-sm text-red-600 font-medium">Could not start session</p>
        <p className="text-xs text-[#718096] font-mono max-w-sm text-center">{error}</p>
        <a href="/dashboard" className="text-xs text-[#0073CF] hover:underline mt-2">← Back to dashboard</a>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f8fafc]">
      <p className="text-sm text-[#718096]">Starting session…</p>
    </div>
  )
}

export default function SessionNewPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-[#f8fafc]">
        <p className="text-sm text-[#718096]">Loading…</p>
      </div>
    }>
      <SessionNewContent />
    </Suspense>
  )
}
