'use client'
import { useEffect, useRef, useState, useCallback } from 'react'
import ArcProgress from './ArcProgress'
import AudioStateDisplay from './AudioStateDisplay'
import CofGates from './CofGates'
import { SpinGates, ChallengerGates } from './MethodologyGates'
import { useFillerAudio } from './FillerAudio'
import OnboardingOverlay from './OnboardingOverlay'
import { RepHint } from './RepHint'
import { GradingDebrief } from './GradingDebrief'

// Web Speech API — not included in TypeScript's default DOM lib
interface ISpeechRecognitionEvent extends Event {
  results: { [i: number]: { [j: number]: { transcript: string } } }
}
interface ISpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  onstart: (() => void) | null
  onresult: ((event: ISpeechRecognitionEvent) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
}
declare global {
  interface Window {
    SpeechRecognition?: new () => ISpeechRecognition
    webkitSpeechRecognition?: new () => ISpeechRecognition
  }
}

type AudioState = 'idle' | 'listening' | 'processing' | 'speaking'

interface CofGateState { clinical: boolean; operational: boolean; financial: boolean }

interface Message { role: 'user' | 'ai'; text: string; coachingNote?: string }

interface Props {
  sessionId: string
  token: string
  apiBase: string
  seriesId?: string  // passed through for "Practice Again" routing
}

