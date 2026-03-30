'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'
import CCEHeader from '@/components/CCEHeader'
import ContentLibrary from '@/components/ContentLibrary'

function getInitials(email: string): string {
  const parts = email.split('@')[0].split(/[._-]/)
  return parts.slice(0, 2).map(p => p[0]?.toUpperCase() ?? '').join('')
}

export default function LibraryPage() {
  const router = useRouter()
  const [initials, setInitials] = useState('')

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) { router.replace('/auth/login'); return }
      if (user.email) setInitials(getInitials(user.email))
    })
  }, [router])

  return (
    <div className="bg-[#10141a] min-h-screen flex flex-col">
      <CCEHeader userInitials={initials || undefined} />
      <main className="flex-1 p-4 max-w-5xl mx-auto w-full">
        <div className="mb-4">
          <h1
            className="text-xl font-bold text-[#e8eaed]"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            Content Library
          </h1>
          <p className="text-[12px] text-[#9aa0a6] mt-0.5">
            Admin-approved scenarios and your personal practice materials.
          </p>
        </div>
        <ContentLibrary />
      </main>
    </div>
  )
}
