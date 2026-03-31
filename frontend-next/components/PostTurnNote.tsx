'use client'
import { useEffect, useRef, useState } from 'react'

interface Props {
  note: string | null
}

export function PostTurnNote({ note }: Props) {
  const [visible, setVisible] = useState(false)
  const [displayNote, setDisplayNote] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!note) return
    if (timerRef.current) clearTimeout(timerRef.current)
    setDisplayNote(note)
    setVisible(true)
    timerRef.current = setTimeout(() => {
      setVisible(false)
      timerRef.current = null
    }, 4000)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [note])

  if (!displayNote) return null

  return (
    <div
      style={{
        opacity: visible ? 1 : 0,
        transition: 'opacity 0.35s ease',
        borderLeft: '3px solid #2ddbde',
        background: '#31353c',
        pointerEvents: visible ? 'auto' : 'none',
      }}
      className="mx-4 mb-2 rounded-lg px-3 py-2"
    >
      <p className="text-[11px] text-[#9aa0a6] font-bold uppercase tracking-wider mb-0.5">Coach Note</p>
      <p className="text-[12px] text-[#e8eaed] italic" style={{ fontFamily: 'var(--font-inter)' }}>
        {displayNote}
      </p>
    </div>
  )
}
