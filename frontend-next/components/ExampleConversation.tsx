'use client'
import { useRef, useState } from 'react'
import { createClient } from '@/lib/supabase'

const API = process.env.NEXT_PUBLIC_API_URL ?? ''

interface Turn {
  speaker: 'rep' | 'buyer'
  text: string
  coaching?: string
}

interface Props {
  script: Turn[]
}

function PlayIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.2"/>
      <path d="M5.5 4.5l4 2.5-4 2.5V4.5z" fill="currentColor"/>
    </svg>
  )
}

function PauseIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.2"/>
      <path d="M5.5 4.5h1.2v5H5.5zM7.3 4.5h1.2v5H7.3z" fill="currentColor"/>
    </svg>
  )
}

function SpeakerLabel({ speaker }: { speaker: 'rep' | 'buyer' }) {
  if (speaker === 'rep') {
    return (
      <span className="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded"
        style={{ background: 'rgba(45,219,222,0.12)', color: '#2ddbde' }}>
        Rep
      </span>
    )
  }
  return (
    <span className="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded"
      style={{ background: 'rgba(129,140,248,0.12)', color: '#818cf8' }}>
      Dr. Ellis
    </span>
  )
}

export default function ExampleConversation({ script }: Props) {
  const [activeIdx, setActiveIdx] = useState<number | null>(null)
  const [loadingIdx, setLoadingIdx] = useState<number | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [playingAll, setPlayingAll] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const stopRef = useRef(false)

  async function getToken(): Promise<string | null> {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token ?? null
  }

  async function playTurn(idx: number): Promise<void> {
    const turn = script[idx]
    const token = await getToken()
    if (!token) return
    setLoadingIdx(idx)
    setActiveIdx(idx)
    try {
      const res = await fetch(`${API}/api/demo/tts`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: turn.text, speaker: turn.speaker }),
      })
      if (!res.ok) throw new Error('TTS failed')
      const { audio_data, content_type } = await res.json()
      setLoadingIdx(null)
      await new Promise<void>((resolve) => {
        const audio = new Audio(`data:${content_type};base64,${audio_data}`)
        audioRef.current = audio
        audio.onended = () => resolve()
        audio.onerror = () => resolve()
        audio.play().catch(() => resolve())
      })
    } catch {
      setLoadingIdx(null)
    }
    if (!stopRef.current) setActiveIdx(null)
  }

  async function playAll() {
    stopRef.current = false
    setPlayingAll(true)
    setExpanded(true)
    for (let i = 0; i < script.length; i++) {
      if (stopRef.current) break
      await playTurn(i)
      // small gap between turns
      await new Promise(r => setTimeout(r, 350))
    }
    setPlayingAll(false)
    setActiveIdx(null)
  }

  function stopAll() {
    stopRef.current = true
    setPlayingAll(false)
    setActiveIdx(null)
    setLoadingIdx(null)
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
  }

  return (
    <div className="bg-[#1c2026] border border-white/[0.06] rounded-xl overflow-hidden">
      {/* Header row */}
      <div className="flex items-center justify-between px-5 py-4">
        <div>
          <p className="text-[11px] font-semibold text-[#2ddbde] uppercase tracking-widest">
            Example Conversation
          </p>
          <p className="text-[11px] text-[#5f6368] mt-0.5">
            Watch what a great conversation looks like before you practice.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {playingAll ? (
            <button
              onClick={stopAll}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-colors"
              style={{ background: 'rgba(239,68,68,0.12)', color: '#ef4444' }}
            >
              <PauseIcon />
              Stop
            </button>
          ) : (
            <button
              onClick={playAll}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-colors"
              style={{ background: 'rgba(45,219,222,0.1)', color: '#2ddbde' }}
            >
              <PlayIcon />
              Play Audio
            </button>
          )}
          <button
            onClick={() => setExpanded(e => !e)}
            className="px-3 py-1.5 rounded-lg text-[11px] font-semibold text-[#9aa0a6] hover:text-[#e8eaed] transition-colors"
            style={{ background: 'rgba(255,255,255,0.04)' }}
          >
            {expanded ? 'Hide' : 'Read'}
          </button>
        </div>
      </div>

      {/* Conversation turns */}
      {expanded && (
        <div className="border-t border-white/[0.06] divide-y divide-white/[0.04]">
          {script.map((turn, i) => (
            <div
              key={i}
              className={`px-5 py-3 transition-colors ${
                activeIdx === i ? 'bg-[#2ddbde]/[0.04]' : ''
              } ${turn.speaker === 'rep' ? '' : 'bg-[#181c22]'}`}
            >
              <div className="flex items-start gap-3">
                {/* Play single turn button */}
                <button
                  onClick={() => playTurn(i)}
                  disabled={loadingIdx !== null || playingAll}
                  className="flex-shrink-0 mt-0.5 text-[#5f6368] hover:text-[#2ddbde] transition-colors disabled:opacity-30"
                  title="Play this line"
                >
                  {loadingIdx === i ? (
                    <div className="w-3.5 h-3.5 rounded-full border border-[#2ddbde]/40 border-t-[#2ddbde] animate-spin" />
                  ) : (
                    <PlayIcon size={14} />
                  )}
                </button>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <SpeakerLabel speaker={turn.speaker} />
                    {activeIdx === i && (
                      <span className="text-[9px] text-[#2ddbde] animate-pulse">playing</span>
                    )}
                  </div>
                  <p className="text-[13px] text-[#e8eaed] leading-relaxed">{turn.text}</p>
                  {turn.coaching && (
                    <div className="mt-2 flex items-start gap-1.5">
                      <span className="text-[9px] font-bold text-[#5f6368] uppercase tracking-wider flex-shrink-0 mt-0.5">
                        Why
                      </span>
                      <p className="text-[11px] text-[#5f6368] leading-relaxed italic">{turn.coaching}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
