'use client'

interface Props { hint: string | null }

export function RepHint({ hint }: Props) {
  if (!hint) return null
  return (
    <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 animate-fade-in max-w-sm w-full px-4">
      <div
        className="glass rounded-xl p-3 text-[#e8eaed] text-[13px] text-center shadow-lg"
        style={{ border: '1px solid rgba(45,219,222,0.2)' }}
      >
        {hint}
      </div>
    </div>
  )
}
