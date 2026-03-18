# BSCI CCE Portal — UI Overhaul & Domain Design

## Goal

Replace all generic Next.js placeholder UI with a branded, mobile-first BSCI Continuing Clinical Excellence experience ready for customer beta testing. Add custom domain `bsc.liquidsmarts.com`.

## Design Decisions

**Visual direction:** Clean & Clinical — white/light gray surfaces, BSC blue (`#0073CF`) as primary, system fonts, no dark mode.

**Branding:** Program-forward. "BSCI Continuing Clinical Excellence" is the identity. "CCE Portal" is the short form. "Powered by LiquidSMARTS™" appears in footer/small print only.

**Personalization:** The auth callback screen greets reps by first name ("Welcome, Sarah.") pulled from Supabase `user_metadata.first_name`. This requires first name to be stored at onboarding (written during `/join` flow).

**Auth flow:** Magic link only — no password. Three states on the login/callback screens: enter email → check inbox (echoes their email) → welcome by name → dashboard.

---

## Design System

### Colors
- Primary: `#0073CF` (BSC blue)
- Primary dark: `#0052a3`
- Background: `#f8fafc`
- Surface: `#ffffff`
- Border: `#e2e8f0`
- Text primary: `#1a202c`
- Text secondary: `#718096`
- Text muted: `#a0aec0`
- Success: `#1a7a3f` / `#e6f4ea`
- Info bg: `#f0f7ff` / border `#bfdbfe` / text `#1e40af`

### Shared Header Component (`<CCEHeader>`)
All pages share a consistent top bar:
- Background: `#0073CF`
- Height: `52px`, `px-4`
- Left side: 32×32px `bg-white/20 rounded-lg` box containing an inline SVG play icon (triangle pointing right, 14×14, white fill) + text stack: "BOSTON SCIENTIFIC" (11px, font-bold, white, tracking-wide) / "Continuing Clinical Excellence" (9px, `text-white/75`)
- Right side: rep dashboard only — 32×32 `bg-white/20 rounded-full` circle with user initials (12px, font-bold, white). All other pages: empty.
- Props: `{ userInitials?: string }` — renders avatar only when prop is provided.

### Footer (login and join pages only)
- "No password needed · Powered by LiquidSMARTS™" — `text-[10px] text-muted text-center`

---

## Screens

### 1. Root `/` — Redirect
**File:** `app/page.tsx`

Two behaviors depending on session state — check with `supabase.auth.getSession()` on mount (client component):
- Session exists → `router.replace('/dashboard')`
- No session → `router.replace('/auth/login')`

Use `'use client'` + `useEffect`. Render a blank white screen while the check runs (no flash of boilerplate).

---

### 2. Login `/auth/login`
**File:** `app/auth/login/page.tsx`

**Layout:** Full-screen centered card on `bg-[#f8fafc]`. Card is `bg-white rounded-xl shadow-sm w-full max-w-sm`.

**States:**
- **Default:** CCEHeader (no initials) + card body: "CCE Portal" (h1, 20px bold) + "Sign in to access your training" (12px, secondary) + email input (label: "Work Email", placeholder: "name@bsci.com", `border border-[#e2e8f0] rounded-lg px-3 py-2 text-sm w-full`) + "Send My Access Link →" button (full-width, `bg-[#0073CF] text-white rounded-lg py-2.5 text-sm font-semibold`) + footer
- **Sent:** Replace form with: green envelope SVG icon (inline, 22px, `#1a7a3f`, in 48px `bg-[#e6f4ea] rounded-full` circle) + "Check your inbox" (16px bold) + "We sent a secure link to **[email]**" (12px, secondary) + blue info box (`bg-[#f0f7ff] border border-[#bfdbfe] rounded-lg p-3 text-[11px] text-[#1e40af]`): "Click the link in your email to sign in. It expires in 1 hour."

**Technical:** Store submitted email in `useState`. On `supabase.auth.signInWithOtp()` success set `sent = true`. No backend call.

---

### 3. Auth Callback `/auth/callback`
**File:** `app/auth/callback/page.tsx`

**Header:** CCEHeader present on all 3 states — no `userInitials` prop (no avatar).

**Initialization:** On mount, call `supabase.auth.getSession()` first. If a session is already present (magic link processed before component mounted), skip the listener and jump directly to the Welcome state. Otherwise, register `onAuthStateChange` to listen for `SIGNED_IN`.

