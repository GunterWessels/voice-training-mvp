'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import VoiceChat from '@/components/VoiceChat'
import { Suspense } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

function SessionContent() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const params = useSearchParams()
  const seriesId = params.get('series') ?? undefined
  const [token, setToken] = useState<string | null>(null)

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) { router.replace('/auth/login'); return }
      setToken(session.access_token)
    })
  }, [router])

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f8fafc]">
        <p className="text-sm text-[#718096]">Loading…</p>
      </div>
    )
  }

  return <VoiceChat sessionId={id} token={token} apiBase={API} seriesId={seriesId} />
}

export default function SessionPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-[#f8fafc]">
        <p className="text-sm text-[#718096]">Loading…</p>
      </div>
    }>
      <SessionContent />
    </Suspense>
  )
}
