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
