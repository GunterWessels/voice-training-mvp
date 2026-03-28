interface Props { clinical: boolean; operational: boolean; financial: boolean }

type GateStatus = 'passed' | 'missed' | 'pending'

export default function CofGates({ clinical, operational, financial }: Props) {
  const gates: { name: string; status: GateStatus }[] = [
    { name: 'CLINICAL',    status: clinical    === true ? 'passed' : clinical    === false ? 'missed' : 'pending' },
    { name: 'OPERATIONAL', status: operational === true ? 'passed' : operational === false ? 'missed' : 'pending' },
    { name: 'FINANCIAL',   status: financial   === true ? 'passed' : financial   === false ? 'missed' : 'pending' },
  ]

  const leftBorderColor: Record<GateStatus, string> = {
    passed:  '#2ddbde',
    missed:  '#5f6368',
    pending: 'transparent',
  }

  const labelColor: Record<GateStatus, string> = {
    passed:  'text-[#2ddbde]',
    missed:  'text-[#5f6368]',
    pending: 'text-[#9aa0a6]',
  }

  return (
    <div className="flex gap-2">
      {gates.map(({ name, status }) => (
        <div
          key={name}
          data-gate={name.toLowerCase()}
          className="bg-[#181c22] rounded-lg p-3"
          style={{
            borderTop:    '1px solid rgba(255,255,255,0.08)',
            borderRight:  '1px solid rgba(255,255,255,0.08)',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            borderLeft:   status === 'pending'
              ? '1px solid rgba(255,255,255,0.08)'
              : `2px solid ${leftBorderColor[status]}`,
          }}
        >
          <span className={`text-[10px] tracking-widest uppercase ${labelColor[status]}`}>
            {name}
          </span>
        </div>
      ))}
    </div>
  )
}
