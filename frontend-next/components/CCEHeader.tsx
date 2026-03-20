'use client'
import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { createClient } from '@/lib/supabase'

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

interface CCEHeaderProps {
  userInitials?: string
}

type Role = 'rep' | 'manager' | 'admin' | null

export default function CCEHeader({ userInitials }: CCEHeaderProps) {
  const pathname = usePathname()
  const [role, setRole] = useState<Role>(null)
  const [initials, setInitials] = useState(userInitials ?? '')

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) return
      // Resolve role from backend allowlist check
      fetch(`${API}/api/auth/check`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      })
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d?.role) setRole(d.role) })
        .catch(() => {})

      // Derive initials from email if not passed as prop
      if (!userInitials && session.user?.email) {
        const parts = session.user.email.split('@')[0].split(/[._-]/)
        setInitials(parts.slice(0, 2).map((p: string) => p[0]?.toUpperCase() ?? '').join(''))
      }
    })
  }, [userInitials])

  const navLinks: { href: string; label: string; minRole: Role }[] = [
    { href: '/dashboard', label: 'Practice',  minRole: 'rep' },
    { href: '/manager',   label: 'Team',      minRole: 'manager' },
    { href: '/admin',     label: 'Admin',     minRole: 'admin' },
  ]

  const roleRank: Record<string, number> = { rep: 1, manager: 2, admin: 3 }
  const visibleLinks = navLinks.filter(l =>
    role && roleRank[role] >= roleRank[l.minRole ?? 'rep']
  )

  return (
    <header
      style={{ background: '#0073CF', height: '52px' }}
      className="flex items-center justify-between px-4 flex-shrink-0"
    >
      {/* Left: logo */}
      <a href="/dashboard" className="flex items-center gap-2.5 flex-shrink-0">
        <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3 2l9 5-9 5V2z" fill="white" />
          </svg>
        </div>
        <div className="hidden sm:block">
          <div className="text-[11px] font-bold text-white tracking-wide leading-none">
            BOSTON SCIENTIFIC
          </div>
          <div className="text-[9px] text-white/75 leading-none mt-0.5">
            Continuing Clinical Excellence
          </div>
        </div>
      </a>

      {/* Center: nav links (role-gated) */}
      {visibleLinks.length > 0 && (
        <nav className="flex items-center gap-1">
          {visibleLinks.map(link => {
            const active = pathname === link.href || pathname.startsWith(link.href + '/')
            return (
              <a
                key={link.href}
                href={link.href}
                className={`text-[11px] font-semibold px-3 py-1.5 rounded-md transition-colors ${
                  active
                    ? 'bg-white/25 text-white'
                    : 'text-white/70 hover:text-white hover:bg-white/15'
                }`}
              >
                {link.label}
              </a>
            )
          })}
        </nav>
      )}

      {/* Right: avatar */}
      {initials ? (
        <div
          data-testid="cce-avatar"
          className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center text-[12px] font-bold text-white flex-shrink-0"
        >
          {initials}
        </div>
      ) : (
        <div className="w-8 flex-shrink-0" /> /* spacer to keep logo centered */
      )}
    </header>
  )
}
