// frontend-next/components/CCEHeader.tsx
interface Props { userInitials?: string }

export default function CCEHeader({ userInitials }: Props) {
  return (
    <header
      className="flex items-center justify-between px-4 h-[52px] bg-[#10141a]"
      style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
    >
      <div className="flex items-center gap-2.5">
        <div
          className="flex items-center justify-center w-7 h-7 rounded-md bg-[#1c2026]"
          style={{ border: '1px solid rgba(255,255,255,0.08)' }}
        >
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
