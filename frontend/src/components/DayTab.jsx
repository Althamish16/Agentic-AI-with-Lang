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
  const hasSlideDemos = day.demos.some((d) => typeof d.slide === 'number')

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

  // ── Day 1: stacked layout — full-width concept tabs (Slide 1 is the first
  //    tab, showing the deck cover), then the active demo panel, then a
  //    collapsible reference section at the bottom.
  if (hasSlideDemos) {
    return (
      <div className="space-y-6">
        {/* Optional question input, only used by the Lab tab. */}
        {anyNeedsQuestion && (
          <div className="glass rounded-2xl p-4">
            <label className="block text-[11px] font-semibold uppercase tracking-wide text-slate-400 mb-1">
              Optional question (used by the Lab tab)
            </label>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="A sensible default is used if empty"
              className="w-full rounded-lg bg-slate-900/60 border border-white/10 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50"
            />
          </div>
        )}

        <SlideTabs day={day} runs={runs} runDemo={runDemo} accent={accent} />

        <ReferenceCollapsible day={day} accent={accent} />
      </div>
    )
  }

  // ── Days 2–7: original 2-column layout (explanation left, demos right).
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-5">
        <div className="flex items-center gap-3">
          <span className={`flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br ${accent.grad} text-white font-bold shadow-lg`}>{day.n}</span>
          <div>
            <h2 className="text-xl font-extrabold text-slate-100">{day.title}</h2>
            <p className={`text-xs ${accent.text}`}>{day.tag}</p>
          </div>
        </div>

        <div className="glass rounded-2xl p-5 space-y-4">
          {day.explain.map((s, i) => (
            <div key={i} className="animate-fadeInUp">
              <h3 className={`text-sm font-semibold ${accent.text} mb-0.5`}>{s.h}</h3>
              <div className="report text-sm"><ReportView text={s.body} /></div>
            </div>
          ))}
          <div className={`rounded-lg ${accent.bg} ${accent.ring} ring-1 px-3 py-2 text-sm ${accent.text}`}>💡 {day.why}</div>
        </div>

        <div className="glass rounded-2xl p-5">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">Flow</h3>
          <FlowDiagram steps={day.flow} accent={accent} />
        </div>

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

        {renderFlatDemos(day, runs, runDemo, accent)}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// SlideOneCover — the "Slide 1" title card. Sized to ~half the viewport on
// desktop so the deck's cover slide has real presence, then compresses on
// small screens. Concept chips preview the tabs below.
// ─────────────────────────────────────────────────────────────────────────────
function SlideOneCover({ day, accent }) {
  // Split "AI Fundamentals — Chains, Tools & Agents" so the deck's two-line
  // cover typography reads cleanly (superline + main title).
  const [preTitle, mainTitle] = splitTitle(day.title)
  return (
    <div className={`relative overflow-hidden rounded-3xl bg-gradient-to-br ${accent.grad} p-[1px] shadow-2xl`}>
      <div className="relative rounded-3xl bg-slate-950/85 px-6 sm:px-10 py-10 sm:py-12">
        {/* Soft radial glows — no grid squares. */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'radial-gradient(ellipse 60% 50% at 15% 10%, rgba(255,255,255,0.08), transparent 60%),' +
              'radial-gradient(ellipse 50% 60% at 90% 100%, rgba(255,255,255,0.05), transparent 55%)',
          }}
        />

        <div className="relative flex items-center gap-3 mb-6">
          <span className={`flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${accent.grad} text-white font-bold text-lg shadow-lg`}>
            {day.n}
          </span>
          <span className={`text-[11px] font-bold uppercase tracking-[0.2em] ${accent.text}`}>
            Slide 1 · Cover
          </span>
        </div>

        {preTitle && (
          <p className={`relative text-lg sm:text-xl font-semibold ${accent.text} mb-2`}>
            {preTitle}
          </p>
        )}
        <h1 className="relative text-3xl sm:text-4xl lg:text-5xl font-extrabold bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent leading-tight">
          {mainTitle}
        </h1>
        <p className={`relative mt-4 text-base sm:text-lg italic text-slate-300`}>{day.tag}</p>

        {day.why && (
          <p className="relative mt-6 max-w-2xl text-sm sm:text-base text-slate-300">
            💡 {day.why}
          </p>
        )}

        {/* concept chips = the tab labels, previewed */}
        {day.flow && day.flow.length > 0 && (
          <div className="relative mt-6">
            <p className={`text-[11px] font-bold uppercase tracking-wider ${accent.text} mb-2`}>Concepts we'll cover</p>
            <div className="flex flex-wrap gap-2">
              {day.flow.map((step, i) => (
                <span
                  key={i}
                  className={`rounded-full ${accent.bg} ${accent.ring} ring-1 px-3 py-1 text-xs font-medium ${accent.text}`}
                >
                  {step}
                </span>
              ))}
            </div>
          </div>
        )}

        <p className="relative mt-8 text-[11px] text-slate-500">
          Pick a concept tab above to see it demonstrated live against Azure gpt-5.4.
        </p>
      </div>
    </div>
  )
}

// Split "AI Fundamentals — Chains, Tools & Agents" on an em/en dash or hyphen
// into [pre, main]. Falls back to [null, title] when there's no separator.
function splitTitle(title) {
  const m = /^(.+?)\s*[—–-]\s*(.+)$/.exec(title || '')
  return m ? [m[1], m[2]] : [null, title]
}

