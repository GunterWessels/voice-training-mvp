'use client'
import { Suspense, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { createClient } from '@/lib/supabase'

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

function SessionNewContent() {
  const router = useRouter()
  const params = useSearchParams()
  const seriesId = params.get('series')
  const mode = params.get('mode') ?? 'practice'  // 'practice' | 'demo'

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
        .then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(({ session_id }) => router.replace(`/session/${session_id}?series=${seriesId}&mode=${mode}`))
        .catch(() => router.replace('/dashboard'))
    })
  }, [seriesId, mode, router])

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
