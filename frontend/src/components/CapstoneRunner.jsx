import { useEffect, useRef, useState } from 'react'
import ApprovalPanel from './ApprovalPanel.jsx'
import ReportView from './ReportView.jsx'
import {
  IconApprove, IconBolt, IconDoc, IconPlan, IconPublish,
  IconReflect, IconResearch, IconSpark, IconWrite,
} from './Icons.jsx'

// ─────────────────────────────────────────────────────────────────────────────
// CapstoneRunner — the SSE-driven Day 7 capstone experience.
//
// Streams /api/run for a question, renders each node update live, PAUSES on
// approval_required and shows the human-in-the-loop panel with real Approve
// / Request-changes buttons, then resumes via /api/resume.
//
// Used by:
//   • StudioTab             — top-level "Studio" tab
//   • Day 7 · M6 · Full run — inline inside the Day 7 module
//
// Props:
//   initialQuestion   optional string, prefilled in the input
//   autoRun           when true, kicks off the run on mount using initialQuestion
//   showQuestionBar   when false, hides the question input (useful when the
//                     enclosing page already has its own question box)
//   threadPrefix      string prepended to the generated thread_id (namespacing)
// ─────────────────────────────────────────────────────────────────────────────

const STAGES = [
  { key: 'plan',     title: 'Plan',     desc: 'Decompose the question',                           Icon: IconPlan },
  { key: 'research', title: 'Research', desc: 'Retrieve + answer each sub-question (RAG)',        Icon: IconResearch },
  { key: 'write',    title: 'Write',    desc: 'Compose the report',                               Icon: IconWrite },
  { key: 'reflect',  title: 'Reflect',  desc: 'Self-critique the draft',                          Icon: IconReflect },
  { key: 'approve',  title: 'Approve',  desc: 'Human-in-the-loop gate — YOU approve here',        Icon: IconApprove },
  { key: 'publish',  title: 'Publish',  desc: 'Finalize the report',                              Icon: IconPublish },
]

const EXAMPLES = [
  'Should I use similarity or MMR retrieval?',
  'How do agents use memory and tools?',
  'What is chunking and why does it matter in RAG?',
]

const freshStages = () => ({
  plan:     { status: 'idle' },
  research: { status: 'idle', items: [] },
  write:    { status: 'idle' },
  reflect:  { status: 'idle' },
  approve:  { status: 'idle' },
  publish:  { status: 'idle' },
})

function applyEvent(prev, ev) {
  const s = { ...prev, research: { ...prev.research, items: [...prev.research.items] } }
  if (ev.event === 'start') s.plan = { status: 'active' }
  else if (ev.event === 'node') {
    if (ev.node === 'plan') { s.plan = { status: 'done', topic: ev.topic, plan: ev.plan || [] }; s.research.status = 'active' }
    else if (ev.node === 'research') { s.research.status = 'active'; s.research.items.push({ q: ev.sub_question, sources: ev.sources || [], cursor: ev.cursor }) }
    else if (ev.node === 'write') { s.research.status = 'done'; s.write = { status: 'done', revision: ev.revision, draft: ev.draft }; s.reflect.status = 'active' }
    else if (ev.node === 'reflect') { s.reflect = { status: 'done', verdict: ev.verdict, critique: ev.critique }; if (ev.verdict === 'REVISE') s.write.status = 'active'; else s.approve.status = 'active' }
    else if (ev.node === 'human_approval') { s.approve.status = 'active' }
    else if (ev.node === 'publish') { s.publish = { status: 'done', final: ev.final }; s.approve.status = 'done' }
  }
  else if (ev.event === 'approval_required') s.approve.status = 'active'
  else if (ev.event === 'resumed') s.approve.status = 'done'
  else if (ev.event === 'final') { s.publish = { status: 'done', final: ev.final }; s.approve.status = 'done' }
  return s
}

const STATUS_STYLES = {
  idle:   'border-white/10 text-slate-500',
  active: 'border-brand-400 text-brand-200 animate-pulseRing bg-brand-500/10',
  done:   'border-emerald-400/60 text-emerald-300 bg-emerald-500/10',
}

