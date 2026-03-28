'use client'
import { useState, useEffect } from 'react'

const SCRIPT = "We're practicing — nothing here is real. Speak naturally, like you're in the room. Don't try to record anything, just talk. I'm listening for discovery, COF impact, and how you handle objections. Tap anywhere when you're ready."

export default function OnboardingOverlay({ onDismiss }: { onDismiss: () => void }) {
  const [visible, setVisible] = useState(true)
  const [countdown, setCountdown] = useState(20)

  useEffect(() => {
    const interval = setInterval(() => setCountdown(c => c - 1), 1000)
    const timer = setTimeout(() => { setVisible(false); onDismiss() }, 20000)
    return () => { clearInterval(interval); clearTimeout(timer) }
  }, [onDismiss])

  if (!visible) return null

  return (
    <div className="fixed inset-0 bg-gray-900/95 flex flex-col items-center justify-center z-50 px-6"
         onClick={() => { setVisible(false); onDismiss() }}>
      <div className="max-w-sm text-center space-y-6">
        <div className="flex justify-center gap-1">
          {[1,2,3,4,5].map(i => (
            <div key={i} className="w-1 bg-[#2ddbde] rounded animate-bounce"
                 style={{ height: `${20 + i * 8}px`, animationDelay: `${i * 0.1}s` }} />
          ))}
        </div>
        <p className="text-white text-lg leading-relaxed">{SCRIPT}</p>
        <p className="text-[#9aa0a6] text-sm">Tap anywhere to skip · {countdown}s</p>
      </div>
    </div>
  )
}
