import ReportView from './ReportView.jsx'
import { IconDoc } from './Icons.jsx'

// Renders a demo result by its `kind`. Reusable across days.
export default function DayResult({ data, accent }) {
  if (!data) return null
  if (data.kind === 'error' || data.error) {
    return <div className="rounded-xl bg-red-500/10 ring-1 ring-red-500/40 p-4 text-sm text-red-200">{data.error || 'Unknown error'}</div>
  }

  const Src = ({ children }) => (
    <span className={`inline-flex items-center gap-1 rounded-md ${accent.bg} px-1.5 py-0.5 text-[11px] ${accent.text}`}>
      <IconDoc width={10} height={10} /> {children}
    </span>
  )

  switch (data.kind) {
    case 'plan':
      return (
        <Panel title="Structured plan (validated JSON)">
          <p className="text-sm italic text-slate-300 mb-2">“{data.topic}”</p>
          <ol className="space-y-1">
            {data.sub_questions.map((q, i) => (
              <li key={i} className="text-sm text-slate-200 flex gap-2"><span className={`font-bold ${accent.text}`}>{i + 1}.</span> {q}</li>
            ))}
          </ol>
        </Panel>
      )

    case 'raw_vs_parsed':
      return (
        <div className="space-y-3">
          <Panel title="❌ Raw LLM — free text (hard to use)">
            <p className="text-sm text-slate-300 whitespace-pre-wrap">{data.raw}</p>
          </Panel>
          <Panel title="✅ Parsed chain — typed JSON (feeds the next step)">
            <p className="text-sm italic text-slate-300 mb-1">“{data.parsed.topic}”</p>
            <ol className="space-y-1">{data.parsed.sub_questions.map((q, i) => <li key={i} className="text-sm text-slate-200 flex gap-2"><span className={`font-bold ${accent.text}`}>{i + 1}.</span> {q}</li>)}</ol>
          </Panel>
        </div>
      )

    case 'prompt_preview':
      return (
        <Panel title="The exact prompt sent to the model">
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-black/40 p-3 text-xs text-slate-200">{data.prompt}</pre>
        </Panel>
      )

    case 'compare':
      return (
        <Panel title="Retrieval — two strategies">
          <div className="space-y-2 text-sm">
            <div>{data.label_a}:<div className="flex flex-wrap gap-1 mt-1">{data.sources_a.map((s) => <Src key={s}>{s}</Src>)}</div></div>
            <div>{data.label_b}:<div className="flex flex-wrap gap-1 mt-1">{data.sources_b.map((s) => <Src key={s}>{s}</Src>)}</div></div>
          </div>
        </Panel>
      )

    case 'answer':
      return (
        <div className="space-y-3">
          {data.heading && <p className={`text-sm ${accent.text}`}>{data.heading}</p>}
          <Panel title="Answer"><ReportView text={data.answer} /><div className="mt-2 flex flex-wrap gap-1">{data.sources.map((s) => <Src key={s}>{s}</Src>)}</div></Panel>
        </div>
      )

    case 'chunks':
      return (
        <Panel title="Chunking — size changes the number of chunks">
          <table className="w-full text-sm mb-3">
            <thead><tr className="text-slate-400 text-xs"><th className="text-left py-1">chunk size</th><th className="text-left">overlap</th><th className="text-left"># chunks</th></tr></thead>
            <tbody>{data.variants.map((v) => <tr key={v.size} className="text-slate-200"><td className="py-0.5">{v.size}</td><td>{v.overlap}</td><td className={accent.text}>{v.count}</td></tr>)}</tbody>
          </table>
          <p className="text-xs text-slate-400 mb-1">sample chunk (size 800):</p>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-black/40 p-3 text-xs text-slate-300">{data.sample}…</pre>
        </Panel>
      )

    case 'retrieved':
      return (
        <Panel title="Top-k retrieved chunks (lower score = closer)">
          <div className="space-y-2">
            {data.items.map((it, i) => (
              <div key={i} className="rounded-lg bg-black/20 p-2">
                <div className="flex items-center justify-between text-xs mb-1"><Src>{it.source}</Src><span className="text-slate-400">score {it.score}</span></div>
                <p className="text-xs text-slate-300">{it.preview}…</p>
              </div>
            ))}
          </div>
        </Panel>
      )

    case 'trace':
      return (
        <div className="space-y-3">
          <Trace trace={data.trace} accent={accent} />
          {data.critique && <Panel title="Self-critique (reflection)"><p className="text-sm text-slate-300">{data.critique.slice(0, 500)}{data.critique.length > 500 ? '…' : ''}</p></Panel>}
          {data.final && <Panel title="Final report"><ReportView text={data.final} /></Panel>}
        </div>
      )

    case 'tools':
      return (
        <div className="space-y-3">
          <Panel title="Tool calls the agent chose">
            <div className="flex flex-wrap gap-2">
              {data.tool_calls.length ? data.tool_calls.map((t, i) => (
                <span key={i} className={`rounded-md ${accent.bg} px-2 py-1 text-xs ${accent.text} font-mono`}>{t.name}({Object.values(t.args)[0]?.toString().slice(0, 28)}…)</span>
              )) : <span className="text-sm text-slate-400">answered directly (no tools)</span>}
            </div>
          </Panel>
          <Panel title="Final answer"><ReportView text={data.final} /></Panel>
        </div>
      )

    case 'routing':
      return (
        <Panel title="Tool selection — the model picks per question">
          <div className="space-y-2">
            {data.cases.map((c, i) => (
              <div key={i} className="rounded-lg bg-black/20 p-2">
                <p className="text-sm text-slate-200">{c.question}</p>
                <div className="mt-1 flex flex-wrap gap-1">{c.tools.map((t, j) => <span key={j} className={`rounded-md ${accent.bg} px-1.5 py-0.5 text-[11px] font-mono ${accent.text}`}>{t}</span>)}</div>
              </div>
            ))}
          </div>
        </Panel>
      )

    case 'resilience':
      return (
        <Panel title="Crash vs graceful recovery">
          <p className="text-sm text-red-300">✗ unhandled: {data.crash}</p>
          <ul className="mt-1 text-sm">{data.retry.map((r, i) => <li key={i} className={r.includes('recovered') ? 'text-emerald-300' : 'text-amber-300'}>↻ {r}</li>)}</ul>
        </Panel>
      )

    case 'memory_short':
      return (
        <Panel title="Short-term memory (checkpointer + thread_id)">
          <p className="text-sm text-slate-400">Turn 1 → <span className="text-slate-200">{data.turn1}</span></p>
          <p className="text-sm text-slate-400 mt-1">Turn 2 (“what was it?”) → <span className="text-emerald-300">{data.turn2}</span></p>
        </Panel>
      )

    case 'memory_long':
      return (
        <Panel title="Long-term memory (vector recall)">
          <p className="text-xs text-slate-400 mb-1">query: “{data.query}”</p>
          <ul className="text-sm text-slate-200 space-y-1">{data.recall.map((h, i) => <li key={i}>• {h}</li>)}</ul>
        </Panel>
      )

    case 'compaction':
      return (
        <Panel title={`Compaction: ${data.before} → ${data.after} messages`}>
          <p className="text-sm text-slate-300 whitespace-pre-wrap">{data.summary}</p>
        </Panel>
      )

    case 'supervisor':
      return (
        <div className="space-y-3">
          <Panel title="Supervisor decisions">
            <ol className="space-y-1 text-sm">{data.supervisor.map((s, i) => <li key={i} className="text-slate-200"><span className={`font-semibold ${accent.text}`}>{s.decision}</span> — <span className="text-slate-400">{s.note}</span></li>)}</ol>
          </Panel>
          <Panel title={`Researcher gathered ${data.findings.length} findings`}>
            <ul className="space-y-1 text-sm text-slate-300">{data.findings.map((f, i) => <li key={i} className="line-clamp-1">• {f.sub_question}</li>)}</ul>
          </Panel>
          <Panel title="Writer’s report"><ReportView text={data.report} /></Panel>
        </div>
      )

    case 'resume':
      return (
        <div className="space-y-3">
          <Panel title="Kill & resume">
            <p className="text-sm text-amber-300">💥 interrupted before {JSON.stringify(data.interrupted_before)} — {data.before_findings} findings safely checkpointed.</p>
            <p className="text-sm text-emerald-300 mt-1">✓ resumed from disk and finished writing.</p>
          </Panel>
          <Panel title="Report (produced after resuming)"><ReportView text={data.final} /></Panel>
        </div>
      )

    case 'critique':
      return (
        <div className="space-y-3">
          <Panel title="Draft"><ReportView text={data.draft} /></Panel>
          <Panel title="Self-critique">
            <span className={`inline-block mb-2 rounded-md px-2 py-0.5 text-[11px] font-semibold ${data.verdict === 'PASS' ? 'bg-emerald-500/15 text-emerald-300' : 'bg-amber-500/15 text-amber-300'}`}>verdict: {data.verdict}</span>
            <p className="text-sm text-slate-300 whitespace-pre-wrap">{data.critique}</p>
          </Panel>
        </div>
      )

    case 'approval':
      return (
        <Panel title="⏸ interrupt() paused here — approval request">
          <p className="text-sm text-amber-200 mb-2">{data.message}</p>
          {data.critique && <p className="text-xs text-slate-400 mb-2">critique: {data.critique.slice(0, 250)}…</p>}
          <div className="max-h-56 overflow-y-auto rounded-lg bg-black/20 p-3"><ReportView text={data.draft} /></div>
          <p className="mt-2 text-xs text-slate-500">In the Studio tab you can actually approve/reject this and resume the graph.</p>
        </Panel>
      )

    default:
      return <pre className="text-xs text-slate-400 overflow-x-auto">{JSON.stringify(data, null, 2)}</pre>
  }
}

function Panel({ title, children }) {
  return (
    <div className="rounded-xl bg-black/20 border border-white/5 p-4 animate-fadeInUp">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">{title}</h4>
      {children}
    </div>
  )
}

function Trace({ trace, accent }) {
  return (
    <div className="rounded-xl bg-black/20 border border-white/5 p-4">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">Node trace</h4>
      <ol className="space-y-1.5">
        {trace.map((t, i) => (
          <li key={i} className="flex items-center gap-2 text-sm animate-fadeInUp" style={{ animationDelay: `${i * 60}ms` }}>
            <span className={`h-2 w-2 rounded-full ${accent.dot}`} />
            <span className="font-mono text-slate-200">{t.node}</span>
            {t.verdict && <span className="text-xs text-amber-300">verdict: {t.verdict}</span>}
            {t.revision && <span className="text-xs text-slate-500">rev #{t.revision}</span>}
            {(t.detail?.sub_question || t.sub_question) && <span className="text-xs text-slate-500 line-clamp-1">{t.detail?.sub_question || t.sub_question}</span>}
          </li>
        ))}
      </ol>
    </div>
  )
}
