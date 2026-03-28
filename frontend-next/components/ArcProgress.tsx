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
            className={
              isActive
                ? 'w-2.5 h-2.5 rounded-full bg-[#2ddbde] shadow-[0_0_8px_rgba(45,219,222,0.6)] animate-pulse'
                : isPast
                ? 'w-2 h-2 rounded-full bg-[#2ddbde] opacity-60'
                : 'w-2 h-2 rounded-full bg-[#31353c]'
            }
          />
        )
      })}
    </div>
  )
}
