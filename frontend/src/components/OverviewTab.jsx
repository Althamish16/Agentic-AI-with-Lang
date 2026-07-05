import { ACCENTS, DAYS } from '../data/days.js'
import { IconBolt, IconSpark } from './Icons.jsx'

export default function OverviewTab({ onNavigate }) {
  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="glass rounded-2xl p-6 sm:p-8">
        <h1 className="text-2xl sm:text-3xl font-extrabold bg-gradient-to-r from-brand-300 via-fuchsia-300 to-sky-300 bg-clip-text text-transparent">
          One agent, built one layer at a time.
        </h1>
        <p className="mt-2 max-w-2xl text-slate-300">
          Over 7 days we grow a single <strong>Research Assistant</strong> from a one-line chain into a
          self-improving, human-supervised agent. Each day adds one capability — and it all compounds
          into the <span className="text-fuchsia-300 font-medium">Studio</span>.
        </p>

        {/* Kitchen analogy */}
        <div className="mt-5 rounded-xl bg-black/20 border border-white/5 p-4">
          <p className="text-sm text-slate-300">
            🍳 <strong className="text-slate-100">Think of a kitchen.</strong> Days 1–7 each teach one
            station — prep, cooking, tasting, plating. The <strong className="text-slate-100">Studio</strong> is
            the whole kitchen running <em>one order end-to-end</em>: the same code you wrote each day,
            now wired into <strong className="text-slate-100">one agent</strong> that plans → researches →
            writes → double-checks itself → asks you to approve → publishes.
          </p>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <button onClick={() => onNavigate('day1')} className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 transition">
            <IconBolt width={16} height={16} /> Start with Day 1
          </button>
          <button onClick={() => onNavigate('studio')} className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand-500 to-fuchsia-500 px-4 py-2 text-sm font-semibold text-white shadow-lg transition">
            <IconSpark width={16} height={16} /> Open the Studio
          </button>
        </div>
      </div>

      {/* Architecture */}
      <div className="glass rounded-2xl p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400 mb-4">How it runs — 2 processes, 1 agent</h2>
        <div className="flex flex-col sm:flex-row items-stretch gap-3">
          <ArchBox title="Frontend — the face" port=":9000" desc="React + Vite. Shows every step live." />
          <div className="flex items-center justify-center text-slate-500 text-sm">— proxies /api →</div>
          <ArchBox title="Backend — the brain" port=":5000" desc="FastAPI runs the LangGraph agent, streams over SSE." />
        </div>
        <p className="mt-3 text-xs text-slate-500">
          The <strong className="text-slate-400">agent</strong> is one LangGraph graph. You watch its nodes fire in real time.
        </p>
      </div>

      {/* Compounding journey */}
      <div className="glass rounded-2xl p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400 mb-4">The 7-day journey (click any day)</h2>
        <div className="space-y-2">
          {DAYS.map((d) => {
            const a = ACCENTS[d.accent]
            return (
              <button
                key={d.key}
                onClick={() => onNavigate(d.key)}
                className="w-full text-left flex items-center gap-3 rounded-xl border border-white/5 bg-black/10 p-3 hover:bg-white/5 hover:border-white/15 transition"
              >
                <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${a.grad} text-white text-sm font-bold`}>{d.n}</span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-slate-100">{d.title}</span>
                  <span className="block text-xs text-slate-400 truncate">{d.tag}</span>
                </span>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function ArchBox({ title, port, desc }) {
  return (
    <div className="flex-1 rounded-xl border border-white/10 bg-black/20 p-4">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-slate-100">{title}</span>
        <span className="rounded-md bg-white/5 px-2 py-0.5 text-xs font-mono text-slate-300">{port}</span>
      </div>
      <p className="mt-1 text-xs text-slate-400">{desc}</p>
    </div>
  )
}
