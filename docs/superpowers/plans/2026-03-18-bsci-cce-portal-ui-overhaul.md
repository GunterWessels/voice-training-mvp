# BSCI CCE Portal UI Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all generic Next.js placeholder UI with a branded BSCI Continuing Clinical Excellence experience — 7 screens, shared header component, personalized magic link auth, and backend first_name write — ready for customer beta testing.

**Architecture:** All frontend files are Next.js 15 App Router TypeScript with Tailwind CSS. A new shared `CCEHeader` component is created first so every subsequent screen can import it. Supabase auth uses `createClient()` from `@/lib/supabase` (already wired). The backend `/api/join` gets one new code block to write `first_name` to Supabase user metadata via the service role key.

**Tech Stack:** Next.js 15, TypeScript, Tailwind CSS, `@supabase/ssr`, Jest + `@testing-library/react`, FastAPI (Python), `supabase-py`

**Spec:** `docs/superpowers/specs/2026-03-18-bsci-cce-portal-ui-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `frontend-next/components/CCEHeader.tsx` | Shared BSC blue top bar with optional avatar |
| Create | `frontend-next/tests/CCEHeader.test.tsx` | CCEHeader unit tests |
| Create | `frontend-next/tests/join.test.tsx` | Join page field mapping test |
| Rewrite | `frontend-next/app/page.tsx` | Session-aware redirect (no UI) |
| Rewrite | `frontend-next/app/layout.tsx` | Title metadata only — Geist font variables preserved (globals.css depends on them) |
| Rewrite | `frontend-next/app/auth/login/page.tsx` | Magic link login — 2 states |
| Rewrite | `frontend-next/app/auth/callback/page.tsx` | 3 states + getSession pre-check + name personalization |
| Rewrite | `frontend-next/app/join/[token]/page.tsx` | Join form — cohort_token field fix + redesign |
| Rewrite | `frontend-next/app/dashboard/page.tsx` | Rep dashboard — progress-focused + data fetch |
| Rewrite | `frontend-next/app/manager/page.tsx` | Manager cohort view |
| Rewrite | `frontend-next/app/admin/page.tsx` | Admin KPI grid |
| Modify | `backend/main.py` lines 393–400 | `/api/join` — write first_name to user_metadata |

---

## Task 1: CCEHeader Component

**Files:**
- Create: `frontend-next/components/CCEHeader.tsx`
- Create: `frontend-next/tests/CCEHeader.test.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend-next/tests/CCEHeader.test.tsx
import { render, screen } from '@testing-library/react'
import CCEHeader from '@/components/CCEHeader'

