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
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <CCEHeader />

      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm w-full max-w-sm p-6">
          {!sent ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <h1 className="text-[20px] font-bold text-[#1a202c]">You&apos;ve been invited</h1>
                <p className="text-[12px] text-[#718096] mt-1">Boston Scientific CCE Program</p>
              </div>

              <div>
                <label htmlFor="name" className="block text-[11px] font-semibold text-[#4a5568] mb-1">
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
                  className="border border-[#e2e8f0] rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-[#0073CF]/30"
                />
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
                {loading ? 'Joining…' : 'Join the Program →'}
              </button>

              <p className="text-[10px] text-[#a0aec0] text-center">
                No password needed · Powered by LiquidSMARTS™
              </p>
            </form>
          ) : (
            <div className="flex flex-col items-center text-center gap-3 py-4">
              <div className="w-12 h-12 bg-[#e6f4ea] rounded-full flex items-center justify-center">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17l-5-5" stroke="#1a7a3f" strokeWidth="2.5"
                    strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <h2 className="text-[16px] font-bold text-[#1a202c]">Check your email</h2>
              <p className="text-[12px] text-[#718096] leading-relaxed">
                We sent your access link to{' '}
                <strong className="text-[#1a202c]">{email}</strong>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
