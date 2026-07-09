import { useEffect, useState } from 'react'
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

  // Day 2 results carry a `corpus` label ("your N uploaded files" / "built-in
  // sample docs") so it's always clear what the demo just ran against.
  const corpusNote = data.corpus ? (
    <p className="mb-2 text-[11px] text-slate-500">running on: <span className={accent.text}>{data.corpus}</span></p>
  ) : null

  // Day 2 query-side stages echo the exact question that drove retrieval, so
  // it's transparent WHY these chunks (and this answer) came back.
  const queryNote = data.query ? (
    <p className="mb-2 text-xs text-slate-300">
      question: <span className={`font-medium ${accent.text}`}>“{data.query}”</span>
    </p>
  ) : null

  // One retrieved chunk, rendered transparently: rank badge, source + chunk id,
  // optional score/cosine, and a text preview. `hot` tints chunks worth calling
  // out (e.g. MMR's diverse picks). When a chunk's text repeats elsewhere in the
  // corpus we show a "×N identical" badge instead of hiding the duplicates.
  // Reused by compare / answer / retrieved / embedding.
  const Chunk = ({ c, hot }) => (
    <div className={`rounded-lg p-2 border ${hot ? `${accent.bg} ${accent.ring} ring-1 border-transparent` : 'bg-black/20 border-white/5'}`}>
      <div className="flex items-center justify-between gap-2 text-xs mb-1">
        <span className="flex items-center gap-1.5 min-w-0 flex-wrap">
          <span className={`shrink-0 inline-flex h-4 w-4 items-center justify-center rounded ${accent.bg} text-[10px] font-bold ${accent.text}`}>{c.rank}</span>
          <Src>{c.source}{c.chunk_id != null ? ` · #${c.chunk_id}` : ''}</Src>
          {c.dup_count > 1 && (
            <span className="shrink-0 rounded bg-amber-500/15 text-amber-300 px-1.5 py-0.5 text-[10px] font-medium" title={c.dup_ids?.length ? `identical chunks: ${c.dup_ids.map((x) => `#${x}`).join(', ')}` : ''}>
              ×{c.dup_count} identical in your doc
            </span>
          )}
          {c.same_as != null && (
            <span className="shrink-0 rounded bg-amber-500/15 text-amber-300 px-1.5 py-0.5 text-[10px] font-medium">
              = identical to #{c.same_as}
            </span>
          )}
        </span>
        {c.cosine != null
          ? <span className="shrink-0 text-slate-400">cosine {c.cosine}</span>
          : c.score != null && <span className="shrink-0 text-slate-400">score {c.score}</span>}
      </div>
      <p className="text-xs text-slate-300">{c.preview}…</p>
    </div>
  )

  // "N duplicate copies were folded away" note, shown when dedup collapsed chunks.
  const collapsedNote = data.collapsed > 0 ? (
    <p className="mt-2 text-[11px] text-amber-300/80">
      {data.collapsed} near-duplicate chunk{data.collapsed === 1 ? '' : 's'} collapsed — your document repeats this content, so retrieval kept only the distinct pieces.
    </p>
  ) : null

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

    case 'compare': {
      // Prefer the rich, chunk-level shape (docs_a/docs_b); fall back to the
      // old filename-only shape so nothing breaks if the backend is older.
      const docsA = data.docs_a || (data.sources_a || []).map((s, i) => ({ rank: i + 1, source: s, preview: '' }))
      const docsB = data.docs_b || (data.sources_b || []).map((s, i) => ({ rank: i + 1, source: s, preview: '' }))
      const keyOf = (c) => (c.chunk_id != null ? `${c.source}#${c.chunk_id}` : `${c.source}|${c.preview}`)
      const inA = new Set(docsA.map(keyOf))
      return (
        <Panel title="Retrieval — two strategies, chunk by chunk">
          {corpusNote}
          {queryNote}
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <p className="text-xs font-semibold text-slate-300 mb-1.5">{data.label_a}</p>
              <div className="space-y-2">{docsA.map((c, i) => <Chunk key={i} c={c} />)}</div>
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-300 mb-1.5">{data.label_b}</p>
              <div className="space-y-2">{docsB.map((c, i) => <Chunk key={i} c={c} hot={!inA.has(keyOf(c))} />)}</div>
            </div>
          </div>
          <p className="mt-2 text-[11px] text-slate-500">
            Highlighted chunks on the right are the ones the second strategy pulled in that the first did not — the visible difference between the two.
          </p>
          {docsA.some((c) => c.same_as != null) && (
            <p className="mt-1 text-[11px] text-amber-300/80">
              Notice the left column repeats identical chunks — that redundancy is exactly what MMR is designed to remove.
            </p>
          )}
        </Panel>
      )
    }

    case 'answer':
      return (
        <div className="space-y-3">
          {corpusNote}
          {queryNote}
          {data.heading && <p className={`text-sm ${accent.text}`}>{data.heading}</p>}
          <Panel title="Answer"><ReportView text={data.answer} /><div className="mt-2 flex flex-wrap gap-1">{data.sources.map((s) => <Src key={s}>{s}</Src>)}</div></Panel>
          {data.context && data.context.length > 0 && (
            <Panel title={`Context the model was given — ${data.context.length} retrieved chunk${data.context.length === 1 ? '' : 's'}`}>
              <p className="text-[11px] text-slate-500 mb-2">The answer above may use ONLY these chunks. The <span className="font-mono">[n]</span> citations point back to them.</p>
              <div className="space-y-2">{data.context.map((c, i) => <Chunk key={i} c={c} />)}</div>
            </Panel>
          )}
        </div>
      )

    case 'chunks':
      return (
        <Panel title="Chunking — size changes the number of chunks">
          {corpusNote}
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
          {corpusNote}
          {queryNote}
          <div className="space-y-2">
            {data.items.map((it, i) => <Chunk key={i} c={it} />)}
          </div>
          {collapsedNote}
        </Panel>
      )

    case 'documents':
      return (
        <Panel title={`Loaded ${data.count} documents · ${data.total_chars.toLocaleString()} characters`}>
          {corpusNote}
          <div className="space-y-2">
            {data.items.map((it, i) => (
              <div key={i} className="rounded-lg bg-black/20 p-2">
                <div className="flex items-center justify-between text-xs mb-1"><Src>{it.source}</Src><span className="text-slate-400">{it.chars.toLocaleString()} chars</span></div>
                <p className="text-xs text-slate-300">{it.preview}…</p>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-slate-500">Each file is now a <span className="font-mono">Document</span> = page_content + metadata. The metadata (source) becomes the citation.</p>
        </Panel>
      )

    case 'embedding': {
      // Prefer the ranked top-k list; fall back to the single-nearest shape.
      const neighbors = data.neighbors || (data.nearest ? [{ rank: 1, ...data.nearest }] : [])
      return (
        <div className="space-y-3">
          {corpusNote}
          <Panel title={`Embed — ${data.count} chunks × ${data.dim}-dim vectors · ${data.model}`}>
            <p className="text-xs text-slate-400 mb-1">your question “{data.query}” as a vector (first 8 of {data.dim} numbers):</p>
            <pre className="overflow-x-auto rounded-lg bg-black/40 p-3 text-xs text-slate-300">[{data.head.join(', ')}, …]</pre>
          </Panel>
          <Panel title={`Nearest chunks by cosine similarity — closest ${neighbors.length} of ${data.count} (higher = more similar)`}>
            <div className="space-y-2">
              {neighbors.map((c, i) => <Chunk key={i} c={c} hot={i === 0} />)}
            </div>
            {collapsedNote}
          </Panel>
        </div>
      )
    }

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

    case 'slide_demo':
      return <SlideDemo data={data} accent={accent} />

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

// ─────────────────────────────────────────────────────────────────────────────
// SlideDemo — renders a Day-1 slide's live event stream (heading / note /
// prompt_block / model_response / prob_bars / tool_call / observation / tag /
// table / verdict / final / takeaway). One-off block per step type keeps each
// piece readable and lets us style teaching cues (prob bars, verdict badges,
// tag pills) distinctly.
//
// Also used by Day-3 "modules" (mode === 'module'), which add richer step
// types: state_json, graph_mermaid, node_flash, route_decision, code_view,
// progress, compare_grid, loop_meter.
// ─────────────────────────────────────────────────────────────────────────────
function SlideDemo({ data, accent }) {
  const isModule = data.mode === 'module'
  const badge = isModule ? `Module ${data.slide} · Live` : `Slide ${data.slide} · Live demo`
  return (
    <div className="space-y-2">
      {/* Slide / Module banner — mirrors the CLI's boxed header */}
      <div className={`rounded-xl ${accent.bg} ${accent.ring} ring-1 px-4 py-3`}>
        <div className={`text-[11px] font-semibold uppercase tracking-wide ${accent.text}`}>{badge}</div>
        <div className="text-sm font-bold text-slate-100">{data.title}</div>
        {data.subtitle && <div className="text-xs text-slate-300 mt-0.5">{data.subtitle}</div>}
      </div>

      {/* Steps */}
      <div className="space-y-2">
        {(data.steps || []).map((s, i) => (
          <SlideStep key={i} step={s} accent={accent} idx={i} />
        ))}
      </div>
    </div>
  )
}

function SlideStep({ step, accent, idx }) {
  const delay = { animationDelay: `${idx * 30}ms` }

  switch (step.type) {
    case 'heading':
      return (
        <div className="pt-2 animate-fadeInUp" style={delay}>
          <div className={`text-[11px] font-semibold uppercase tracking-wider ${accent.text} flex items-center gap-2`}>
            <span className={`inline-block h-2 w-2 rounded-full ${accent.dot}`} /> ▶ {step.label}
          </div>
          {step.desc && <div className="text-[11px] text-slate-400 pl-4">{step.desc}</div>}
        </div>
      )

    case 'note':
      return (
        <p className="text-xs text-slate-400 italic pl-4 animate-fadeInUp" style={delay}>{step.text}</p>
      )

    case 'prompt_block':
      return (
        <div className="rounded-lg bg-black/30 border border-white/5 px-3 py-2 animate-fadeInUp" style={delay}>
          <span className={`inline-block rounded ${accent.bg} px-1.5 py-0.5 text-[10px] font-bold ${accent.text} mr-2 align-top`}>[{step.label}]</span>
          <span className="text-xs text-slate-300 whitespace-pre-wrap">{step.text}</span>
        </div>
      )

    case 'model_response':
      return (
        <div className="rounded-lg bg-emerald-500/5 border border-emerald-400/20 px-3 py-2 animate-fadeInUp" style={delay}>
          <div className="text-[10px] font-semibold uppercase tracking-wide text-emerald-300 mb-1">{step.who || 'Model'}</div>
          <div className="text-sm text-slate-100 whitespace-pre-wrap">{step.text}</div>
        </div>
      )

    case 'prob_bars': {
      const chosen = step.chosen
      return (
        <div className="rounded-lg bg-black/30 border border-white/5 px-3 py-2 animate-fadeInUp" style={delay}>
          <div className="text-xs text-slate-400 mb-1">
            Prompt: <span className="text-slate-200 italic">"{step.prompt}"</span>
            {chosen && (<>&nbsp;·&nbsp;chosen: <span className="text-emerald-300 font-mono">{chosen}</span></>)}
          </div>
          <div className="space-y-1">
            {(step.candidates || []).map((c, j) => {
              const pct = Math.round((c.prob || 0) * 100)
              return (
                <div key={j} className="flex items-center gap-2 text-xs">
                  <span className="font-mono text-slate-200 w-16 truncate">{c.token}</span>
                  <div className="flex-1 h-2 rounded bg-white/5 overflow-hidden">
                    <div className={`h-full bg-gradient-to-r ${accent.grad}`} style={{ width: `${Math.max(2, pct)}%` }} />
                  </div>
                  <span className="text-slate-400 w-12 text-right">{(c.prob * 100).toFixed(1)}%</span>
                </div>
              )
            })}
          </div>
        </div>
      )
    }

    case 'tool_call':
      return (
        <div className="rounded-lg bg-amber-500/5 border border-amber-400/25 px-3 py-2 font-mono text-xs text-amber-200 animate-fadeInUp" style={delay}>
          <span className="text-amber-400 font-semibold">🔧 tool_call → </span>
          {step.name}({Object.entries(step.args || {}).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')})
          {step.id && <span className="text-amber-400/60 ml-2">#{String(step.id).slice(0, 10)}…</span>}
        </div>
      )

    case 'observation':
      return (
        <div className="rounded-lg bg-slate-500/10 border border-slate-500/20 px-3 py-2 text-xs animate-fadeInUp" style={delay}>
          <span className="text-slate-400 font-semibold">👁 observation → </span>
          <span className="text-slate-100 whitespace-pre-wrap">{step.text}</span>
        </div>
      )

    case 'tag':
      return (
        <div className="flex items-start gap-2 text-xs animate-fadeInUp" style={delay}>
          <span className={`shrink-0 rounded-md ${accent.bg} px-1.5 py-0.5 font-bold ${accent.text} uppercase tracking-wide`}>[{step.label}]</span>
          <span className="text-slate-300 whitespace-pre-wrap">{step.text}</span>
        </div>
      )

    case 'table':
      return (
        <div className="overflow-x-auto rounded-lg bg-black/30 border border-white/5 animate-fadeInUp" style={delay}>
          <table className="min-w-full text-xs">
            <thead>
              <tr>
                {(step.headers || []).map((h, j) => (
                  <th key={j} className={`text-left px-3 py-2 ${accent.text} font-semibold uppercase tracking-wide border-b border-white/10`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(step.rows || []).map((r, ri) => (
                <tr key={ri} className="border-b border-white/5 last:border-0">
                  {r.map((c, ci) => (
                    <td key={ci} className={`px-3 py-2 align-top ${ci === 0 ? 'font-semibold text-slate-200' : 'text-slate-300'}`}>{c}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )

    case 'verdict':
      return (
        <div className={`rounded-lg px-3 py-2 border animate-fadeInUp ${step.passed ? 'bg-emerald-500/10 border-emerald-400/30' : 'bg-rose-500/10 border-rose-400/30'}`} style={delay}>
          <div className={`text-xs font-bold uppercase tracking-wider ${step.passed ? 'text-emerald-300' : 'text-rose-300'}`}>
            {step.passed ? '✓ verdict: PASS' : '✗ verdict: NEEDS REVISION'}
          </div>
          {!step.passed && (step.issues || []).length > 0 && (
            <ul className="mt-1 space-y-0.5 text-xs text-rose-200">
              {step.issues.map((iss, j) => <li key={j}>• {iss}</li>)}
            </ul>
          )}
        </div>
      )

    case 'final':
      return (
        <div className={`rounded-xl bg-gradient-to-br ${accent.grad} p-[1px] animate-fadeInUp`} style={delay}>
          <div className="rounded-xl bg-slate-950/85 px-4 py-3">
            <div className={`text-[10px] font-bold uppercase tracking-wider ${accent.text} mb-1`}>Final answer</div>
            <div className="text-sm text-slate-100 whitespace-pre-wrap"><ReportView text={step.text} /></div>
          </div>
        </div>
      )

    case 'takeaway':
      return (
        <div className="rounded-lg bg-fuchsia-500/10 border border-fuchsia-400/30 px-3 py-2 animate-fadeInUp" style={delay}>
          <span className="text-fuchsia-300 font-bold text-xs">➜ Takeaway: </span>
          <span className="text-fuchsia-100 text-xs">{step.text}</span>
        </div>
      )

    // ─── Day-3 LangGraph step types ─────────────────────────────────────
    case 'state_json':
      return <StateJsonStep step={step} accent={accent} delay={delay} />

    case 'graph_mermaid':
      return <GraphMermaidStep step={step} accent={accent} delay={delay} />

    case 'node_flash':
      return <NodeFlashStep step={step} accent={accent} delay={delay} />

    case 'route_decision':
      return <RouteDecisionStep step={step} accent={accent} delay={delay} />

    case 'code_view':
      return <CodeViewStep step={step} accent={accent} delay={delay} />

    case 'progress':
      return <ProgressStep step={step} accent={accent} delay={delay} />

    case 'compare_grid':
      return <CompareGridStep step={step} accent={accent} delay={delay} />

    case 'loop_meter':
      return <LoopMeterStep step={step} accent={accent} delay={delay} />

    default:
      return null
  }
}

// ═════════════════════════════════════════════════════════════════════════
// Day-3 step renderers — one component per rich LangGraph step type.
// Kept below the switch so the main file stays scannable.
// ═════════════════════════════════════════════════════════════════════════

// StateJson — animated TypedDict snapshot with per-key diff highlighting.
// If `prev` is provided, keys whose serialized value changed are auto-included
// in the highlight set (union with `step.highlight`). Long strings collapse.
function StateJsonStep({ step, accent, delay }) {
  const prev = step.prev || {}
  const state = step.state || {}
  const explicit = new Set(step.highlight || [])
  const changed = new Set()
  for (const k of Object.keys(state)) {
    if (JSON.stringify(prev[k]) !== JSON.stringify(state[k])) changed.add(k)
  }
  const hot = (k) => explicit.has(k) || (step.prev && changed.has(k))
  return (
    <div className={`rounded-xl bg-black/40 border ${accent.ring} ring-1 border-white/5 p-3 animate-fadeInUp`} style={delay}>
      <div className="flex items-baseline justify-between mb-2">
        <div className={`text-[11px] font-bold uppercase tracking-wider ${accent.text}`}>{step.title || 'State'}</div>
        {step.prev && (
          <div className="text-[10px] text-slate-500">
            {changed.size ? `${changed.size} field${changed.size === 1 ? '' : 's'} changed` : 'no change'}
          </div>
        )}
      </div>
      <div className="font-mono text-xs">
        <span className="text-slate-500">{'{'}</span>
        <div className="pl-3">
          {Object.entries(state).map(([k, v], i) => (
            <div key={k} className={`transition-colors rounded px-1 -mx-1 ${hot(k) ? `${accent.bg} ring-1 ${accent.ring}` : ''}`}>
              <span className={hot(k) ? `${accent.text} font-semibold` : 'text-slate-300'}>{k}</span>
              <span className="text-slate-500">: </span>
              <StateValue v={v} accent={accent} hot={hot(k)} />
              {i < Object.entries(state).length - 1 && <span className="text-slate-500">,</span>}
              {hot(k) && step.prev && changed.has(k) && (
                <span className={`ml-2 text-[9px] rounded ${accent.bg} px-1 ${accent.text}`}>updated</span>
              )}
            </div>
          ))}
        </div>
        <span className="text-slate-500">{'}'}</span>
      </div>
      {step.note && <p className="mt-2 text-[11px] text-slate-400">{step.note}</p>}
    </div>
  )
}

function StateValue({ v, accent, hot }) {
  if (v === null || v === undefined) return <span className="text-slate-500">null</span>
  if (typeof v === 'boolean') return <span className="text-amber-300">{String(v)}</span>
  if (typeof v === 'number') return <span className="text-amber-200">{v}</span>
  if (typeof v === 'string') {
    const short = v.length > 80 ? v.slice(0, 80) + '…' : v
    return <span className={hot ? 'text-emerald-200' : 'text-emerald-300/80'}>"{short}"</span>
  }
  if (Array.isArray(v)) {
    if (v.length === 0) return <span className="text-slate-500">[]</span>
    return (
      <span>
        <span className="text-slate-500">[</span>
        {v.length <= 4 && v.every((x) => typeof x !== 'object') ? (
          v.map((x, i) => (
            <span key={i}>
              <StateValue v={x} accent={accent} hot={hot} />
              {i < v.length - 1 && <span className="text-slate-500">, </span>}
            </span>
          ))
        ) : (
          <span className="text-slate-400"> {v.length} item{v.length === 1 ? '' : 's'} </span>
        )}
        <span className="text-slate-500">]</span>
      </span>
    )
  }
  if (typeof v === 'object') {
    const keys = Object.keys(v)
    return <span className="text-slate-400">{'{'}{keys.length} field{keys.length === 1 ? '' : 's'}{'}'}</span>
  }
  return <span className="text-slate-300">{String(v)}</span>
}

// GraphMermaid — renders a Mermaid flowchart client-side (dynamic import so
// we don't force everyone to load Mermaid for Day 1/2). Falls back to plain
// code if Mermaid isn't installed. Active nodes get a highlight overlay.
function GraphMermaidStep({ step, accent, delay }) {
  const [svg, setSvg] = useState('')
  const [err, setErr] = useState('')
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const mermaid = (await import('mermaid')).default
        mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose', flowchart: { curve: 'basis' } })
        // Emphasize active nodes by injecting a classDef + `class ... active`
        // lines. We add them before the last blank line of the markup.
        const withHi = injectActive(step.markup, step.active || [])
        const id = 'mermaid_' + Math.random().toString(36).slice(2)
        const { svg } = await mermaid.render(id, withHi)
        if (!cancelled) setSvg(svg)
      } catch (e) {
        if (!cancelled) setErr(String(e?.message || e))
      }
    })()
    return () => { cancelled = true }
  }, [step.markup, JSON.stringify(step.active || [])])
  return (
    <div className={`rounded-xl bg-black/30 border border-white/5 p-3 animate-fadeInUp`} style={delay}>
      {step.title && <div className={`text-[11px] font-bold uppercase tracking-wider ${accent.text} mb-2`}>{step.title}</div>}
      {svg ? (
        <div className="mermaid-wrap overflow-x-auto flex justify-center [&_svg]:max-w-full" dangerouslySetInnerHTML={{ __html: svg }} />
      ) : err ? (
        <pre className="text-[11px] text-amber-300 whitespace-pre-wrap">{step.markup}</pre>
      ) : (
        <pre className="text-[11px] text-slate-400 whitespace-pre-wrap">{step.markup}</pre>
      )}
      {step.note && <p className="mt-2 text-[11px] text-slate-400">{step.note}</p>}
    </div>
  )
}

function injectActive(markup, active) {
  if (!active || !active.length) return markup
  const classDef = '\nclassDef active fill:#7c3aed,stroke:#f0abfc,stroke-width:2px,color:#fff;\n'
  const classes = active.map((n) => `class ${n} active;`).join('\n')
  return markup + classDef + classes + '\n'
}

// NodeFlash — the "planner fires" pill. Different color per status.
function NodeFlashStep({ step, accent, delay }) {
  const tones = {
    active: 'bg-violet-500/15 text-violet-200 border-violet-400/40 ring-2 ring-violet-400/50',
    done:   'bg-emerald-500/10 text-emerald-200 border-emerald-400/30',
    pending: 'bg-slate-500/10 text-slate-300 border-slate-400/30',
    error:  'bg-rose-500/10 text-rose-200 border-rose-400/40',
  }
  const dotTone = {
    active: 'bg-violet-400 animate-pulse',
    done:   'bg-emerald-400',
    pending: 'bg-slate-400',
    error:  'bg-rose-400 animate-pulse',
  }
  const t = tones[step.status] || tones.active
  const d = dotTone[step.status] || dotTone.active
  return (
    <div className={`flex items-center gap-2 rounded-lg border px-3 py-2 animate-fadeInUp ${t}`} style={delay}>
      <span className={`h-2.5 w-2.5 rounded-full ${d}`} />
      <span className="font-mono text-xs font-bold">{step.node}</span>
      {step.label && <span className="text-xs opacity-90">— {step.label}</span>}
    </div>
  )
}

// RouteDecision — condition, boolean, chosen branch.
function RouteDecisionStep({ step, accent, delay }) {
  const cls = step.value ? 'bg-emerald-500/10 border-emerald-400/30 text-emerald-200' : 'bg-amber-500/10 border-amber-400/30 text-amber-200'
  return (
    <div className={`rounded-lg border px-3 py-2 animate-fadeInUp ${cls}`} style={delay}>
      <div className="flex items-baseline gap-2 flex-wrap text-xs">
        <span className="opacity-70 uppercase tracking-wider text-[10px] font-bold">router</span>
        <span className="font-mono">{step.condition}</span>
        <span className="opacity-70">→</span>
        <span className={`font-mono font-bold ${step.value ? 'text-emerald-300' : 'text-amber-300'}`}>{String(step.value)}</span>
        <span className="opacity-70">→ branch</span>
        <span className="font-mono font-bold">{step.branch}</span>
      </div>
      {step.desc && <p className="mt-1 text-[11px] opacity-80">{step.desc}</p>}
    </div>
  )
}

// CodeView — Python snippet with optional highlighted lines.
function CodeViewStep({ step, accent, delay }) {
  const lines = (step.code || '').split('\n')
  const hi = new Set(step.highlight || [])
  return (
    <div className={`rounded-xl bg-black/50 border border-white/10 overflow-hidden animate-fadeInUp`} style={delay}>
      {step.title && (
        <div className={`px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider ${accent.text} bg-white/5 border-b border-white/10 flex items-center justify-between`}>
          <span>{step.title}</span>
          <span className="text-slate-500 font-mono normal-case tracking-normal">{step.language || 'python'}</span>
        </div>
      )}
      <pre className="text-[12px] leading-relaxed overflow-x-auto py-2">
        {lines.map((line, i) => {
          const n = i + 1
          const isHi = hi.has(n)
          return (
            <div key={i} className={`flex ${isHi ? `${accent.bg} border-l-2 ${accent.ring}` : ''}`}>
              <span className="w-8 shrink-0 text-right pr-2 text-slate-600 select-none">{n}</span>
              <code className={`whitespace-pre pr-3 ${isHi ? 'text-slate-100' : 'text-slate-300'}`}>{line || ' '}</code>
            </div>
          )
        })}
      </pre>
    </div>
  )
}

// Progress — thick bar with a step label.
function ProgressStep({ step, accent, delay }) {
  const pct = step.total ? Math.min(100, Math.round((step.current / step.total) * 100)) : 0
  return (
    <div className="rounded-lg bg-black/30 border border-white/5 px-3 py-2 animate-fadeInUp" style={delay}>
      <div className="flex items-baseline justify-between mb-1 text-xs">
        <span className="text-slate-300">{step.label || 'progress'}</span>
        <span className={`font-mono ${accent.text}`}>{step.current} / {step.total}</span>
      </div>
      <div className="h-2 rounded bg-white/5 overflow-hidden">
        <div className={`h-full bg-gradient-to-r ${accent.grad} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

// CompareGrid — two mini-panels side-by-side (ReAct vs Plan-Execute).
function CompareGridStep({ step, accent, delay }) {
  const Side = ({ side, tone }) => (
    <div className={`rounded-xl border p-3 ${tone}`}>
      <div className={`text-[11px] font-bold uppercase tracking-wider ${accent.text} mb-1`}>{side.title}</div>
      {side.subtitle && <p className="text-[11px] text-slate-300 mb-2">{side.subtitle}</p>}
      {side.chips && side.chips.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {side.chips.map((c, i) => (
            <span key={i} className={`text-[10px] rounded-full ${accent.bg} px-2 py-0.5 ${accent.text}`}>{c}</span>
          ))}
        </div>
      )}
      <div className="space-y-1">
        {(side.items || []).map((it, i) => (
          <div key={i} className="flex items-baseline gap-2 text-[11px]">
            <span className="text-slate-500 shrink-0 w-32">{it.k}</span>
            <span className="text-slate-200">{it.v}</span>
          </div>
        ))}
      </div>
    </div>
  )
  return (
    <div className="grid gap-3 md:grid-cols-2 animate-fadeInUp" style={delay}>
      <Side side={step.left}  tone="bg-black/30 border-white/10" />
      <Side side={step.right} tone="bg-black/30 border-white/10" />
    </div>
  )
}

// LoopMeter — the runaway-loop counter used by Module 12.
function LoopMeterStep({ step, accent, delay }) {
  const bar = Math.min(100, Math.round((step.tokens / 60000) * 100))
  const tone = step.warning
    ? 'bg-rose-500/10 border-rose-400/40 text-rose-200'
    : 'bg-black/30 border-white/10 text-slate-200'
  return (
    <div className={`rounded-lg border px-3 py-2 animate-fadeInUp ${tone}`} style={delay}>
      <div className="flex items-baseline justify-between text-xs mb-1">
        <span className="font-mono">iteration {step.iterations}</span>
        <span className={`font-mono ${step.warning ? 'text-rose-300' : accent.text}`}>{step.tokens.toLocaleString()} tokens</span>
      </div>
      <div className="h-2 rounded bg-white/5 overflow-hidden">
        <div
          className={`h-full transition-all ${step.warning ? 'bg-gradient-to-r from-amber-500 to-rose-500' : `bg-gradient-to-r ${accent.grad}`}`}
          style={{ width: `${bar}%` }}
        />
      </div>
      {step.note && <p className="mt-1 text-[11px] opacity-80">{step.note}</p>}
    </div>
  )
}
