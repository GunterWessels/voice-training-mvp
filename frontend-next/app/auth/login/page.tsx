'use client'
import { useState } from 'react'
import { createClient } from '@/lib/supabase'
import CCEHeader from '@/components/CCEHeader'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    const supabase = createClient()
    await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    })
    setSent(true)
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#10141a]">
      <CCEHeader />
      <div className="flex-1 flex items-center justify-center px-4">
        <div
          className="bg-[#1c2026] rounded-xl w-full max-w-sm p-6 shadow-[0px_20px_40px_rgba(45,219,222,0.08)]"
          style={{ border: '1px solid rgba(255,255,255,0.08)' }}
        >
          {!sent ? (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div>
                <h1
                  className="text-[18px] font-bold text-[#e8eaed]"
                  style={{ fontFamily: 'var(--font-space-grotesk)' }}
                >
                  CCE Portal
                </h1>
                <p className="text-[12px] text-[#9aa0a6] mt-0.5">
                  Sign in to access your training
                </p>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] text-[#9aa0a6] font-medium">
                  Work Email
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="name@bsci.com"
                  className="bg-[#181c22] rounded-lg px-3 py-2 text-sm text-[#e8eaed] placeholder:text-[#5f6368] focus:border-[#2ddbde] focus:outline-none w-full"
                  style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="btn-primary-gradient rounded-lg py-2.5 text-sm font-semibold w-full disabled:opacity-50"
              >
                {loading ? 'Sending…' : 'Send My Access Link →'}
              </button>
              <p className="text-[10px] text-[#5f6368] text-center">
                No password needed · Powered by LiquidSMARTS™
              </p>
            </form>
          ) : (
            <div className="flex flex-col items-center gap-3 py-2">
              <div
                className="w-12 h-12 rounded-full bg-[#181c22] flex items-center justify-center"
                style={{ border: '1px solid rgba(45,219,222,0.2)' }}
              >
                <svg width="20" height="16" viewBox="0 0 20 16" fill="none">
                  <rect x="0" y="0" width="20" height="16" rx="3" stroke="#2ddbde" strokeWidth="1.5" />
                  <path d="M0 4L10 10L20 4" stroke="#2ddbde" strokeWidth="1.5" />
                </svg>
              </div>
              <div className="text-center">
                <p className="text-[15px] font-bold text-[#e8eaed]">Check your inbox</p>
                <p className="text-[12px] text-[#9aa0a6] mt-0.5">
                  We sent a secure link to{' '}
                  <strong className="text-[#e8eaed]">{email}</strong>
                </p>
              </div>
              <div
                className="w-full rounded-lg p-3 text-[11px] text-[#2ddbde]"
                style={{ background: 'rgba(45,219,222,0.06)', border: '1px solid rgba(45,219,222,0.2)' }}
              >
                Click the link in your email to sign in. It expires in 1 hour.
              </div>
              <p className="text-[10px] text-[#5f6368] text-center">
                No password needed · Powered by LiquidSMARTS™
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
