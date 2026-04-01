'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'

export default function RootPage() {
  const router = useRouter()

  useEffect(() => {
    // Magic links redirect to the root domain with the token in the hash.
    // Forward to /auth/callback so the session exchange is handled correctly.
    if (typeof window !== 'undefined' && window.location.hash.includes('access_token')) {
      router.replace('/auth/callback' + window.location.hash)
      return
    }
    const supabase = createClient()
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.replace('/dashboard')
      } else {
        router.replace('/auth/login')
      }
    })
  }, [router])

  return <div className="min-h-screen bg-[#10141a]" />
}
