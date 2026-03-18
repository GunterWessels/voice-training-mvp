'use client'

type AudioState = 'idle' | 'listening' | 'processing' | 'speaking'

interface Props { state: AudioState }

const STATE_CONFIG: Record<AudioState, { label: string; color: string; animation: string }> = {
  idle:       { label: 'Tap to start',  color: 'text-gray-400',   animation: '' },
  listening:  { label: 'Listening…',   color: 'text-teal-400',   animation: 'animate-pulse' },
  processing: { label: 'Processing…',  color: 'text-blue-400',   animation: 'animate-spin' },
  speaking:   { label: 'Speaking…',    color: 'text-indigo-400', animation: 'animate-bounce' },
}

export default function AudioStateDisplay({ state }: Props) {
  const { label, color, animation } = STATE_CONFIG[state]
  return (
    <div data-testid="audio-state" data-state={state}
         className="flex flex-col items-center gap-3 py-6">
      {/* Waveform bars — 5 bars, height varies by state */}
      <div className="flex items-end gap-1 h-10">
        {[1,2,3,4,5].map(i => (
          <div
            key={i}
            className={`w-1.5 rounded-full bg-current ${color} transition-all duration-150`}
            style={{
              height: state === 'idle'       ? '4px'
                    : state === 'listening'  ? `${8 + (i * 6)}px`
                    : state === 'processing' ? `${(i % 2 === 0) ? 20 : 8}px`
                    : `${4 + (i * 5)}px`,
              animationDelay: `${i * 80}ms`,
            }}
          />
        ))}
      </div>
      <span className={`text-sm font-medium tracking-wide ${color} ${animation}`}>
        {label}
      </span>
    </div>
  )
}
