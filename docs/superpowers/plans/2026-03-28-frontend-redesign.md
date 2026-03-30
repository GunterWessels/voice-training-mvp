# Frontend Redesign: Clinical Command Center Design System

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the BSC blue (#0073CF) light-mode design system in `frontend-next/` with the Stitch "Clinical Command Center" dark design system — dark surfaces, bioluminescent teal, Space Grotesk + Inter typography, glassmorphism overlays, and PTT button upgrade — across all screens and components.

**Architecture:** All changes are cosmetic (CSS variables, Tailwind classes, font declarations). No business logic, no API contracts, no component props change. Work screen-by-screen: global setup first, then shared components, then pages, then the voice session. Each task produces a visually correct, testable screen. The existing `CCEHeader`, `VoiceChat`, `ArcProgress`, `CofGates`, `RepHint`, and `GradingDebrief` components are restyled — not rewritten.

**Tech Stack:** Next.js 15 App Router, TypeScript, Tailwind CSS 4, `next/font` (Google Fonts — Space Grotesk + Inter)

---

## Design Token Reference (use these everywhere)

```
Background (base):        #10141a   → bg-[#10141a]
Surface:                  #1c2026   → bg-[#1c2026]
Surface low:              #181c22   → bg-[#181c22]
Surface highest:          #31353c   → bg-[#31353c]
Surface bright (hover):   #353940   → bg-[#353940]

Primary (teal):           #2ddbde   → text-[#2ddbde] / border-[#2ddbde]
Primary container:        #007e80
Primary gradient:         linear-gradient(135deg, #2ddbde, #007e80)  → bg-gradient-to-br from-[#2ddbde] to-[#007e80]

On-primary (text on teal): #0a1a1a
Text primary:             #e8eaed   → text-[#e8eaed]
Text secondary:           #9aa0a6   → text-[#9aa0a6]
Text muted:               #5f6368   → text-[#5f6368]

Outline variant (ghost border): rgba(255,255,255,0.08)
Cyan glow shadow:         0px 20px 40px rgba(45, 219, 222, 0.08)
PTT active glow:          0 0 0 12px rgba(45,219,222,0.15), 0 0 0 24px rgba(45,219,222,0.06)

Fonts:
  Display/Headlines:      Space Grotesk (weights 400, 500, 700)
  Body/UI:                Inter (weights 400, 500, 600)
  Monospace (data/IDs):   system-ui monospace, label-sm treatment
```

---

## File Map

| Action | File | Change |
|--------|------|--------|
| Modify | `frontend-next/app/globals.css` | CSS variables, font declarations, body defaults |
| Modify | `frontend-next/app/layout.tsx` | Replace Geist fonts with Space Grotesk + Inter via next/font |
| Modify | `frontend-next/components/CCEHeader.tsx` | Dark console header — teal accent, monospace label |
| Modify | `frontend-next/app/auth/login/page.tsx` | Dark card, teal CTA |
| Modify | `frontend-next/app/auth/callback/page.tsx` | Dark overlay, teal progress bar |
| Modify | `frontend-next/app/join/[token]/page.tsx` | Dark card, teal CTA |
| Modify | `frontend-next/app/dashboard/page.tsx` | Dark surfaces, teal progress, scenario cards |
| Modify | `frontend-next/app/manager/page.tsx` | Dark table, teal accents |
| Modify | `frontend-next/app/admin/page.tsx` | Dark KPI grid |
| Modify | `frontend-next/components/ArcProgress.tsx` | Dark dots, teal active dot |
| Modify | `frontend-next/components/CofGates.tsx` | Dark gate cards, teal pass state |
| Modify | `frontend-next/components/RepHint.tsx` | Glassmorphism hint overlay |
| Modify | `frontend-next/app/session/[id]/page.tsx` | Dark loading screen |
| Modify | `frontend-next/components/VoiceChat.tsx` | PTT button gradient + pulse glow, dark layout |

---

## Task 1: Global setup — CSS variables, fonts, body

**Files:**
- Modify: `frontend-next/app/globals.css`
- Modify: `frontend-next/app/layout.tsx`

- [ ] **Step 1: Replace `globals.css` with Clinical Command Center tokens**

```css
/* frontend-next/app/globals.css */
@import "tailwindcss";

:root {
  /* Surfaces */
  --background:                #10141a;
  --surface:                   #1c2026;
  --surface-low:               #181c22;
  --surface-highest:           #31353c;
  --surface-bright:            #353940;

  /* Primary */
  --primary:                   #2ddbde;
  --primary-container:         #007e80;
  --on-primary:                #0a1a1a;

  /* Text */
  --text-primary:              #e8eaed;
  --text-secondary:            #9aa0a6;
  --text-muted:                #5f6368;

  /* Borders */
  --outline-variant:           rgba(255, 255, 255, 0.08);

  /* Shadows */
  --cyan-glow:                 0px 20px 40px rgba(45, 219, 222, 0.08);
  --ptt-active-glow:           0 0 0 12px rgba(45,219,222,0.15), 0 0 0 24px rgba(45,219,222,0.06);
}

body {
  background-color: var(--background);
  color: var(--text-primary);
  font-family: var(--font-inter), system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  overscroll-behavior: none;
}

/* Utility: gradient primary button */
.btn-primary-gradient {
  background: linear-gradient(135deg, #2ddbde, #007e80);
  color: #0a1a1a;
  font-weight: 600;
}

/* Utility: ghost border */
.ghost-border {
  border: 1px solid rgba(255, 255, 255, 0.08);
}

/* Utility: glassmorphism overlay */
.glass {
  background: rgba(28, 32, 38, 0.8);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
```

- [ ] **Step 2: Update `layout.tsx` — swap Geist for Space Grotesk + Inter**

```typescript
// frontend-next/app/layout.tsx
import type { Metadata } from 'next'
import { Space_Grotesk, Inter } from 'next/font/google'
import './globals.css'

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  variable: '--font-space-grotesk',
  display: 'swap',
})

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-inter',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'CCE Voice Platform',
  description: 'Boston Scientific Continuing Clinical Excellence',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${inter.variable}`}>
      <body>{children}</body>
    </html>
  )
}
```

- [ ] **Step 3: Verify build compiles**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next
npx tsc --noEmit 2>&1
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend-next/app/globals.css frontend-next/app/layout.tsx
git commit -m "feat(design): Clinical Command Center CSS variables + Space Grotesk/Inter fonts"
```