export default function VoiceChat({ sessionId, token, apiBase, seriesId }: Props) {
  const wsRef = useRef<WebSocket | null>(null)
  const recognitionRef = useRef<ISpeechRecognition | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)  // prevent GC before onended fires
  const [audioState, setAudioState] = useState<AudioState>('idle')
  const [messages, setMessages] = useState<Message[]>([])
  const [arcStage, setArcStage] = useState(0)
  const [cofGates, setCofGates] = useState<CofGateState>({ clinical: false, operational: false, financial: false })
  const [spinGates, setSpinGates] = useState({ situation: false, problem: false, implication: false, need_payoff: false })
  const [challengerGates, setChallengerGates] = useState({ teach: false, tailor: false, take_control: false })
  const [personaId, setPersonaId] = useState<string>('')
  const [scenarioName, setScenarioName] = useState('')
  const [isDemo, setIsDemo] = useState(false)
  const [sessionEnded, setSessionEnded] = useState(false)
  const sessionEndedRef = useRef(false)  // stable ref for onclose closure
  const [showOnboarding, setShowOnboarding] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const filler = useFillerAudio({ personaId: personaId || 'default' })
  const fillerRef = useRef(filler)
  fillerRef.current = filler  // keep ref current on every render
  const [hint, setHint] = useState<string | null>(null)
  const [debrief, setDebrief] = useState<any | null>(null)
  // Coach notes are off by default in practice; toggle on demand
  const [showCoach, setShowCoach] = useState(false)

  // Connect to WebSocket with automatic reconnect (handles Railway proxy idle drops)
  useEffect(() => {
    let destroyed = false
    let retryCount = 0
    const MAX_RETRIES = 5

    function connect() {
      if (destroyed || sessionEndedRef.current) return
      const wsBase = apiBase.replace(/^http/, 'ws')
      const ws = new WebSocket(`${wsBase}/ws/${sessionId}?token=${token}`)
      wsRef.current = ws

      ws.onmessage = (event) => {
        let msg: Record<string, unknown>
        try { msg = JSON.parse(event.data) } catch { return }

        if (msg.type === 'ready') {
          retryCount = 0  // successful connection — reset retry counter
          setError(null)
          setPersonaId((msg.persona as any)?.id ?? '')
          setScenarioName((msg.scenario as any)?.name ?? 'Training Session')
          if (msg.is_demo) setIsDemo(true)
        }

        if (msg.type === 'ai_message') {
          fillerRef.current.cancel()
          setMessages(prev => [...prev, {
            role: 'ai',
            text: msg.text as string,
            coachingNote: msg.coaching_note as string | undefined,
          }])
          if (msg.cof_gates) setCofGates(msg.cof_gates as CofGateState)
          if (msg.spin_gates) setSpinGates(msg.spin_gates as typeof spinGates)
          if (msg.challenger_gates) setChallengerGates(msg.challenger_gates as typeof challengerGates)
          if (typeof msg.arc_stage === 'number') setArcStage(msg.arc_stage)

          // Play audio — backend sends field as "audio" (base64 mp3)
          const audioB64 = (msg.audio_b64 ?? msg.audio) as string | undefined
          if (audioB64) {
            setAudioState('speaking')
            const audioEl = new Audio(`data:audio/mp3;base64,${audioB64}`)
            audioRef.current = audioEl  // hold ref to prevent GC before onended fires
            audioEl.onended = () => { audioRef.current = null; setAudioState('idle') }
            audioEl.play().catch(() => { audioRef.current = null; setAudioState('idle') })
          } else {
            setAudioState('idle')
          }

          if (msg.session_end) { sessionEndedRef.current = true; setSessionEnded(true); setAudioState('idle') }
        }

        if (msg.type === 'ai_response' && msg.hint) {
          setHint(msg.hint as string)
          setTimeout(() => setHint(null), 6000)
        }

        if (msg.type === 'grading_debrief') {
          setDebrief(msg.debrief)
        }

        if (msg.type === 'error') {
          setError(msg.message as string)
          setAudioState('idle')
        }
      }

      ws.onerror = () => {
        // onerror always fires before onclose — let onclose handle retry logic
      }

      ws.onclose = () => {
        if (destroyed || sessionEndedRef.current) return
        setAudioState('idle')
        if (retryCount < MAX_RETRIES) {
          // Exponential backoff: 1s, 2s, 4s, 8s, 16s
          const delay = Math.min(1000 * Math.pow(2, retryCount), 16000)
          retryCount++
          setError(`Reconnecting… (attempt ${retryCount}/${MAX_RETRIES})`)
          setTimeout(connect, delay)
        } else {
          setError('Connection lost. Please refresh the page.')
        }
      }
    }

    connect()
    return () => {
      destroyed = true
      wsRef.current?.close()
    }
  }, [sessionId, token, apiBase]) // eslint-disable-line react-hooks/exhaustive-deps

  const sendText = useCallback((text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'user_message', text }))
    setMessages(prev => [...prev, { role: 'user', text }])
    setHint(null)
    setAudioState('processing')
  }, [])

  const startListening = useCallback(() => {
    const SpeechRecognitionAPI = window.SpeechRecognition ?? window.webkitSpeechRecognition
    if (!SpeechRecognitionAPI) return
    const recognition = new SpeechRecognitionAPI()
    recognitionRef.current = recognition
    recognition.continuous = false
    recognition.interimResults = false
    recognition.onstart = () => {
      setAudioState('listening')
      filler.startTimer()
    }
    recognition.onresult = (event: ISpeechRecognitionEvent) => {
      const text = event.results[0][0].transcript
      filler.cancel()
      sendText(text)
    }
    recognition.onerror = () => { filler.cancel(); setAudioState('idle') }
    recognition.onend = () => { if (audioState === 'listening') setAudioState('idle') }
    recognition.start()
  }, [audioState, filler, sendText])

  const dismissOnboarding = useCallback(() => setShowOnboarding(false), [])

  const endSession = useCallback(() => {
    // Stop any playing audio immediately
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
    recognitionRef.current?.stop()
    // Send graceful end if socket is open; otherwise just close
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end_session' }))
    }
    wsRef.current?.close()
    sessionEndedRef.current = true
    setSessionEnded(true)
    setAudioState('idle')
  }, [])

  if (sessionEnded) {
    return (
      <div className="min-h-screen bg-[#10141a] flex flex-col items-center justify-center p-6 space-y-6">
        {/* Show debrief overlay on top if it arrived */}
        <GradingDebrief debrief={debrief} onDismiss={() => setDebrief(null)} />
        <h2 className="text-2xl font-bold text-[#e8eaed]">Session Complete</h2>
        <CofGates {...cofGates} />
        {!debrief && (
          <p className="text-[#9aa0a6] text-sm">Check your email for results and your certificate if earned.</p>
        )}
        <div className="flex flex-col items-center gap-3 pt-2">
          {seriesId && (
            <a
              href={`/session/new?series=${seriesId}`}
              className="btn-primary-gradient text-[#0a1a1a] text-sm font-semibold px-6 py-2.5 rounded-lg transition-colors"
            >
              Practice Again
            </a>
          )}
          <a
            href="/dashboard"
            className="text-sm text-[#9aa0a6] hover:text-[#e8eaed] transition-colors"
          >
            Back to Dashboard
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#10141a] flex flex-col">
      {showOnboarding && <OnboardingOverlay onDismiss={dismissOnboarding} />}
      <RepHint hint={hint} />
      <GradingDebrief debrief={debrief} onDismiss={() => setDebrief(null)} />

      {/* Header */}
      <div className="bg-[#1c2026] border-b border-white/[0.06] px-4 py-3 space-y-1">
        <div className="flex items-center justify-between">
          {scenarioName && <p className="text-sm font-medium text-[#e8eaed]">{scenarioName}</p>}
          <div className="flex items-center gap-2">
            {isDemo && (
              <span className="text-[10px] font-bold bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded uppercase tracking-wider">
                Demo — AI is the rep
              </span>
            )}
            {!isDemo && (
              <button
                onClick={() => setShowCoach(v => !v)}
                className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider transition-colors ${
                  showCoach
                    ? 'bg-amber-500/10 text-amber-400'
                    : 'bg-white/5 text-[#9aa0a6] hover:bg-amber-500/10 hover:text-amber-400'
                }`}
              >
                Coach {showCoach ? 'ON' : 'OFF'}
              </button>
            )}
          </div>
        </div>
        {!isDemo && <ArcProgress currentStage={arcStage} totalStages={6} />}
        {!isDemo && <CofGates {...cofGates} />}
        {!isDemo && <SpinGates {...spinGates} />}
        {!isDemo && <ChallengerGates {...challengerGates} />}
        {isDemo && (
          <p className="text-[11px] text-[#9aa0a6]">
            Speak Rachel's lines. Watch how the rep responds and why.
          </p>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`max-w-xs ${m.role === 'user' ? 'ml-auto' : ''}`}>
            {/* Role label in demo mode */}
            {isDemo && (
              <p className={`text-[9px] font-bold uppercase tracking-wider mb-0.5 ${
                m.role === 'user' ? 'text-right text-[#2ddbde]' : 'text-amber-400'
              }`}>
                {m.role === 'user' ? 'Rachel (you)' : 'Rep (AI)'}
              </p>
            )}
            <div
              className={`rounded-lg px-4 py-2 text-sm ${
                m.role === 'user'
                  ? 'bg-[#181c22] text-[#e8eaed]'
                  : 'bg-[#1c2026] text-[#e8eaed]'
              }`}
              style={{ border: '1px solid rgba(255,255,255,0.08)' }}
            >
              {m.text}
            </div>
            {/* Coaching note — visible only when coach is toggled on */}
            {m.coachingNote && showCoach && (
              <div className="mt-1 rounded-lg px-3 py-2" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}>
                <p className="text-[9px] font-bold text-amber-400 uppercase tracking-wider mb-0.5 font-mono">Coach</p>
                <p className="text-[11px] text-[#2ddbde] font-mono">{m.coachingNote}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Error */}
      {error && <p className="px-4 text-red-400 text-sm">{error}</p>}

      {/* Controls */}
      <div
        className="bg-[#10141a] p-4 flex flex-col items-center gap-3"
        style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
      >
        <AudioStateDisplay state={audioState} />
        {isDemo && audioState === 'idle' && (
          <p className="text-[11px] text-amber-400 font-medium">Speak as Rachel</p>
        )}
        <button
          onClick={startListening}
          disabled={audioState === 'processing' || audioState === 'speaking'}
          className="relative w-20 h-20 rounded-full btn-primary-gradient disabled:opacity-40 transition-all duration-200 flex items-center justify-center"
          style={{
            boxShadow: audioState === 'listening'
              ? '0 0 0 12px rgba(45,219,222,0.15), 0 0 0 24px rgba(45,219,222,0.06), inset 0 2px 4px rgba(0,0,0,0.3)'
              : 'inset 0 2px 4px rgba(0,0,0,0.3)',
          }}
          aria-label="Start speaking"
        >
          {audioState === 'processing' ? (
            <div className="w-6 h-6 rounded-full border-2 border-[#0a1a1a]/40 border-t-[#0a1a1a] animate-spin" />
          ) : (
            <svg width="22" height="28" viewBox="0 0 22 28" fill="none">
              <rect x="6" y="0" width="10" height="18" rx="5" fill="#0a1a1a"/>
              <path d="M1 14C1 20.075 5.477 25 11 25C16.523 25 21 20.075 21 14" stroke="#0a1a1a" strokeWidth="2" strokeLinecap="round"/>
              <line x1="11" y1="25" x2="11" y2="28" stroke="#0a1a1a" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          )}
        </button>
        <div className="flex items-center gap-4">
          {seriesId && (
            <a
              href={`/session/new?series=${seriesId}${isDemo ? '&mode=demo' : ''}`}
              onClick={() => { if (audioRef.current) { audioRef.current.pause(); audioRef.current = null } wsRef.current?.close() }}
              className="text-xs text-[#9aa0a6] hover:text-[#2ddbde] transition-colors"
            >
              ↺ Restart
            </a>
          )}
          <button
            onClick={endSession}
            className="text-xs text-[#9aa0a6] hover:text-red-400 transition-colors"
            aria-label="End session"
          >
            ✕ End {isDemo ? 'Demo' : 'Session'}
          </button>
        </div>
      </div>
    </div>
  )
}
