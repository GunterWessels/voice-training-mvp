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
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#10141a] gap-3">
        <p className="text-sm text-red-500 font-medium">Could not start session</p>
        <p className="text-xs text-[#9aa0a6] font-mono max-w-sm text-center">{error}</p>
        <a href="/dashboard" className="text-xs text-[#2ddbde] hover:underline mt-2">← Back to dashboard</a>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#10141a]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-[#31353c] border-t-[#2ddbde] animate-spin" />
        <p className="text-sm text-[#9aa0a6]">Starting session…</p>
      </div>
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