**States (3):**
1. **Verifying** (default): Centered spinner (`border-4 border-[#e2e8f0] border-t-[#0073CF] rounded-full w-8 h-8 animate-spin`) + "Verifying your link…" (12px, muted)
2. **Welcome** (session established): Call `supabase.auth.getUser()` → read `user.user_metadata.first_name` (fall back to email prefix if absent). Display:
   - 52×52 `bg-[#0073CF] rounded-full` circle with white checkmark SVG + `ring-[6px] ring-[#0073CF]/20`
   - "Welcome, [firstName]." (18px, font-extrabold)
   - "You're in the right place." (12px, secondary)
   - Progress bar: `h-[3px] bg-[#e2e8f0] rounded` track, inner div starts at `w-0` and transitions to `w-full` over 2s linear (`transition-all duration-[2000ms] ease-linear`). The `w-full` class must be applied via a state variable set inside `setTimeout(() => setAnimating(true), 0)` immediately after the Welcome state is entered — this ensures the initial `w-0` render commits to the DOM before the transition fires. After 2s, `router.replace('/dashboard')`.
3. **Error** (auth failure / `SIGNED_OUT` on error): "This link has expired or already been used." + "Request a new link →" link to `/auth/login`

---

### 4. Join `/join/[token]`
**File:** `app/join/[token]/page.tsx`

**Layout:** Same card pattern as login.

**States:**
- **Default:** CCEHeader (no initials) + "You've been invited" (h1) + "Boston Scientific CCE Program" (subtitle) + Name input + Email input + "Join the Program →" button + footer
- **Sent:** Green checkmark icon + "Check your email" + "We sent your access link to **[email]**"

**Technical:** On submit, POST to `/api/join` with `{ cohort_token: token, name, email }`. Note: the backend `JoinRequest` model uses the field name `cohort_token` — the URL param `token` must be mapped to this field name on submission. On HTTP 200 set `sent = true`. On non-200 show inline error.

---

### 5. Rep Dashboard `/dashboard`
**File:** `app/dashboard/page.tsx`
**Mode:** `'use client'`

**Sections (top to bottom):**
1. **CCEHeader** with `userInitials` prop (derive from user email/metadata on mount via `supabase.auth.getUser()`)
2. **Certification Progress card** — `bg-white rounded-xl shadow-sm p-4`: "Certification Progress" (11px, semibold, secondary, uppercase tracked) + "0 / 1 complete" right-aligned in `#0073CF` + `h-1.5 bg-[#e2e8f0] rounded` track with `bg-[#0073CF]` fill (width = certs/total × 100%)
3. **Scenario card** — `bg-white rounded-xl shadow-sm p-4 border-l-4 border-[#0073CF]`: "REQUIRED" badge (`text-[10px] font-bold text-[#0073CF] uppercase tracking-widest`) + scenario name (13px, font-bold) + "6 stages · Not started" (11px, muted) + "Start →" button (`bg-[#0073CF] text-white text-sm px-4 py-2 rounded-lg font-semibold`, floated right)
4. **Recent Sessions** — section label (10px, uppercase, tracked, muted) + always renders empty state "No sessions yet" (12px, muted, centered, `py-6`). No API call — static empty state for beta. Wire to real data in a future sprint.
5. **Stats row** — 3 equal `bg-white rounded-xl shadow-sm` cards: Sessions / Certs / Streak. Values from `/api/completions`.

**Data fetching:** Single `useEffect` on mount — `Promise.all([fetch('/api/completions'), fetch('/api/series')])`. On any non-200 or network error, silently show zero/dash values (no error toast for beta). Never block render.

**Endpoint response contracts:**

`GET /api/completions` → `{ sessions_completed: number, certs_earned: number, streak_days: number | null }`
- `sessions_completed` → Sessions stat card value
- `certs_earned` → Certs stat card value + numerator in Certification Progress "X / 1 complete"
- `streak_days` → Streak stat card value (render `—` if null)

`GET /api/series` → `{ series: Array<{ id: string, name: string, stage_count: number, status: 'not_started' | 'in_progress' | 'complete' }> }`
- First item in array → Scenario card (name, stage_count, status label)
- `status === 'complete'` → hide "Start →" button, show green "✓ Complete" badge instead

---

### 6. Manager Dashboard `/manager`
**File:** `app/manager/page.tsx`
**Mode:** `'use client'`