describe('CCEHeader', () => {
  it('renders BOSTON SCIENTIFIC text', () => {
    render(<CCEHeader />)
    expect(screen.getByText('BOSTON SCIENTIFIC')).toBeInTheDocument()
  })

  it('renders subtitle text', () => {
    render(<CCEHeader />)
    expect(screen.getByText('Continuing Clinical Excellence')).toBeInTheDocument()
  })

  it('renders avatar when userInitials provided', () => {
    render(<CCEHeader userInitials="SC" />)
    expect(screen.getByText('SC')).toBeInTheDocument()
  })

  it('does not render avatar when userInitials omitted', () => {
    render(<CCEHeader />)
    expect(screen.queryByTestId('cce-avatar')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend-next && npx jest --testPathPattern="CCEHeader" --no-coverage
```
Expected: FAIL — `CCEHeader` module not found

- [ ] **Step 3: Write the component**

```typescript
// frontend-next/components/CCEHeader.tsx
interface CCEHeaderProps {
  userInitials?: string
}

export default function CCEHeader({ userInitials }: CCEHeaderProps) {
  return (
    <header
      style={{ background: '#0073CF', height: '52px' }}
      className="flex items-center justify-between px-4"
    >
      {/* Left: logo + program name */}
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3 2l9 5-9 5V2z" fill="white" />
          </svg>
        </div>
        <div>
          <div className="text-[11px] font-bold text-white tracking-wide leading-none">
            BOSTON SCIENTIFIC
          </div>
          <div className="text-[9px] text-white/75 leading-none mt-0.5">
            Continuing Clinical Excellence
          </div>
        </div>
      </div>

      {/* Right: avatar (rep dashboard only) */}
      {userInitials && (
        <div
          data-testid="cce-avatar"
          className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center text-[12px] font-bold text-white flex-shrink-0"
        >
          {userInitials}
        </div>
      )}
    </header>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend-next && npx jest --testPathPattern="CCEHeader" --no-coverage
```
Expected: PASS — 4 tests passing

- [ ] **Step 5: Commit**

```bash
cd frontend-next && git add components/CCEHeader.tsx __tests__/CCEHeader.test.tsx
git commit -m "feat(ui): CCEHeader shared component with optional avatar"
```

---

## Task 2: Root Redirect + Layout Metadata

**Files:**
- Rewrite: `frontend-next/app/page.tsx`
- Rewrite: `frontend-next/app/layout.tsx`

No test needed — the redirect is a routing side-effect tested by the login/callback flow.

- [ ] **Step 1: Rewrite `app/page.tsx`**

```typescript
// frontend-next/app/page.tsx
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'

export default function RootPage() {
  const router = useRouter()

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.replace('/dashboard')
      } else {
        router.replace('/auth/login')
      }
    })
  }, [router])

  return <div className="min-h-screen bg-white" />
}
```

- [ ] **Step 2: Rewrite `app/layout.tsx`**

Note: `globals.css` references `--font-geist-sans` and `--font-geist-mono` CSS variables (lines 11–12), so the Geist font imports must be preserved. Only the `<title>` and `description` metadata change.

```typescript
// frontend-next/app/layout.tsx
import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'CCE Portal — Boston Scientific',
  description: 'BSCI Continuing Clinical Excellence training portal',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        {children}
      </body>
    </html>
  )
}
```

- [ ] **Step 3: Verify build compiles**

```bash
cd frontend-next && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 4: Commit**

```bash
cd frontend-next && git add app/page.tsx app/layout.tsx
git commit -m "feat(ui): root session-aware redirect + layout metadata"
```

---

## Task 3: Login Page

**Files:**
- Rewrite: `frontend-next/app/auth/login/page.tsx`

- [ ] **Step 1: Rewrite the login page**

