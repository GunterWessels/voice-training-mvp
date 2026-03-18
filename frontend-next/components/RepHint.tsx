'use client'

interface Props { hint: string | null }

export function RepHint({ hint }: Props) {
  if (!hint) return null
  return (
    <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 animate-fade-in">
      <div className="bg-slate-800/90 backdrop-blur border border-amber-500/30 text-amber-300 text-sm px-4 py-2.5 rounded-full shadow-lg max-w-sm text-center">
        {hint}
      </div>
    </div>
  )
}
