'use client'

interface SpinGateState {
  situation: boolean
  problem: boolean
  implication: boolean
  need_payoff: boolean
}

interface ChallengerGateState {
  teach: boolean
  tailor: boolean
  take_control: boolean
}

const SPIN_LABELS: { key: keyof SpinGateState; label: string }[] = [
  { key: 'situation',   label: 'S' },
  { key: 'problem',     label: 'P' },
  { key: 'implication', label: 'I' },
  { key: 'need_payoff', label: 'N' },
]

const CHALLENGER_LABELS: { key: keyof ChallengerGateState; label: string }[] = [
  { key: 'teach',       label: 'Teach' },
  { key: 'tailor',      label: 'Tailor' },
  { key: 'take_control', label: 'Control' },
]

export function SpinGates(props: SpinGateState) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-[9px] font-bold text-[#5f6368] uppercase tracking-wider">SPIN</span>
      <div className="flex gap-2">
        {SPIN_LABELS.map(({ key, label }) => (
          <div
            key={key}
            title={key.replace('_', '-')}
            className={`flex items-center gap-1 text-xs font-semibold transition-colors ${
              props[key] ? 'text-[#2ddbde]' : 'text-[#5f6368]'
            }`}
          >
            <span>{props[key] ? '✓' : '○'}</span>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function ChallengerGates(props: ChallengerGateState) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-[9px] font-bold text-[#5f6368] uppercase tracking-wider">CHG</span>
      <div className="flex gap-2">
        {CHALLENGER_LABELS.map(({ key, label }) => (
          <div
            key={key}
            title={key.replace('_', '-')}
            className={`flex items-center gap-1 text-xs font-semibold transition-colors ${
              props[key] ? 'text-[#2ddbde]' : 'text-[#5f6368]'
            }`}
          >
            <span>{props[key] ? '✓' : '○'}</span>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
