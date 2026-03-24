'use client'
import { useState } from 'react'
import { createClient } from '@/lib/supabase'
import CCEHeader from '@/components/CCEHeader'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const supabase = createClient()
    try {
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: `${process.env.NEXT_PUBLIC_SITE_URL ?? location.origin}/auth/callback` },
      })
      if (error) {
        setError(error.message)
      } else {
        setSent(true)
      }
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <CCEHeader />

      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm w-full max-w-sm p-6">
          {!sent ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <h1 className="text-[20px] font-bold text-[#1a202c]">CCE Portal</h1>
                <p className="text-[12px] text-[#718096] mt-1">Sign in to access your training</p>
              </div>

              <div>
                <label htmlFor="email" className="block text-[11px] font-semibold text-[#4a5568] mb-1">
                  Work Email
                </label>
                <input
                  id="email"
                  type="email"
                  aria-label="Work Email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="name@bsci.com"
                  required
                  className="border border-[#e2e8f0] rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#0073CF]/30"
                />
              </div>

              {error && <p className="text-red-600 text-xs">{error}</p>}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#0073CF] text-white rounded-lg py-2.5 text-sm font-semibold disabled:opacity-50"
              >
                {loading ? 'Sending…' : 'Send My Access Link →'}
              </button>

              <p className="text-[10px] text-[#a0aec0] text-center">
                No password needed · Powered by LiquidSMARTS™
              </p>
            </form>
          ) : (
            <div className="flex flex-col items-center text-center gap-3 py-4">
              <div className="w-12 h-12 bg-[#e6f4ea] rounded-full flex items-center justify-center">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <path d="M3 8l9 6 9-6M5 6h14a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2z"
                    stroke="#1a7a3f" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <h2 className="text-[16px] font-bold text-[#1a202c]">Check your inbox</h2>
              <p className="text-[12px] text-[#718096] leading-relaxed">
                We sent a secure link to{' '}
                <strong className="text-[#1a202c]">{email}</strong>
              </p>
              <div className="bg-[#f0f7ff] border border-[#bfdbfe] rounded-lg p-3 text-[11px] text-[#1e40af] leading-relaxed w-full">
                Click the link in your email to sign in. It expires in 1 hour.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
