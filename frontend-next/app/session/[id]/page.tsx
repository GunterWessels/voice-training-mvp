'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import VoiceChat from '@/components/VoiceChat'

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

export default function SessionPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
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

  return <VoiceChat sessionId={id} token={token} apiBase={API} />
}
