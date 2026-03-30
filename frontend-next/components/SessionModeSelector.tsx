'use client'

export type SessionMode = 'practice' | 'certification'

interface Props {
  value: SessionMode
  onChange: (mode: SessionMode) => void
}

export default function SessionModeSelector({ value, onChange }: Props) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {/* Practice */}
      <button
        type="button"
        onClick={() => onChange('practice')}
        className={`rounded-lg p-4 text-left transition-all ${
          value === 'practice'
            ? 'bg-[#1c2026] outline outline-2 outline-[#2ddbde]'
            : 'bg-[#181c22] hover:bg-[#1c2026]'
        }`}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
          <span className="text-sm font-bold text-[#e8eaed]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
            Practice
          </span>
        </div>
        <p className="text-[11px] text-[#9aa0a6] leading-relaxed">
          Full access to all materials. Passive logging. No certification outcome.
        </p>
      </button>

      {/* Certification */}
      <button
        type="button"
        onClick={() => onChange('certification')}
        className={`rounded-lg p-4 text-left transition-all ${
          value === 'certification'
            ? 'bg-[#1c2026] outline outline-2 outline-[#2ddbde]'
            : 'bg-[#181c22] hover:bg-[#1c2026]'
        }`}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="text-amber-400 flex-shrink-0">
            <path d="M6 1v10M1 6h10" stroke="none"/>
            <rect x="3" y="1" width="6" height="8" rx="1" stroke="currentColor" strokeWidth="1.2"/>
            <path d="M4 10l2 1 2-1" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
            <path d="M4.5 4h3M4.5 6h2" stroke="currentColor" strokeWidth="1" strokeLinecap="round"/>
          </svg>
          <span className="text-sm font-bold text-[#e8eaed]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
            Certification
          </span>
        </div>
        <p className="text-[11px] text-[#9aa0a6] leading-relaxed">
          Approved content only. Evaluated session. Certification issued on pass.
        </p>
      </button>
    </div>
  )
}
