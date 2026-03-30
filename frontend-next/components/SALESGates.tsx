'use client'

export interface SalesGateState {
  start: boolean
  ask_discover: boolean
  ask_dissect: boolean
  ask_develop: boolean
  listen_recap: boolean
  explain_reveal: boolean
  explain_relate: boolean
  secure_what: boolean
  secure_when: boolean
  resistance_empathize: boolean
  resistance_ask: boolean
  resistance_respond: boolean
}

const PHASES: Array<{
  phase: string
  label: string
  gates: Array<{ key: keyof SalesGateState; label: string }>
}> = [
  {
    phase: 'S',
    label: 'S',
    gates: [{ key: 'start', label: 'Start' }],
  },
  {
    phase: 'A',
    label: 'A',
    gates: [
      { key: 'ask_discover', label: 'Discover' },
      { key: 'ask_dissect', label: 'Dissect' },
      { key: 'ask_develop', label: 'Develop' },
    ],
  },
  {
    phase: 'L',
    label: 'L',
    gates: [{ key: 'listen_recap', label: 'Recap' }],
  },
  {
    phase: 'E',
    label: 'E',
    gates: [
      { key: 'explain_reveal', label: 'Reveal' },
      { key: 'explain_relate', label: 'Relate' },
    ],
  },
  {
    phase: 'S2',
    label: 'S',
    gates: [
      { key: 'secure_what', label: 'What' },
      { key: 'secure_when', label: 'When' },
    ],
  },
  {
    phase: 'R',
    label: 'Res.',
    gates: [
      { key: 'resistance_empathize', label: 'Empathize' },
      { key: 'resistance_ask', label: 'Ask' },
      { key: 'resistance_respond', label: 'Respond' },
    ],
  },
]

export function SALESGates(props: SalesGateState) {
  return (
    <div className="flex items-start gap-3 flex-wrap">
      <span className="text-[9px] font-bold text-[#5f6368] uppercase tracking-wider mt-0.5 flex-shrink-0">SALES</span>
      <div className="flex items-start gap-3 flex-wrap flex-1">
        {PHASES.map(({ phase, label, gates }) => (
          <div key={phase} className="flex flex-col gap-0.5">
            <span className="text-[8px] font-bold text-[#5f6368] uppercase tracking-wider text-center">
              {label}
            </span>
            <div className="flex gap-1">
              {gates.map(({ key, label: gateLabel }) => (
                <div
                  key={key}
                  title={gateLabel}
                  className={`flex items-center gap-0.5 text-[10px] font-semibold transition-colors ${
                    props[key] ? 'text-[#2ddbde]' : 'text-[#5f6368]'
                  }`}
                >
                  <span>{props[key] ? '✓' : '○'}</span>
                  <span className="text-[9px]">{gateLabel}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
