interface Props { clinical: boolean; operational: boolean; financial: boolean }
export default function CofGates({ clinical, operational, financial }: Props) {
  const Gate = ({ name, passed }: { name: string; passed: boolean }) => (
    <div data-gate={name.toLowerCase()}
         className={`flex items-center gap-1.5 text-sm ${passed ? 'text-green-500' : 'text-gray-400'}`}>
      <span>{passed ? '✓' : '○'}</span>
      <span className="capitalize">{name}</span>
    </div>
  )
  return (
    <div className="flex gap-4">
      <Gate name="clinical" passed={clinical} />
      <Gate name="operational" passed={operational} />
      <Gate name="financial" passed={financial} />
    </div>
  )
}