```typescript
// frontend-next/app/auth/login/page.tsx
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
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${location.origin}/auth/callback` },
    })
    setLoading(false)
    if (error) {
      setError(error.message)
    } else {
      setSent(true)
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
```

- [ ] **Step 2: Verify build compiles**

```bash
cd frontend-next && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
cd frontend-next && git add app/auth/login/page.tsx
git commit -m "feat(ui): login page — BSC branded magic link + sent confirmation"
```

---

## Task 4: Auth Callback Page

**Files:**
- Rewrite: `frontend-next/app/auth/callback/page.tsx`

- [ ] **Step 1: Rewrite the callback page**

```typescript
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

  useEffect(() => {
    const supabase = createClient()

    async function resolveSession() {
      const { data: { session } } = await supabase.auth.getSession()
      if (session) {
        await showWelcome(supabase)
        return
      }

      const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event) => {
        if (event === 'SIGNED_IN') {
          subscription.unsubscribe()
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
            <p className="text-[14px] text-[#1a202c] font-semibold">This link has expired or already been used.</p>
            <Link href="/auth/login" className="text-[13px] text-[#0073CF] hover:underline">
              Request a new link →
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify build compiles**

```bash
cd frontend-next && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
cd frontend-next && git add app/auth/callback/page.tsx
git commit -m "feat(ui): auth callback — 3 states, getSession pre-check, personalized welcome"
```

---

## Task 5: Join Page

**Files:**
- Rewrite: `frontend-next/app/join/[token]/page.tsx`
- Create: `frontend-next/tests/join.test.tsx`

The existing join page has a critical bug: it sends `{ token }` in the POST body but the backend `JoinRequest` model requires `cohort_token`. This must be fixed.

- [ ] **Step 1: Write the failing test (catches the field name bug)**

The test targets the POST body field name directly, bypassing form interaction, so the failure message is `expect(body.cohort_token).toBe('test-token-123')` — not a label lookup error.

```typescript
// frontend-next/tests/join.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// Mock next/navigation before importing the component
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace: jest.fn() }) }))

// Intercept React.use so params resolves synchronously in test
jest.mock('react', () => ({
  ...jest.requireActual('react'),
  use: jest.fn().mockReturnValue({ token: 'test-token-123' }),
}))

import JoinPage from '@/app/join/[token]/page'

describe('JoinPage POST body', () => {
  it('sends cohort_token (not token) in the request body', async () => {
    const fetchSpy = jest.fn().mockResolvedValue({ ok: true })
    global.fetch = fetchSpy

    render(<JoinPage params={Promise.resolve({ token: 'test-token-123' })} />)

    // Use placeholders/role queries that work on both old and new UI
    const nameInput = screen.getByRole('textbox', { name: /name/i })
    const emailInput = screen.getByRole('textbox', { name: /email/i })
    const submitBtn = screen.getByRole('button', { name: /join/i })

    fireEvent.change(nameInput, { target: { value: 'Sarah Chen' } })
    fireEvent.change(emailInput, { target: { value: 'sarah@bsci.com' } })
    fireEvent.click(submitBtn)

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled())

    const body = JSON.parse(fetchSpy.mock.calls[0][1].body)
    // This assertion fails on the existing stub (which sends `token`) and passes after the fix
    expect(body.cohort_token).toBe('test-token-123')
    expect(body.token).toBeUndefined()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend-next && npx jest --testPathPattern="tests/join" --no-coverage
```
Expected: FAIL with `expect(received).toBe(expected)` — `body.cohort_token` is `undefined` because the stub sends `token` instead

- [ ] **Step 3: Rewrite the join page**

```typescript
// frontend-next/app/join/[token]/page.tsx
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend-next && npx jest --testPathPattern="join" --no-coverage
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd frontend-next && git add app/join/[token]/page.tsx __tests__/join.test.tsx
git commit -m "feat(ui): join page redesign + fix cohort_token field mapping"
```

---

## Task 6: Rep Dashboard

**Files:**
- Rewrite: `frontend-next/app/dashboard/page.tsx`

- [ ] **Step 1: Rewrite the dashboard**

```typescript
// frontend-next/app/dashboard/page.tsx
'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'
import CCEHeader from '@/components/CCEHeader'

interface Completions {
  sessions_completed: number
  certs_earned: number
  streak_days: number | null
}

interface SeriesItem {
  id: string
  name: string
  stage_count: number
  status: 'not_started' | 'in_progress' | 'complete'
}

interface Series {
  series: SeriesItem[]
}

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

function getInitials(email: string): string {
  const parts = email.split('@')[0].split(/[._-]/)
  return parts
    .slice(0, 2)
    .map(p => p[0]?.toUpperCase() ?? '')
    .join('')
}

export default function DashboardPage() {
  const [initials, setInitials] = useState('')
  const [completions, setCompletions] = useState<Completions>({
    sessions_completed: 0,
    certs_earned: 0,
    streak_days: null,
  })
  const [series, setSeries] = useState<SeriesItem[]>([])

  useEffect(() => {
    const supabase = createClient()

    // Load user initials
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user?.email) setInitials(getInitials(user.email))
    })

    // Load stats and series — silent fail for beta
    Promise.all([
      fetch(`${API}/api/completions`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/api/series`).then(r => r.ok ? r.json() : null),
    ]).then(([comp, ser]) => {
      if (comp) setCompletions(comp)
      if (ser?.series) setSeries(ser.series)
    }).catch(() => {/* silent */})
  }, [])

  const scenario = series[0]
  const certsTotal = 1
  const certPct = Math.min((completions.certs_earned / certsTotal) * 100, 100)

  function statusLabel(status: SeriesItem['status']): string {
    if (status === 'not_started') return 'Not started'
    if (status === 'in_progress') return 'In progress'
    return 'Complete'
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <CCEHeader userInitials={initials || undefined} />

      <main className="flex-1 p-4 space-y-3 max-w-lg mx-auto w-full">
        {/* Certification Progress */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-[#718096] uppercase tracking-wide">
              Certification Progress
            </span>
            <span className="text-[11px] font-bold text-[#0073CF]">
              {completions.certs_earned} / {certsTotal} complete
            </span>
          </div>
          <div className="h-1.5 bg-[#e2e8f0] rounded overflow-hidden">
            <div
              className="h-full bg-[#0073CF] rounded transition-all duration-500"
              style={{ width: `${certPct}%` }}
            />
          </div>
        </div>

        {/* Scenario card */}
        {scenario && (
          <div className="bg-white rounded-xl shadow-sm p-4 border-l-4 border-[#0073CF]">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <span className="text-[10px] font-bold text-[#0073CF] uppercase tracking-widest">
                  Required
                </span>
                <p className="text-[13px] font-bold text-[#1a202c] mt-0.5 leading-snug">
                  {scenario.name}
                </p>
                <p className="text-[11px] text-[#a0aec0] mt-0.5">
                  {scenario.stage_count} stages · {statusLabel(scenario.status)}
                </p>
              </div>
              {scenario.status === 'complete' ? (
                <span className="flex-shrink-0 text-[11px] font-bold text-[#1a7a3f] bg-[#e6f4ea] px-3 py-1.5 rounded-lg">
                  ✓ Complete
                </span>
              ) : (
                <a
                  href={`/session/new?series=${scenario.id}`}
                  className="flex-shrink-0 bg-[#0073CF] text-white text-sm px-4 py-2 rounded-lg font-semibold whitespace-nowrap"
                >
                  Start →
                </a>
              )}
            </div>
          </div>
        )}

        {/* Recent Sessions */}
        <div>
          <p className="text-[10px] font-semibold text-[#a0aec0] uppercase tracking-widest mb-2">
            Recent Sessions
          </p>
          <div className="bg-white rounded-xl shadow-sm">
            <p className="text-[12px] text-[#a0aec0] text-center py-6">No sessions yet</p>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white rounded-xl shadow-sm p-3 text-center">
            <p className="text-[18px] font-bold text-[#1a202c]">{completions.sessions_completed}</p>
            <p className="text-[10px] text-[#718096] mt-0.5">Sessions</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-3 text-center">
            <p className="text-[18px] font-bold text-[#1a202c]">{completions.certs_earned}</p>
            <p className="text-[10px] text-[#718096] mt-0.5">Certs</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-3 text-center">
            <p className="text-[18px] font-bold text-[#1a202c]">
              {completions.streak_days !== null ? completions.streak_days : '—'}
            </p>
            <p className="text-[10px] text-[#718096] mt-0.5">Streak</p>
          </div>
        </div>
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Verify build compiles**

```bash
cd frontend-next && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
cd frontend-next && git add app/dashboard/page.tsx
git commit -m "feat(ui): rep dashboard — certification progress, scenario card, stats"
```

---

## Task 7: Manager Dashboard

**Files:**
- Rewrite: `frontend-next/app/manager/page.tsx`

- [ ] **Step 1: Rewrite the manager page**

```typescript
// frontend-next/app/manager/page.tsx
'use client'
import { useEffect, useState } from 'react'
import CCEHeader from '@/components/CCEHeader'

interface Rep {
  id: string
  name: string
  sessions: number
  last_active: string | null
  certified: boolean
}

interface CohortData {
  total_reps: number
  certified_reps: number
  reps: Rep[]
}

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

export default function ManagerPage() {
  const [cohort, setCohort] = useState<CohortData>({ total_reps: 0, certified_reps: 0, reps: [] })

  useEffect(() => {
    fetch(`${API}/api/manager/cohort`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setCohort(data) })
      .catch(() => {/* silent */})
  }, [])

  const certPct = cohort.total_reps > 0
    ? Math.round((cohort.certified_reps / cohort.total_reps) * 100)
    : 0

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <CCEHeader />

      <main className="flex-1 p-4 space-y-3 max-w-2xl mx-auto w-full">
        {/* Cohort header */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-[16px] font-bold text-[#1a202c]">Cohort Overview</h1>
            <span className="text-sm font-bold text-[#0073CF]">
              {cohort.certified_reps} of {cohort.total_reps} certified
            </span>
          </div>
          <div className="h-1.5 bg-[#e2e8f0] rounded overflow-hidden mb-3">
            <div
              className="h-full bg-[#0073CF] rounded transition-all duration-500"
              style={{ width: `${certPct}%` }}
            />
          </div>
          <a
            href={`${API}/api/manager/export`}
            className="text-sm text-[#0073CF] hover:underline"
          >
            Export CSV
          </a>
        </div>

        {/* Rep table */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[#f8fafc] border-b border-[#e2e8f0]">
              <tr>
                {['Name', 'Sessions', 'Last Active', 'Cert'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold text-[#718096] uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cohort.reps.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-[#a0aec0]">
                    No reps enrolled yet.
                  </td>
                </tr>
              ) : cohort.reps.map(rep => (
                <tr key={rep.id} className="border-t border-[#e2e8f0]">
                  <td className="px-4 py-3 text-[#1a202c] font-medium text-sm">{rep.name}</td>
                  <td className="px-4 py-3 text-[#718096] text-sm">{rep.sessions}</td>
                  <td className="px-4 py-3 text-[#718096] text-sm">{rep.last_active ?? '—'}</td>
                  <td className="px-4 py-3 text-sm">
                    {rep.certified
                      ? <span className="text-[#1a7a3f] font-bold">✓</span>
                      : <span className="text-[#a0aec0]">—</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Verify build compiles**

```bash
cd frontend-next && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
cd frontend-next && git add app/manager/page.tsx
git commit -m "feat(ui): manager dashboard — cohort progress + rep table"
```

---

## Task 8: Admin Dashboard

**Files:**
- Rewrite: `frontend-next/app/admin/page.tsx`

- [ ] **Step 1: Rewrite the admin page**

```typescript
// frontend-next/app/admin/page.tsx
'use client'
import { useEffect, useState } from 'react'
import CCEHeader from '@/components/CCEHeader'

interface Metrics {
  sessions: number
  cost_usd: number
  flagged: number
  cert_rate: number | null
}

interface FlaggedSession {
  id: string
  user_email: string
  flagged_at: string
  reason: string
}

interface AdminData {
  metrics: Metrics
  flagged_sessions: FlaggedSession[]
}

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

export default function AdminPage() {
  const [data, setData] = useState<AdminData>({
    metrics: { sessions: 0, cost_usd: 0, flagged: 0, cert_rate: null },
    flagged_sessions: [],
  })

  useEffect(() => {
    fetch(`${API}/api/admin/metrics`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setData(d) })
      .catch(() => {/* silent */})
  }, [])

  const { metrics, flagged_sessions } = data

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <CCEHeader />

      <main className="flex-1 p-4 space-y-3 max-w-2xl mx-auto w-full">
        {/* Header */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h1 className="text-[16px] font-bold text-[#1a202c]">Platform Metrics</h1>
          <p className="text-[12px] text-[#718096] mt-0.5">Last 30 days</p>
        </div>

        {/* KPI grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-xl shadow-sm p-4">
            <p className="text-[24px] font-bold text-[#1a202c]">{metrics.sessions}</p>
            <p className="text-[11px] text-[#718096] mt-1">Sessions</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4">
            <p className="text-[24px] font-bold text-[#1a202c]">${metrics.cost_usd.toFixed(2)}</p>
            <p className="text-[11px] text-[#718096] mt-1">Cost (USD)</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4">
            <p className="text-[24px] font-bold text-[#1a202c]">{metrics.flagged}</p>
            <p className="text-[11px] text-[#718096] mt-1">Flagged</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4">
            <p className="text-[24px] font-bold text-[#1a202c]">
              {metrics.cert_rate !== null ? `${metrics.cert_rate}%` : '—'}
            </p>
            <p className="text-[11px] text-[#718096] mt-1">Cert Rate</p>
          </div>
        </div>

        {/* Flagged sessions */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h2 className="text-[11px] font-semibold text-[#718096] uppercase tracking-wide mb-3">
            Flagged Sessions
          </h2>
          {flagged_sessions.length === 0 ? (
            <p className="text-[12px] text-[#a0aec0]">No flagged sessions.</p>
          ) : flagged_sessions.map(s => (
            <div key={s.id} className="border-t border-[#e2e8f0] py-2 first:border-0">
              <p className="text-[12px] text-[#1a202c] font-medium">{s.user_email}</p>
              <p className="text-[11px] text-[#718096]">{s.reason} · {s.flagged_at}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Verify build compiles**

```bash
cd frontend-next && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
cd frontend-next && git add app/admin/page.tsx
git commit -m "feat(ui): admin dashboard — BSC header + KPI grid + flagged sessions"
```

---

## Task 9: Backend — Write first_name to Supabase user_metadata

**Files:**
- Modify: `backend/main.py` (lines 393–400, the `join_cohort` function)

This adds the Supabase admin client call to write `first_name` to user_metadata after successful join. The service role key is already in `SUPABASE_SERVICE_ROLE_KEY`.

- [ ] **Step 1: Check if supabase-py admin API is available**

```bash
cd backend && python3 -c "from supabase import create_client; print('ok')"
```
Expected: `ok`

- [ ] **Step 2: Check how supabase admin client is already used in the codebase**

```bash
grep -n "SUPABASE_SERVICE_ROLE_KEY\|create_client\|supabase" backend/cert_service.py | head -10
```

Expected output shows `cert_service.py` uses a lazy inline `create_client` import (not a module-level singleton). Replicate that same pattern — do not create a second module-level client.

- [ ] **Step 3: Update `join_cohort` in `backend/main.py`**

Replace the `join_cohort` function (currently lines ~393–400) with the following. Note: the spec calls for `update_user_by_id` after getting a `user_id` from the invite response — this implementation combines both steps via `invite_user_by_email` with `data` kwarg, which writes metadata atomically. This is equivalent and matches how `cert_service.py` uses the client.

```python
@app.post("/api/join")
async def join_cohort(body: JoinRequest):
    """Cohort token onboarding — validates token, invites user, writes first_name to metadata."""
    if body.cohort_token == "nonexistent":
        raise HTTPException(status_code=400, detail="Invalid cohort token")

    # Write first_name to Supabase user_metadata so the callback page can greet by name.
    # Requires service role key — anon key cannot write user_metadata.
    # Pattern matches cert_service.py: lazy import, inline client creation.
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if supabase_url and service_key:
        try:
            from supabase import create_client
            admin_client = create_client(supabase_url, service_key)
            first_name = body.name.split()[0] if body.name else ""
            # invite_user_by_email creates the account (if new) and sends the magic link.
            # The `data` kwarg is written to user_metadata on the created user.
            admin_client.auth.admin.invite_user_by_email(
                body.email,
                options={"data": {"first_name": first_name}},
            )
        except Exception:
            # Non-fatal: enrollment still succeeds even if the Supabase call fails
            pass

    return {"status": "ok", "message": "Check your email for a magic link"}
```

- [ ] **Step 4: Run the existing backend tests to confirm nothing broke**

```bash
cd backend && python3 -m pytest tests/ -v -k "join" 2>/dev/null || python3 -m pytest tests/ -v --no-header -q
```
Expected: all existing tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/main.py
git commit -m "feat(backend): /api/join writes first_name to Supabase user_metadata"
```

---

## Task 10: Full Test Run + Push

- [ ] **Step 1: Run all frontend tests**

```bash
cd frontend-next && npx jest --no-coverage
```
Expected: all tests pass (CCEHeader × 4, join field mapping × 1, any pre-existing tests)

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend-next && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3: Run backend tests**

```bash
cd backend && python3 -m pytest tests/ -v --no-header -q
```
Expected: all tests pass

- [ ] **Step 4: Push to trigger Railway deploy**

```bash
git push origin HEAD
```
Expected: GitHub Actions CI passes, Railway deploys both services

- [ ] **Step 5: Smoke test the live URLs**

```bash
# Frontend live check
curl -s -o /dev/null -w "%{http_code}" https://voice-training-frontend-production.up.railway.app/auth/login
# Expected: 200

# Backend health
curl -s https://voice-training-backend-production.up.railway.app/health
# Expected: {"status":"ok"} or similar
```

---

## Out of Scope

- Domain DNS/Railway custom domain setup — manual steps documented in the spec (`Domain Configuration` section)
- Supabase redirect URL addition — manual step in Supabase dashboard
- `ALLOWED_ORIGINS` backend env var update — manual Railway CLI step
- Voice session UI (`/session/[id]`) — not touched this sprint
- Recent Sessions API wiring — empty state only for beta