---

## Task 2: Restyle `CCEHeader` component

**Files:**
- Modify: `frontend-next/components/CCEHeader.tsx`

**Design spec:** Dark console bar. Height 52px. Background #10141a with a subtle bottom ghost-border. Left: monospace label stack — "BOSTON SCIENTIFIC" (10px, tracked, teal #2ddbde) / "Continuing Clinical Excellence" (9px, text-secondary). Right: avatar circle if `userInitials` prop provided (bg-[#2ddbde] text-[#0a1a1a]).

- [ ] **Step 1: Read the current CCEHeader**

```bash
cat /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next/components/CCEHeader.tsx
```

- [ ] **Step 2: Rewrite CCEHeader**

```typescript
// frontend-next/components/CCEHeader.tsx
interface Props { userInitials?: string }

export default function CCEHeader({ userInitials }: Props) {
  return (
    <header
      className="flex items-center justify-between px-4 h-[52px] bg-[#10141a]"
      style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
    >
      {/* Left: identity */}
      <div className="flex items-center gap-2.5">
        <div className="flex items-center justify-center w-7 h-7 rounded-md bg-[#1c2026] ghost-border">
          {/* Play triangle */}
          <svg width="10" height="12" viewBox="0 0 10 12" fill="none">
            <path d="M0 0L10 6L0 12V0Z" fill="#2ddbde" />
          </svg>
        </div>
        <div className="flex flex-col">
          <span
            className="text-[10px] font-bold tracking-[0.12em] text-[#2ddbde] uppercase"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            BOSTON SCIENTIFIC
          </span>
          <span className="text-[9px] text-[#9aa0a6]">
            Continuing Clinical Excellence
          </span>
        </div>
      </div>

      {/* Right: user avatar */}
      {userInitials && (
        <div
          data-testid="cce-avatar"
          className="flex items-center justify-center w-8 h-8 rounded-full bg-[#2ddbde] text-[#0a1a1a] text-[11px] font-bold"
        >
          {userInitials}
        </div>
      )}
    </header>
  )
}
```

