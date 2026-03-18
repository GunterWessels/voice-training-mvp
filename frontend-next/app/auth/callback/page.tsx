// frontend-next/app/auth/callback/page.tsx
'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'
import CCEHeader from '@/components/CCEHeader'

type State = 'verifying' | 'welcome' | 'error'

export default function CallbackPage() {
  const router = useRouter()
  const [state, setState] = useState<State>('verifying')
  const [firstName, setFirstName] = useState('')
  const [animating, setAnimating] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    const supabase = createClient()

    async function resolveSession() {
      const { data: { session } } = await supabase.auth.getSession()
      if (session) {
        await showWelcome(supabase)
        return
      }

      const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event: string) => {
        if (event === 'SIGNED_IN') {
          subscription.unsubscribe()
          // Check allowlist
          const { data: { session } } = await supabase.auth.getSession()
          if (session) {
            const API = process.env.NEXT_PUBLIC_API_URL ?? ''
            try {
              const checkRes = await fetch(`${API}/api/auth/check`, {
                headers: { Authorization: `Bearer ${session.access_token}` },
              })
              if (!checkRes.ok) {
                await supabase.auth.signOut()
                setErrorMsg('Your email is not on the access list. Contact your program administrator.')
                setState('error')
                return
              }
            } catch {
              // Network error — fail open so infra issues don't lock users out
            }
          }
          await showWelcome(supabase)
        } else if (event === 'SIGNED_OUT') {
          setState('error')
        }
      })
    }

    async function showWelcome(supabase: ReturnType<typeof createClient>) {
      const { data: { user } } = await supabase.auth.getUser()
      const name = user?.user_metadata?.first_name
        ?? user?.email?.split('@')[0]
        ?? 'there'
      setFirstName(name)
      setState('welcome')
      // setTimeout ensures the initial w-0 render commits before the transition fires
      setTimeout(() => setAnimating(true), 0)
      setTimeout(() => router.replace('/dashboard'), 2000)
    }

    resolveSession()
  }, [router])

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <CCEHeader />

      <div className="flex-1 flex items-center justify-center px-4">
        {state === 'verifying' && (
          <div className="flex flex-col items-center gap-3">
            <div className="border-4 border-[#e2e8f0] border-t-[#0073CF] rounded-full w-8 h-8 animate-spin" />
            <p className="text-[12px] text-[#a0aec0]">Verifying your link…</p>
          </div>
        )}

        {state === 'welcome' && (
          <div className="flex flex-col items-center text-center gap-3 w-full max-w-xs">
            <div
              className="w-[52px] h-[52px] bg-[#0073CF] rounded-full flex items-center justify-center"
              style={{ boxShadow: '0 0 0 6px rgba(0,115,207,0.12)' }}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M20 6L9 17l-5-5" stroke="white" strokeWidth="2.5"
                  strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-[18px] font-extrabold text-[#1a202c]">Welcome, {firstName}.</p>
              <p className="text-[12px] text-[#718096] mt-1">You&apos;re in the right place.</p>
            </div>
            <p className="text-[11px] text-[#a0aec0]">Taking you to your dashboard…</p>
            <div className="w-full h-[3px] bg-[#e2e8f0] rounded overflow-hidden">
              <div
                className={`h-full bg-[#0073CF] rounded transition-all ease-linear duration-[2000ms] ${animating ? 'w-full' : 'w-0'}`}
              />
            </div>
          </div>
        )}

        {state === 'error' && (
          <div className="flex flex-col items-center text-center gap-3">
            <p className="text-[14px] text-[#1a202c] font-semibold">
              {errorMsg || 'This link has expired or already been used.'}
            </p>
            <Link href="/auth/login" className="text-[13px] text-[#0073CF] hover:underline">
              Request a new link →
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
