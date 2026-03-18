interface Props { currentStage: number; totalStages: number }
export default function ArcProgress({ currentStage, totalStages }: Props) {
  return (
    <div className="flex gap-2 justify-center py-3">
      {Array.from({ length: totalStages }, (_, i) => {
        const stage = i + 1
        const isActive = stage === currentStage
        const isPast = stage < currentStage
        return (
          <span
            key={stage}
            role="presentation"
            className={`w-2.5 h-2.5 rounded-full transition-all ${
              isActive ? 'bg-blue-500 animate-pulse scale-125' :
              isPast   ? 'bg-blue-300' : 'bg-gray-300'
            }`}
          />
        )
      })}
    </div>
  )
}