- [ ] **Step 3: Run existing CCEHeader tests**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next
npx jest --testPathPattern="CCEHeader" --no-coverage 2>&1 | tail -10
```

Expected: all PASS (tests check text content + avatar presence — those are unchanged)

- [ ] **Step 4: Commit**

```bash
git add frontend-next/components/CCEHeader.tsx
git commit -m "feat(design): CCEHeader — dark console bar with teal accent"
```

---

## Task 3: Restyle auth screens — login, callback, join

**Files:**
- Modify: `frontend-next/app/auth/login/page.tsx`
- Modify: `frontend-next/app/auth/callback/page.tsx`
- Modify: `frontend-next/app/join/[token]/page.tsx`

**Design spec:**
- Full-screen background: `bg-[#10141a]`
- Card: `bg-[#1c2026] rounded-xl ghost-border w-full max-w-sm` with `shadow-[0px_20px_40px_rgba(45,219,222,0.08)]`
- Primary CTA: `btn-primary-gradient rounded-lg py-2.5 text-sm font-semibold w-full`
- Input fields: `bg-[#181c22] border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2 text-sm text-[#e8eaed] placeholder:text-[#5f6368] focus:border-[#2ddbde] focus:outline-none`
- Labels: `text-[11px] text-[#9aa0a6] font-medium`
- Footer: "No password needed · Powered by LiquidSMARTS™" — `text-[10px] text-[#5f6368] text-center`
- Sent confirmation: teal envelope icon in `bg-[#1c2026]` circle + info box with `bg-[#1c2026] border border-[rgba(45,219,222,0.2)] text-[#2ddbde]`
- Callback spinner: `border-[#31353c] border-t-[#2ddbde]`
- Callback progress bar: `bg-[#1c2026]` track, `bg-[#2ddbde]` fill

- [ ] **Step 1: Read current login page**

```bash
cat /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next/app/auth/login/page.tsx
```

- [ ] **Step 2: Rewrite login page**

```typescript
// frontend-next/app/auth/login/page.tsx
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
    await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: `${window.location.origin}/auth/callback` } })
    setSent(true)
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#10141a]">
      <CCEHeader />
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="bg-[#1c2026] rounded-xl w-full max-w-sm p-6 shadow-[0px_20px_40px_rgba(45,219,222,0.08)]"
          style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
          {!sent ? (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div>
                <h1 className="text-[18px] font-bold text-[#e8eaed]"
                  style={{ fontFamily: 'var(--font-space-grotesk)' }}>
                  CCE Portal
                </h1>
                <p className="text-[12px] text-[#9aa0a6] mt-0.5">Sign in to access your training</p>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] text-[#9aa0a6] font-medium">Work Email</label>
                <input
                  type="email" required value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="name@bsci.com"
                  className="bg-[#181c22] rounded-lg px-3 py-2 text-sm text-[#e8eaed] placeholder:text-[#5f6368] focus:border-[#2ddbde] focus:outline-none w-full"
                  style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                />
              </div>
              <button
                type="submit" disabled={loading}
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
              <div className="w-12 h-12 rounded-full bg-[#181c22] flex items-center justify-center"
                style={{ border: '1px solid rgba(45,219,222,0.2)' }}>
                <svg width="20" height="16" viewBox="0 0 20 16" fill="none">
                  <rect x="0" y="0" width="20" height="16" rx="3" stroke="#2ddbde" strokeWidth="1.5"/>
                  <path d="M0 4L10 10L20 4" stroke="#2ddbde" strokeWidth="1.5"/>
                </svg>
              </div>
              <div className="text-center">
                <p className="text-[15px] font-bold text-[#e8eaed]">Check your inbox</p>
                <p className="text-[12px] text-[#9aa0a6] mt-0.5">
                  We sent a secure link to <strong className="text-[#e8eaed]">{email}</strong>
                </p>
              </div>
              <div className="w-full rounded-lg p-3 text-[11px] text-[#2ddbde]"
                style={{ background: 'rgba(45,219,222,0.06)', border: '1px solid rgba(45,219,222,0.2)' }}>
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
```

- [ ] **Step 3: Read current callback page**

```bash
cat /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next/app/auth/callback/page.tsx
```

- [ ] **Step 4: Apply dark theme to callback — change only colors/classes, preserve all logic**

Replace all color class references: `bg-[#f8fafc]` → `bg-[#10141a]`, `border-[#e2e8f0] border-t-[#0073CF]` → `border-[#31353c] border-t-[#2ddbde]`, `bg-[#0073CF]` circles → `bg-[#2ddbde]`, `h-[3px] bg-[#e2e8f0]` → `h-[3px] bg-[#31353c]`, inner bar `bg-[#0073CF]` → `bg-[#2ddbde]`, text colors `text-[#718096]` → `text-[#9aa0a6]`, `text-[#1a202c]` → `text-[#e8eaed]`.

The `CCEHeader` usage stays identical — it now renders dark automatically from Task 2.

- [ ] **Step 5: Read and restyle join page**

```bash
cat /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next/app/join/[token]/page.tsx
```

Apply the same dark card pattern as login: `bg-[#10141a]` page, `bg-[#1c2026] ghost-border` card, `btn-primary-gradient` CTA, dark inputs.

- [ ] **Step 6: TypeScript check**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next
npx tsc --noEmit 2>&1
```

Expected: no errors

- [ ] **Step 7: Commit**

```bash
git add frontend-next/app/auth/
git commit -m "feat(design): dark auth screens — login, callback, join"
```

---

## Task 4: Restyle dashboard, manager, admin pages

**Files:**
- Modify: `frontend-next/app/dashboard/page.tsx`
- Modify: `frontend-next/app/manager/page.tsx`
- Modify: `frontend-next/app/admin/page.tsx`

**Design spec for all three:**
- Page background: `bg-[#10141a] min-h-screen`
- Cards: `bg-[#1c2026] rounded-xl p-4` with ghost-border (no box-shadow except scenario card)
- Scenario card: add `shadow-[0px_20px_40px_rgba(45,219,222,0.08)]` + left accent border `border-l-2 border-[#2ddbde]`
- Section labels: `text-[10px] uppercase tracking-widest text-[#5f6368] font-semibold`
- Progress bars: track `bg-[#31353c] h-1.5 rounded`, fill `bg-[#2ddbde]`
- "Start →" button: `btn-primary-gradient rounded-lg px-4 py-2 text-sm`
- Stats values: `text-[24px] font-bold text-[#e8eaed]` (Space Grotesk)
- Table rows hover: `hover:bg-[#353940] transition-colors`
- KPI grid values: `text-[28px] font-bold text-[#2ddbde]` (Space Grotesk)
- Empty states: `text-[12px] text-[#5f6368]`

- [ ] **Step 1: Read current dashboard**

```bash
cat /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next/app/dashboard/page.tsx
```

- [ ] **Step 2: Apply dark token replacements to dashboard**

Replace throughout:
- `bg-[#f8fafc]` → `bg-[#10141a]`
- `bg-white` → `bg-[#1c2026]`
- `border border-[#e2e8f0]` → ghost-border style
- `border-l-4 border-[#0073CF]` → `border-l-2 border-[#2ddbde]`
- `text-[#0073CF]` → `text-[#2ddbde]`
- `bg-[#0073CF]` → `bg-gradient-to-br from-[#2ddbde] to-[#007e80]` (on buttons) or `bg-[#2ddbde]` (on fills)
- `text-[#1a202c]` → `text-[#e8eaed]`
- `text-[#718096]` → `text-[#9aa0a6]`
- `text-[#a0aec0]` → `text-[#5f6368]`
- `h-1.5 bg-[#e2e8f0]` → `h-1.5 bg-[#31353c]`
- `shadow-sm` → remove (use ghost-border instead, per No-Line rule)
- Add `style={{ fontFamily: 'var(--font-space-grotesk)' }}` to large numeric values (24px+ headings)

- [ ] **Step 3: Apply same pattern to manager and admin pages**

Follow identical token replacements. For admin KPI grid values, set `text-[#2ddbde]` (primary) instead of secondary text — these are the hero numbers.

- [ ] **Step 4: TypeScript check**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next
npx tsc --noEmit 2>&1
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add frontend-next/app/dashboard/page.tsx frontend-next/app/manager/page.tsx frontend-next/app/admin/page.tsx
git commit -m "feat(design): dark dashboard, manager, admin pages"
```

---

## Task 5: Restyle ArcProgress and CofGates components

**Files:**
- Modify: `frontend-next/components/ArcProgress.tsx`
- Modify: `frontend-next/components/CofGates.tsx`

**ArcProgress spec:** 6 dots in a horizontal strip. Inactive dots: `w-2 h-2 rounded-full bg-[#31353c]`. Active dot: `w-2.5 h-2.5 rounded-full bg-[#2ddbde] shadow-[0_0_8px_rgba(45,219,222,0.6)] animate-pulse`. Completed dots: `bg-[#2ddbde] opacity-60`.

**CofGates spec:** Three cards in a row. Card base: `bg-[#181c22] rounded-lg p-3 ghost-border`. Gate passed: left border `border-l-2 border-[#2ddbde]` + label `text-[#2ddbde]`. Gate missed: left border `border-l-2 border-[#5f6368]` + label `text-[#5f6368]`. Gate pending: no left border + label `text-[#9aa0a6]`. No icons — use `label-sm` uppercase text only per spec.

- [ ] **Step 1: Read ArcProgress**

```bash
cat /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next/components/ArcProgress.tsx
```

- [ ] **Step 2: Apply dark dot styles to ArcProgress**

Replace all dot color classes with the spec above. The component's props and logic stay identical — only className strings change.

- [ ] **Step 3: Read CofGates**

```bash
cat /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next/components/CofGates.tsx
```

- [ ] **Step 4: Apply dark gate styles to CofGates**

Replace all color references with the spec above. Add ghost-border via inline style where Tailwind's `border` color rgba doesn't work: `style={{ border: '1px solid rgba(255,255,255,0.08)' }}`.

- [ ] **Step 5: TypeScript check**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next
npx tsc --noEmit 2>&1
```

Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add frontend-next/components/ArcProgress.tsx frontend-next/components/CofGates.tsx
git commit -m "feat(design): dark ArcProgress and CofGates"
```

---

## Task 6: Upgrade PTT button and restyle VoiceChat session

**Files:**
- Modify: `frontend-next/components/VoiceChat.tsx`
- Modify: `frontend-next/app/session/[id]/page.tsx`

**Session page loading state:** `bg-[#10141a]` with `text-[#9aa0a6]` spinner text.

**VoiceChat PTT button spec (from Stitch):**
- Base: `w-20 h-20 rounded-full btn-primary-gradient` with `inset 0 2px 4px rgba(0,0,0,0.3)` inner shadow
- Idle state: the gradient + inset shadow
- Active/recording state: add outer pulse — `box-shadow: 0 0 0 12px rgba(45,219,222,0.15), 0 0 0 24px rgba(45,219,222,0.06)` + `animate-pulse`
- Processing state: spinner overlay on the button, gradient dimmed to 70% opacity

**VoiceChat layout:**
- Outer container: `bg-[#10141a] min-h-screen`
- Message bubbles (AI): `bg-[#1c2026] ghost-border rounded-xl text-[#e8eaed]`
- Message bubbles (user): `bg-[#181c22] ghost-border rounded-xl text-[#9aa0a6]`
- Coaching notes: `text-[11px] font-mono text-[#2ddbde]` (monospace per spec)
- Bottom bar: `bg-[#10141a]` with top ghost-border, contains PTT button centered

**RepHint component:** Apply `glass` class (from globals.css — backdrop-blur, semi-transparent surface). Text: `text-[#e8eaed]`. Border: `rgba(45,219,222,0.2)`.

- [ ] **Step 1: Read VoiceChat current PTT button markup**

```bash
grep -n "ptt\|PTT\|button\|onClick\|audioState\|rounded-full\|w-16\|w-20" \
  /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next/components/VoiceChat.tsx | head -30
```

- [ ] **Step 2: Replace PTT button JSX in VoiceChat**

Find the PTT button element and replace its className/style. The `onClick` handler and `disabled` logic stay identical.

```tsx
{/* PTT Button — replace existing button element */}
<button
  onClick={handlePTT}
  disabled={audioState === 'processing' || audioState === 'speaking'}
  className="relative w-20 h-20 rounded-full btn-primary-gradient disabled:opacity-40 transition-all duration-200 flex items-center justify-center"
  style={{
    boxShadow: audioState === 'listening'
      ? '0 0 0 12px rgba(45,219,222,0.15), 0 0 0 24px rgba(45,219,222,0.06), inset 0 2px 4px rgba(0,0,0,0.3)'
      : 'inset 0 2px 4px rgba(0,0,0,0.3)',
  }}
>
  {audioState === 'processing' ? (
    <div className="w-6 h-6 rounded-full border-2 border-[#0a1a1a]/40 border-t-[#0a1a1a] animate-spin" />
  ) : (
    <svg width="22" height="28" viewBox="0 0 22 28" fill="none">
      <rect x="6" y="0" width="10" height="18" rx="5" fill="#0a1a1a"/>
      <path d="M1 14C1 20.075 5.477 25 11 25C16.523 25 21 20.075 21 14" stroke="#0a1a1a" strokeWidth="2" strokeLinecap="round"/>
      <line x1="11" y1="25" x2="11" y2="28" stroke="#0a1a1a" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )}
</button>
```

- [ ] **Step 3: Apply dark layout classes to VoiceChat container, messages, bottom bar**

Replace all `bg-[#f8fafc]`, `bg-white`, `text-[#718096]`, `text-[#1a202c]` references with the dark tokens from the design token reference at the top of this plan.

- [ ] **Step 4: Apply `glass` class to RepHint**

```bash
grep -n "className\|class\|bg-\|border" \
  /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next/components/RepHint.tsx
```

Replace the hint container class with `glass rounded-xl p-3 text-[#e8eaed] text-[13px]` and the border with `rgba(45,219,222,0.2)`.

- [ ] **Step 5: Update session loading screen**

```typescript
// frontend-next/app/session/[id]/page.tsx — replace loading divs
// Change: bg-[#f8fafc] → bg-[#10141a], text-[#718096] → text-[#9aa0a6]
```

- [ ] **Step 6: TypeScript check + full suite**

```bash
cd /Users/gunterwessels/Documents/Sandbox/voice-training-mvp/frontend-next
npx tsc --noEmit 2>&1
npx jest --no-coverage 2>&1 | tail -10
```

Expected: tsc clean, all jest tests pass

- [ ] **Step 7: Commit**

```bash
git add frontend-next/components/VoiceChat.tsx frontend-next/components/RepHint.tsx frontend-next/app/session/
git commit -m "feat(design): PTT button gradient+pulse, dark VoiceChat layout, glassmorphism RepHint"
```

---

## Self-Review

**Spec coverage vs Stitch DESIGN.md:**
- Dark surface hierarchy (#10141a / #1c2026 / #181c22 / #31353c) → Tasks 1, 3, 4 ✓
- No-Line rule (ghost-borders only) → Tasks 1, 2, 3, 4, 5, 6 ✓
- Glass & Gradient rule (glassmorphism on overlays) → Task 6 RepHint ✓
- Primary gradient on CTAs → Tasks 1, 3, 4, 6 ✓
- Space Grotesk (display) + Inter (body) → Task 1 ✓
- Monospace for data/coaching notes → Task 6 ✓
- PTT: gradient fill, inset shadow, pulse glow on active → Task 6 ✓
- ArcProgress dots → Task 5 ✓
- COF gates — no icons, uppercase label-sm → Task 5 ✓
- No pure blacks/grays — all surfaces tinted navy → all tasks use #10141a-based palette ✓

**No placeholders confirmed:** All steps contain exact code or exact grep commands + described replacement.

**Type consistency:** `audioState`, `handlePTT`, `userInitials` — all used as defined in existing components. No new props introduced.

---

*Plans complete and saved. Execute with `superpowers:subagent-driven-development` (recommended — one agent per task) or `superpowers:executing-plans`.*
