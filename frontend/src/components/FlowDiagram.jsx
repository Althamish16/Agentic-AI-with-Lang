// An animated left-to-right flow of steps (the day's pipeline / graph shape).
export default function FlowDiagram({ steps, accent }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {steps.map((s, i) => (
        <div key={i} className="flex items-center gap-2 animate-fadeInUp" style={{ animationDelay: `${i * 80}ms` }}>
          <span className={`rounded-lg border ${accent.ring} ${accent.bg} px-3 py-1.5 text-xs font-medium text-slate-100`}>
            {s}
          </span>
          {i < steps.length - 1 && <span className="text-slate-500">→</span>}
        </div>
      ))}
    </div>
  )
}
