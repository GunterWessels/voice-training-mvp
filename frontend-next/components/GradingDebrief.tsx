'use client'

interface Dimension { id: string; score: number; narrative: string }
interface Debrief {
  overall_score: number
  dimensions: Dimension[]
  top_strength: string
  top_improvement: string
  debrief_audio: boolean
}
interface Props { debrief: Debrief | null; onDismiss: () => void }

const DIM_LABELS: Record<string, string> = {
  cof_coverage: 'COF Coverage',
  discovery_quality: 'Discovery Quality',
  argument_coherence: 'Argument Coherence',
  objection_handling: 'Objection Handling',
  spin_questioning: 'SPIN Questioning',
  challenger_insight: 'Challenger Insight',
}

export function GradingDebrief({ debrief, onDismiss }: Props) {
  if (!debrief) return null
  return (
    <div className="fixed inset-0 bg-black/70 flex items-end justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg p-6 space-y-5">
        <div className="flex justify-between items-start">
          <div>
            <p className="text-slate-500 text-xs uppercase tracking-wider mb-1">Session Score</p>
            <p className="text-4xl font-bold text-white">
              {debrief.overall_score}
              <span className="text-xl text-slate-500">/100</span>
            </p>
          </div>
          <button onClick={onDismiss} className="text-slate-500 hover:text-white text-xl">
            &times;
          </button>
        </div>

        <div className="space-y-3">
          {debrief.dimensions.map(dim => (
            <div key={dim.id} className="bg-slate-800 rounded-lg p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-slate-200">
                  {DIM_LABELS[dim.id] || dim.id}
                </span>
                <span
                  className={`text-sm font-bold ${
                    dim.score >= 80
                      ? 'text-emerald-400'
                      : dim.score >= 60
                      ? 'text-amber-400'
                      : 'text-red-400'
                  }`}
                >
                  {dim.score}
                </span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-1.5 mb-2">
                <div
                  className={`h-1.5 rounded-full transition-all ${
                    dim.score >= 80
                      ? 'bg-emerald-500'
                      : dim.score >= 60
                      ? 'bg-amber-500'
                      : 'bg-red-500'
                  }`}
                  style={{ width: `${dim.score}%` }}
                />
              </div>
              <p className="text-xs text-slate-400">{dim.narrative}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
            <p className="text-xs text-emerald-400 font-medium mb-1">Top Strength</p>
            <p className="text-xs text-slate-300">{debrief.top_strength}</p>
          </div>
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
            <p className="text-xs text-amber-400 font-medium mb-1">Top Improvement</p>
            <p className="text-xs text-slate-300">{debrief.top_improvement}</p>
          </div>
        </div>

        <button
          onClick={onDismiss}
          className="w-full bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium py-2.5 rounded-lg transition-colors"
        >
          Done
        </button>
      </div>
    </div>
  )
}