// ─────────────────────────────────────────────────────────────────────────────
// SlideTabs — full-width tab strip. First tab is the deck's Slide 1 cover;
// then one tab per concept demo (LLM, Prompt, Chain…); a final "Lab" tab holds
// the ResearchPlan coding demos. The active tab's panel renders below.
// ─────────────────────────────────────────────────────────────────────────────
function SlideTabs({ day, runs, runDemo, accent }) {
  const slideDemos = day.demos
    .filter((d) => typeof d.slide === 'number')
    .sort((a, b) => a.slide - b.slide)
  const labDemos = day.demos.filter((d) => typeof d.slide !== 'number')

  const tabs = [
    ...slideDemos.map((d) => ({
      key: d.id,
      kind: 'slide',
      slide: d.slide,
      demo: d,
      label: d.tab || `Slide ${d.slide}`,
    })),
    ...(labDemos.length ? [{ key: '__lab__', kind: 'lab', label: 'Lab' }] : []),
  ]
  const [active, setActive] = useState(tabs[0]?.key)
  const current = tabs.find((t) => t.key === active) || tabs[0]

  return (
    <div className="space-y-4">
      {/* Full-width tab strip (not sticky — keeps the active panel fully visible). */}
      <div className="glass rounded-2xl p-2 sm:p-3">
        <div className="flex items-center gap-1.5 overflow-x-auto scroll-smooth">
          {tabs.map((t) => {
            const isActive = t.key === current?.key
            const isLab = t.kind === 'lab'
            const title =
              t.kind === 'slide' ? t.demo.label :
              'Original coding lab (ResearchPlan)'
            return (
              <button
                key={t.key}
                onClick={() => setActive(t.key)}
                title={title}
                className={
                  'group shrink-0 h-10 px-3 sm:px-4 rounded-xl text-xs sm:text-sm font-semibold transition ' +
                  (isActive
                    ? `bg-gradient-to-r ${accent.grad} text-white shadow-lg`
                    : 'bg-white/5 text-slate-300 hover:bg-white/10 hover:text-slate-100')
                }
              >
                <span className="flex items-center gap-1.5">
                  <span className="whitespace-nowrap">{t.label}</span>
                  {isLab && <span className="text-[10px] opacity-70">· 3</span>}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Active-tab panel */}
      {current?.kind === 'slide' ? (
        <DemoCard
          key={current.demo.id}
          demo={current.demo}
          run={runs[current.demo.id]}
          onRun={() => runDemo(current.demo)}
          accent={accent}
        />
      ) : (
        <div className="space-y-3">
          <div className="glass rounded-2xl p-4">
            <h3 className={`text-sm font-bold ${accent.text}`}>Coding lab · ResearchPlan pipeline</h3>
            <p className="mt-1 text-[11px] text-slate-500">
              The original Day-1 coding lab — a prompt + Pydantic-parser chain that later days reuse.
            </p>
          </div>
          {labDemos.map((demo) => (
            <DemoCard
              key={demo.id}
              demo={demo}
              run={runs[demo.id]}
              onRun={() => runDemo(demo)}
              accent={accent}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// ReferenceCollapsible — the deep "explain + code snippets + flow" content,
// tucked under a click so Day 1's UI stays focused on running the slide demos.
// ─────────────────────────────────────────────────────────────────────────────
function ReferenceCollapsible({ day, accent }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="glass rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-white/5 transition"
      >
        <div className="flex items-center gap-3">
          <span className={`text-[11px] font-bold uppercase tracking-wider ${accent.text}`}>Reference</span>
          <span className="text-sm text-slate-300">Deep dive · explanation, code snippets & flow</span>
        </div>
        <span className={`transition-transform ${open ? 'rotate-180' : ''} text-slate-400`}>▾</span>
      </button>

      {open && (
        <div className="border-t border-white/5 p-5 space-y-6 animate-fadeInUp">
          <div className="space-y-4">
            {day.explain.map((s, i) => (
              <div key={i}>
                <h3 className={`text-sm font-semibold ${accent.text} mb-0.5`}>{s.h}</h3>
                <div className="report text-sm"><ReportView text={s.body} /></div>
              </div>
            ))}
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">Flow</h3>
            <FlowDiagram steps={day.flow} accent={accent} />
          </div>

          <div className="space-y-4">
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
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Legacy flat list (Days 2–7). Sections preserved for future use.
// ─────────────────────────────────────────────────────────────────────────────
function renderFlatDemos(day, runs, runDemo, accent) {
  if (!day.sections || day.sections.length === 0) {
    return day.demos.map((demo) => (
      <DemoCard key={demo.id} demo={demo} run={runs[demo.id]} onRun={() => runDemo(demo)} accent={accent} />
    ))
  }
  return day.sections.map((sec) => {
    const items = day.demos.filter((d) => d.section === sec.id)
    if (items.length === 0) return null
    return (
      <div key={sec.id} className="space-y-3">
        <div className="flex items-baseline justify-between pt-2">
          <h3 className={`text-xs font-bold uppercase tracking-wider ${accent.text}`}>{sec.label}</h3>
          <span className="text-[10px] text-slate-500">{items.length} demo{items.length === 1 ? '' : 's'}</span>
        </div>
        {sec.desc && <p className="text-[11px] text-slate-500 -mt-2">{sec.desc}</p>}
        {items.map((demo) => (
          <DemoCard key={demo.id} demo={demo} run={runs[demo.id]} onRun={() => runDemo(demo)} accent={accent} />
        ))}
      </div>
    )
  })
}

function DemoCard({ demo, run, onRun, accent }) {
  return (
    <div className="glass rounded-2xl p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="font-semibold text-slate-100">{demo.label}</h4>
          <p className="text-xs text-slate-400 mt-0.5">{demo.desc}</p>
        </div>
        <button
          onClick={onRun}
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
}