function StageRow({ def, state, last }) {
  const status = state?.status || 'idle'
  const { Icon } = def
  return (
    <div className="relative flex gap-4">
      {!last && <span className="absolute left-[19px] top-11 h-[calc(100%-1rem)] w-px bg-white/10" />}
      <div className={`z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${STATUS_STYLES[status]} transition-all`}>
        <Icon width={18} height={18} />
      </div>
      <div className={`pb-6 flex-1 ${status === 'idle' ? 'opacity-50' : ''}`}>
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-slate-100">{def.title}</h3>
          {status === 'active' && <span className="text-[10px] uppercase tracking-wide text-brand-300">working…</span>}
          {status === 'done' && <span className="text-[10px] uppercase tracking-wide text-emerald-400">done</span>}
        </div>
        <p className="text-xs text-slate-400">{def.desc}</p>

        {def.key === 'plan' && state?.plan && (
          <div className="mt-2 animate-fadeInUp">
            {state.topic && <p className="text-xs text-slate-300 italic mb-1">“{state.topic}”</p>}
            <ol className="space-y-1">
              {state.plan.map((q, i) => (
                <li key={i} className="text-xs text-slate-300 flex gap-2"><span className="text-brand-400 font-semibold">{i + 1}.</span> {q}</li>
              ))}
            </ol>
          </div>
        )}

        {def.key === 'research' && state?.items?.length > 0 && (
          <div className="mt-2 space-y-2 animate-fadeInUp">
            {state.items.map((it, i) => (
              <div key={i} className="rounded-lg bg-slate-800/40 p-2">
                <p className="text-xs text-slate-300 line-clamp-2">{it.q}</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {(it.sources || []).map((src, j) => (
                    <span key={j} className="inline-flex items-center gap-1 rounded-md bg-brand-500/15 px-1.5 py-0.5 text-[10px] text-brand-200"><IconDoc width={10} height={10} /> {src}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {def.key === 'write' && state?.revision && <p className="mt-1 text-xs text-slate-400">draft ready · revision #{state.revision}</p>}
        {def.key === 'reflect' && state?.verdict && (
          <span className={`mt-1 inline-block rounded-md px-2 py-0.5 text-[11px] font-semibold ${state.verdict === 'PASS' ? 'bg-emerald-500/15 text-emerald-300' : 'bg-amber-500/15 text-amber-300'}`}>verdict: {state.verdict}</span>
        )}
      </div>
    </div>
  )
}

export default function CapstoneRunner({
  initialQuestion = '',
  autoRun = false,
  showQuestionBar = true,
  threadPrefix = 'studio',
}) {
  const [question, setQuestion] = useState(initialQuestion)
  const [stages, setStages] = useState(freshStages)
  const [phase, setPhase] = useState('idle')
  const [approval, setApproval] = useState(null)
  const [finalReport, setFinalReport] = useState(null)
  const [error, setError] = useState(null)
  const esRef = useRef(null)
  const threadRef = useRef(threadPrefix)
  const autoRunFiredRef = useRef(false)

  function openStream(path) {
    esRef.current?.close()
    const es = new EventSource(path)
    esRef.current = es
    es.onmessage = (e) => {
      let ev
      try { ev = JSON.parse(e.data) } catch { return }
      setStages((prev) => applyEvent(prev, ev))
      if (ev.event === 'approval_required') { setApproval(ev); setPhase('awaiting_approval') }
      else if (ev.event === 'final') { setFinalReport(ev.final); setApproval(null); setPhase('done') }
      else if (ev.event === 'error') { setError(ev.message); setPhase('error') }
      else if (ev.event === 'done') es.close()
    }
    es.onerror = () => es.close()
  }

  function run(q) {
    const query = (q ?? question).trim()
    if (!query || phase === 'running' || phase === 'finalizing') return
    setQuestion(query)
    setStages(freshStages())
    setApproval(null)
    setFinalReport(null)
    setError(null)
    setPhase('running')
    threadRef.current = `${threadPrefix}-${Date.now()}`
    openStream(`/api/run?question=${encodeURIComponent(query)}&thread_id=${threadRef.current}`)
  }

  function decide(approved, feedback = '') {
    setPhase('finalizing')
    setApproval(null)
    openStream(`/api/resume?thread_id=${threadRef.current}&approved=${approved}&feedback=${encodeURIComponent(feedback)}`)
  }

  // Auto-fire once on mount when requested (used by Day 7 · M6).
  // React 18 StrictMode double-invokes effects in dev: the first invocation
  // opens an EventSource, then its cleanup closes it immediately. We defer
  // the actual `run()` behind a cancellable timeout so only the surviving
  // mount opens (and keeps) the stream.
  useEffect(() => {
    if (!autoRun || !initialQuestion) {
      return () => esRef.current?.close()
    }
    const t = setTimeout(() => {
      if (autoRunFiredRef.current) return
      autoRunFiredRef.current = true
      run(initialQuestion)
    }, 50)
    return () => {
      clearTimeout(t)
      // Only close the stream on the *real* unmount — i.e. after we've
      // actually started a run. StrictMode's transient cleanup runs before
      // any run has fired, so this is a no-op there.
      if (autoRunFiredRef.current) esRef.current?.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const busy = phase === 'running' || phase === 'finalizing'

  return (
    <div className="space-y-6">
      {/* Question bar */}
      {showQuestionBar && (
        <div>
          <div className="glass rounded-2xl p-2 flex items-center gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && run()}
              placeholder="Ask a research question…"
              className="flex-1 bg-transparent px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none"
            />
            <button onClick={() => run()} disabled={busy || !question.trim()} className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-3 font-semibold text-white hover:bg-brand-500 disabled:opacity-40 transition">
              <IconBolt width={16} height={16} /> {busy ? 'Running…' : 'Run'}
            </button>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button key={ex} onClick={() => run(ex)} disabled={busy} className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300 hover:border-brand-400/60 hover:text-brand-200 disabled:opacity-40 transition">{ex}</button>
            ))}
          </div>
        </div>
      )}

      {/* Grid */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <div className="glass rounded-2xl p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">Agent trace (live)</h2>
          {STAGES.map((def, i) => <StageRow key={def.key} def={def} state={stages[def.key]} last={i === STAGES.length - 1} />)}
        </div>

        <div className="space-y-6">
          {error && (
            <div className="glass rounded-2xl p-5 ring-1 ring-red-500/40">
              <h3 className="font-semibold text-red-300">Something went wrong</h3>
              <p className="mt-1 text-sm text-slate-300">{error}</p>
              <p className="mt-2 text-xs text-slate-500">Is the backend running on :5000? Try <code>python backend/app.py</code>.</p>
            </div>
          )}

          {phase === 'awaiting_approval' && approval && (
            <ApprovalPanel payload={approval} busy={false} onApprove={() => decide(true)} onReject={(fb) => decide(false, fb)} />
          )}

          {finalReport ? (
            <div className="glass rounded-2xl p-6 animate-fadeInUp">
              <div className="mb-3 flex items-center gap-2 text-emerald-300"><IconPublish width={18} height={18} /><h2 className="font-semibold">Published report</h2></div>
              <ReportView text={finalReport} />
            </div>
          ) : (
            phase === 'idle' && (
              <div className="glass rounded-2xl p-8 text-center text-slate-400">
                <IconSpark width={28} height={28} className="mx-auto mb-3 text-brand-300" />
                <p className="font-medium text-slate-200">Ask a question to begin</p>
                <p className="mt-1 text-sm">The agent plans, researches your docs, writes, critiques itself, and pauses for your approval before publishing.</p>
              </div>
            )
          )}

          {busy && !finalReport && phase !== 'awaiting_approval' && (
            <div className="glass rounded-2xl p-6">
              <div className="h-3 w-1/3 rounded bg-white/10 mb-3 overflow-hidden relative">
                <span className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent" />
              </div>
              <p className="text-sm text-slate-400">The agent is working… watch the trace on the left.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
