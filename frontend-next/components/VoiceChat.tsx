'use client'
import { useEffect, useRef, useState, useCallback } from 'react'
import ArcProgress from './ArcProgress'
import CofGates from './CofGates'
import { useFillerAudio } from './FillerAudio'
import OnboardingOverlay from './OnboardingOverlay'

type AudioState = 'idle' | 'listening' | 'processing' | 'speaking'

interface CofGateState { clinical: boolean; operational: boolean; financial: boolean }

interface Message { role: 'user' | 'ai'; text: string }

interface Props {
  sessionId: string
  token: string
  apiBase: string
}

export default function VoiceChat({ sessionId, token, apiBase }: Props) {
  const wsRef = useRef<WebSocket | null>(null)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const [audioState, setAudioState] = useState<AudioState>('idle')
  const [messages, setMessages] = useState<Message[]>([])
  const [arcStage, setArcStage] = useState(0)
  const [cofGates, setCofGates] = useState<CofGateState>({ clinical: false, operational: false, financial: false })
  const [personaId, setPersonaId] = useState<string>('')
  const [scenarioName, setScenarioName] = useState('')
  const [sessionEnded, setSessionEnded] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const filler = useFillerAudio({ personaId: personaId || 'default' })

  // Connect to WebSocket
  useEffect(() => {
    const wsBase = apiBase.replace(/^http/, 'ws')
    const ws = new WebSocket(`${wsBase}/ws/${sessionId}?token=${token}`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      let msg: Record<string, unknown>
      try { msg = JSON.parse(event.data) } catch { return }

      if (msg.type === 'ready') {
        setPersonaId(msg.persona_id as string)
        setScenarioName(msg.scenario_name as string)
      }

      if (msg.type === 'ai_message') {
        filler.cancel()
        setMessages(prev => [...prev, { role: 'ai', text: msg.text as string }])
        if (msg.cof_gates) setCofGates(msg.cof_gates as CofGateState)
        if (typeof msg.arc_stage === 'number') setArcStage(msg.arc_stage)

        // Play audio
        if (msg.audio_b64) {
          setAudioState('speaking')
          const audio = new Audio(`data:audio/mp3;base64,${msg.audio_b64}`)
          audio.onended = () => setAudioState('idle')
          audio.play().catch(() => setAudioState('idle'))
        } else {
          setAudioState('idle')
        }

        if (msg.session_end) setSessionEnded(true)
      }

      if (msg.type === 'error') {
        setError(msg.message as string)
        setAudioState('idle')
      }
    }

    ws.onerror = () => setError('Connection error. Please refresh.')
    ws.onclose = () => { if (!sessionEnded) setAudioState('idle') }

    return () => ws.close()
  }, [sessionId, token, apiBase]) // eslint-disable-line react-hooks/exhaustive-deps

  const sendText = useCallback((text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'user_message', text }))
    setMessages(prev => [...prev, { role: 'user', text }])
    setAudioState('processing')
  }, [])

  const startListening = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || (window as unknown as { webkitSpeechRecognition: typeof SpeechRecognition }).webkitSpeechRecognition
    if (!SpeechRecognition) return
    const recognition = new SpeechRecognition()
    recognitionRef.current = recognition
    recognition.continuous = false
    recognition.interimResults = false
    recognition.onstart = () => {
      setAudioState('listening')
      filler.startTimer()
    }
    recognition.onresult = (event) => {
      const text = event.results[0][0].transcript
      filler.cancel()
      sendText(text)
    }
    recognition.onerror = () => { filler.cancel(); setAudioState('idle') }
    recognition.onend = () => { if (audioState === 'listening') setAudioState('idle') }
    recognition.start()
  }, [audioState, filler, sendText])

  if (sessionEnded) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Session Complete</h2>
        <CofGates {...cofGates} />
        <p className="text-gray-500 text-sm">Check your email for results and your certificate if earned.</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {showOnboarding && <OnboardingOverlay onDismiss={() => setShowOnboarding(false)} />}

      {/* Header */}
      <div className="bg-white border-b px-4 py-3 space-y-1">
        {scenarioName && <p className="text-sm font-medium text-gray-700">{scenarioName}</p>}
        <ArcProgress currentStage={arcStage} totalStages={6} />
        <CofGates {...cofGates} />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`max-w-xs rounded-lg px-4 py-2 text-sm ${
            m.role === 'user' ? 'ml-auto bg-blue-600 text-white' : 'bg-white border text-gray-800'
          }`}>
            {m.text}
          </div>
        ))}
      </div>

      {/* Error */}
      {error && <p className="px-4 text-red-600 text-sm">{error}</p>}

      {/* Controls */}
      <div className="bg-white border-t p-4 flex flex-col items-center gap-3">
        <p className="text-xs text-gray-500 capitalize">{audioState === 'idle' ? 'Tap to speak' : audioState + '…'}</p>
        <button
          onClick={startListening}
          disabled={audioState !== 'idle'}
          className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl transition-all ${
            audioState === 'idle' ? 'bg-blue-600 hover:bg-blue-700 text-white' :
            audioState === 'listening' ? 'bg-teal-500 text-white animate-pulse' :
            'bg-gray-200 text-gray-400'
          }`}
          aria-label="Start speaking"
        >
          🎤
        </button>
      </div>
    </div>
  )
}