**Sections:**
1. **CCEHeader** — no `userInitials` prop (no avatar on manager view)
2. **Cohort header card** — `bg-white rounded-xl shadow-sm p-4`: "Cohort Overview" (h1) + "0 of 0 certified" right-aligned `text-[#0073CF] font-bold text-sm` + `h-1.5` cert progress bar + "Export CSV" link (`text-sm text-[#0073CF] hover:underline`)
3. **Rep table** — `bg-white rounded-xl shadow-sm overflow-hidden`: columns Name / Sessions / Last Active / Cert (✓ in green or — in muted) + empty state row spanning all columns: "No reps enrolled yet." (`text-sm text-[#a0aec0] text-center py-8`)

**Data:** `useEffect` → `fetch('/api/manager/cohort')`. On error show zeros/empty state.

---

### 7. Admin Dashboard `/admin`
**File:** `app/admin/page.tsx`
**Mode:** `'use client'`

**Sections:**
1. **CCEHeader** — no `userInitials`
2. **Header card** — "Platform Metrics" (h1) + "Last 30 days" (12px, muted)
3. **KPI grid** — `grid grid-cols-2 gap-3`: Sessions / Cost (USD) / Flagged / Cert Rate — each `bg-white rounded-xl shadow-sm p-4`: large bold value (24px) + label (11px, muted)
4. **Flagged Sessions** — `bg-white rounded-xl shadow-sm p-4`: "Flagged Sessions" label + "No flagged sessions." empty state

**Data:** `useEffect` → `fetch('/api/admin/metrics')`. On error show zeros.

---

## Domain Configuration

### Step 1: DNS (`liquidsmarts.com` — Hostinger DNS panel)
Add CNAME record:
```
Name:  bsc
Type:  CNAME
Value: voice-training-frontend-production.up.railway.app
TTL:   300
```

### Step 2: Railway custom domain (Railway dashboard)
Go to Railway → project `daring-reverence` → service `voice-training-frontend` → **Settings → Networking → Add Custom Domain** → enter `bsc.liquidsmarts.com`. Railway will provision the TLS cert automatically once DNS propagates.

### Step 3: Update environment variables
- Backend `ALLOWED_ORIGINS`: add `https://bsc.liquidsmarts.com` (via `railway variables --service voice-training-backend`)
- Frontend `NEXT_PUBLIC_API_URL`: no change needed
- Supabase Auth: Dashboard → project `zpjqpuyrjssotofxiukh` → Authentication → URL Configuration → add `https://bsc.liquidsmarts.com/auth/callback` to **Redirect URLs**

---

## Backend Changes Required

### 1. `/api/join` — write `first_name` to Supabase user metadata
After successfully processing the join request, extract first name from the `name` field and write it to Supabase `user_metadata` so the callback page can greet the rep by name:

```python
first_name = body.name.split()[0] if body.name else ""
# After creating/inviting the Supabase user (user_id obtained from invite response):
supabase_admin.auth.admin.update_user_by_id(user_id, {
    "user_metadata": {"first_name": first_name}
})
```

The `supabase_admin` client uses `SUPABASE_SERVICE_ROLE_KEY` (already in env). This call requires the service role key — the anon client cannot write `user_metadata`.

---

## Files Changed

| File | Change |
|------|--------|
| `frontend-next/app/page.tsx` | Session-aware redirect (dashboard if authed, login if not) |
| `frontend-next/app/auth/login/page.tsx` | Full redesign + sent confirmation state |
| `frontend-next/app/auth/callback/page.tsx` | 3 states + `getSession()` pre-check + name personalization |
| `frontend-next/app/join/[token]/page.tsx` | Redesign + invited framing + `cohort_token` field mapping |
| `frontend-next/app/dashboard/page.tsx` | Progress-focused layout + data fetch |
| `frontend-next/app/manager/page.tsx` | BSC header + cohort progress + table |
| `frontend-next/app/admin/page.tsx` | BSC header + KPI grid |
| `frontend-next/components/CCEHeader.tsx` | New shared header component |
| `backend/main.py` | Write `first_name` to `user_metadata` in `/api/join` |

---

## Out of Scope
- Voice session UI (`/session/[id]`) — already built, not touched this sprint
- Manager/admin authentication gating — already handled by middleware
- Email template for magic link — controlled by Supabase
- Recent Sessions list on dashboard — empty state only; wire to API in future sprint
