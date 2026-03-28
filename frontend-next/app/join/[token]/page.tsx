'use client'
import { useState, use } from 'react'
import CCEHeader from '@/components/CCEHeader'

interface Props {
  params: Promise<{ token: string }>
}

export default function JoinPage({ params }: Props) {
  const { token } = use(params)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await fetch('/api/join', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // IMPORTANT: backend JoinRequest uses `cohort_token`, not `token`
        body: JSON.stringify({ cohort_token: token, name, email }),
      })
      if (res.ok) {
        setSent(true)
      } else {
        setError('Enrollment failed. Please check your invitation link and try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#10141a]">
      <CCEHeader />

      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div
          className="bg-[#1c2026] rounded-xl w-full max-w-sm p-6 shadow-[0px_20px_40px_rgba(45,219,222,0.08)]"
          style={{ border: '1px solid rgba(255,255,255,0.08)' }}
        >
          {!sent ? (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div>
                <h1
                  className="text-[20px] font-bold text-[#e8eaed]"
                  style={{ fontFamily: 'var(--font-space-grotesk)' }}
                >
                  You&apos;ve been invited
                </h1>
                <p className="text-[12px] text-[#9aa0a6] mt-0.5">Boston Scientific CCE Program</p>
              </div>

              <div className="flex flex-col gap-1.5">
                <label htmlFor="name" className="text-[11px] text-[#9aa0a6] font-medium">
                  Full Name
                </label>
                <input
                  id="name"
                  type="text"
                  aria-label="Full Name"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="Sarah Chen"
                  required
                  className="bg-[#181c22] rounded-lg px-3 py-2 text-sm text-[#e8eaed] placeholder:text-[#5f6368] focus:border-[#2ddbde] focus:outline-none w-full"
                  style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label htmlFor="email" className="text-[11px] text-[#9aa0a6] font-medium">
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
                  className="bg-[#181c22] rounded-lg px-3 py-2 text-sm text-[#e8eaed] placeholder:text-[#5f6368] focus:border-[#2ddbde] focus:outline-none w-full"
                  style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                />
              </div>

              {error && <p className="text-red-500 text-xs">{error}</p>}

              <button
                type="submit"
                disabled={loading}
                className="btn-primary-gradient rounded-lg py-2.5 text-sm font-semibold w-full disabled:opacity-50"
              >
                {loading ? 'Joining…' : 'Join the Program →'}
              </button>

              <p className="text-[10px] text-[#5f6368] text-center">
                No password needed · Powered by LiquidSMARTS™
              </p>
            </form>
          ) : (
            <div className="flex flex-col items-center text-center gap-3 py-4">
              <div
                className="w-12 h-12 rounded-full bg-[#181c22] flex items-center justify-center"
                style={{ border: '1px solid rgba(45,219,222,0.2)' }}
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17l-5-5" stroke="#2ddbde" strokeWidth="2.5"
                    strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div className="text-center">
                <h2 className="text-[16px] font-bold text-[#e8eaed]">Check your email</h2>
                <p className="text-[12px] text-[#9aa0a6] mt-0.5 leading-relaxed">
                  We sent your access link to{' '}
                  <strong className="text-[#e8eaed]">{email}</strong>
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
