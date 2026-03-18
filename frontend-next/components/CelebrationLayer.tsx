'use client'
import { useEffect } from 'react'
import confetti from 'canvas-confetti'

const CELEBRATIONS: Record<string, { type: string; message: string; audio?: string }> = {
  first_session:   { type: 'confetti', message: "You just had your first AI sales conversation. Most people don't even try." },
  first_cof_clean: { type: 'badge',    message: "Clean COF sweep.", audio: '/celebrations/chime.mp3' },
  streak_3:        { type: 'audio',    message: "OK I have to say — you're getting better at this.", audio: '/celebrations/persona-streak.mp3' },
  speed_stage_5:   { type: 'badge',    message: "Fast hands." },
  first_cert:      { type: 'confetti', message: "Certificate earned.", audio: '/celebrations/cert-sound.mp3' },
  same_day_series: { type: 'text',     message: "Same-day finish. Noted." },
  redemption_arc:  { type: 'text',     message: "Redemption arc complete." },
}

interface Props { trigger: string; cohortCelebrationsEnabled: boolean }

export default function CelebrationLayer({ trigger, cohortCelebrationsEnabled }: Props) {
  const cel = CELEBRATIONS[trigger]
  useEffect(() => {
    if (!cohortCelebrationsEnabled || !cel) return
    if (cel.type === 'confetti') confetti({ particleCount: 120, spread: 70, origin: { y: 0.6 } })
    if (cel.audio) new Audio(cel.audio).play().catch(() => {})
  }, [trigger, cohortCelebrationsEnabled, cel])

  if (!cohortCelebrationsEnabled || !cel) return null
  return (
    <div data-testid="celebration-message"
         className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-gray-900 text-white px-6 py-3 rounded-full text-sm shadow-lg z-50">
      {cel.message}
    </div>
  )
}
