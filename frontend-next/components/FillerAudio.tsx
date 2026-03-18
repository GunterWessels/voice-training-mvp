'use client'
import { useRef, useCallback } from 'react'

const FILLER_CLIPS = ['hmm','go-on','interesting','thats-a-lot','ok',
                       'right-right','mm-hmm','long-answer','tell-me-more','noted']

interface Props { personaId: string; triggerMs?: number }

export function useFillerAudio({ personaId, triggerMs = 800 }: Props) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastClipRef = useRef<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const startTimer = useCallback(() => {
    timerRef.current = setTimeout(() => {
      let clip: string
      do { clip = FILLER_CLIPS[Math.floor(Math.random() * FILLER_CLIPS.length)] }
      while (clip === lastClipRef.current)
      lastClipRef.current = clip
      const audio = new Audio(`/filler/${personaId}/${clip}.mp3`)
      audioRef.current = audio
      audio.play().catch(() => {})
    }, triggerMs)
  }, [personaId, triggerMs])

  const cancel = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
  }, [])

  return { startTimer, cancel }
}
