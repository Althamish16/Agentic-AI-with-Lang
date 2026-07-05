import { useState } from 'react'
import { ACCENTS } from '../data/days.js'
import DayResult from './DayResult.jsx'
import FlowDiagram from './FlowDiagram.jsx'
import ReportView from './ReportView.jsx'
import { IconBolt } from './Icons.jsx'

export default function DayTab({ day }) {
  const accent = ACCENTS[day.accent]
  const [q, setQ] = useState('')
  const [runs, setRuns] = useState({}) // demoId -> { loading, data }
  const anyNeedsQuestion = day.demos.some((d) => d.needsQuestion)

  async function runDemo(demo) {
    setRuns((prev) => ({ ...prev, [demo.id]: { loading: true, data: null } }))
    try {
      const qs = new URLSearchParams({ demo: demo.id })
      if (demo.needsQuestion && q.trim()) qs.set('question', q.trim())
      const r = await fetch(`/api/lab/${day.n}?${qs.toString()}`)
      const data = await r.json()
      setRuns((prev) => ({ ...prev, [demo.id]: { loading: false, data } }))
    } catch (e) {
      setRuns((prev) => ({ ...prev, [demo.id]: { loading: false, data: { kind: 'error', error: `Backend unreachable on :5000 — is it running? (${e})` } } }))
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* ── Left: explanation + code ── */}
      <div className="space-y-5">
        <div className="flex items-center gap-3">
          <span className={`flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br ${accent.grad} text-white font-bold shadow-lg`}>{day.n}</span>
          <div>
            <h2 className="text-xl font-extrabold text-slate-100">{day.title}</h2>
            <p className={`text-xs ${accent.text}`}>{day.tag}</p>
          </div>
        </div>

        {/* Detailed explanation sections */}
        <div className="glass rounded-2xl p-5 space-y-4">
          {day.explain.map((s, i) => (
            <div key={i} className="animate-fadeInUp">
              <h3 className={`text-sm font-semibold ${accent.text} mb-0.5`}>{s.h}</h3>
              <div className="report text-sm"><ReportView text={s.body} /></div>
            </div>
          ))}
          <div className={`rounded-lg ${accent.bg} ${accent.ring} ring-1 px-3 py-2 text-sm ${accent.text}`}>💡 {day.why}</div>
        </div>

        {/* Flow */}
        <div className="glass rounded-2xl p-5">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">Flow</h3>
          <FlowDiagram steps={day.flow} accent={accent} />
        </div>

        {/* Multiple code snippets */}
        <div className="glass rounded-2xl p-5 space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Code examples</h3>
          {day.snippets.map((sn, i) => (
            <div key={i}>
              <p className="text-xs font-medium text-slate-300 mb-1">{sn.title}</p>
              <pre className="overflow-x-auto rounded-lg bg-black/40 p-3 text-xs text-slate-200 leading-relaxed"><code>{sn.code}</code></pre>
            </div>
          ))}
        </div>

        <div className="text-xs text-slate-400"><span className="font-semibold text-slate-300">Carries over: </span>{day.carriesOver}</div>
      </div>

      {/* ── Right: multiple live demos ── */}
      <div className="space-y-4">
        <div className="glass rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-slate-200">Run it live · {day.demos.length} demos</h3>
          <p className="mt-1 text-[11px] text-slate-500">Each button runs the real code on the backend (live Azure calls).</p>
          {anyNeedsQuestion && (
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Optional question (a sensible default is used if empty)"
              className="w-full mt-3 rounded-lg bg-slate-900/60 border border-white/10 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50"
            />
          )}
        </div>

        {day.demos.map((demo) => {
          const run = runs[demo.id]
          return (
            <div key={demo.id} className="glass rounded-2xl p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h4 className="font-semibold text-slate-100">{demo.label}</h4>
                  <p className="text-xs text-slate-400 mt-0.5">{demo.desc}</p>
                </div>
                <button
                  onClick={() => runDemo(demo)}
                  disabled={run?.loading}
                  className={`shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r ${accent.grad} px-3 py-1.5 text-xs font-semibold text-white shadow disabled:opacity-50 transition`}
                >
                  <IconBolt width={14} height={14} /> {run?.loading ? 'Running…' : 'Run'}
                </button>
              </div>

              {run?.loading && (
                <div className="mt-3 h-2.5 w-1/3 rounded bg-white/10 overflow-hidden relative">
                  <span className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/25 to-transparent" />
                </div>
              )}
              {run?.data && <div className="mt-3"><DayResult data={run.data} accent={accent} /></div>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
