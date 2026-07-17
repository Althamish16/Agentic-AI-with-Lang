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

    case 'tools': {
      // ── T2 · Agent loop — rendered as a NUMBERED PROCESSING PIPELINE ──
      // Every hop the agent takes becomes one numbered step so learners
      // watch the loop unfold end-to-end: ask → decide → tool runs →
      // result returns → decide again → final answer.
      const turns = Array.isArray(data.turns) ? data.turns : null
      const steps = []
      let n = 1

      steps.push({
        n: n++, kind: 'input', title: 'You ask',
        hint: 'The whole loop is driven by ONE HumanMessage — nothing else.',
        body: <p className="whitespace-pre-wrap text-slate-100">{data.question || '(no question)'}</p>,
      })

      if (turns) {
        turns.forEach((t) => {
          // Each tool call inside a turn = decision step + output step.
          if (t.calls && t.calls.length > 0) {
            t.calls.forEach((c) => {
              steps.push({
                n: n++, kind: 'decision',
                title: <>Turn {t.turn} · model decides to call <span className={`font-mono ${accent.text}`}>{c.name}(…)</span></>,
                hint: 'The LLM emits a structured tool_call — the graph routes to ToolNode.',
                body: (
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">arguments the model chose</p>
                    <pre className="overflow-x-auto rounded bg-black/50 p-2 text-[11px] leading-relaxed text-amber-100">{JSON.stringify(c.args, null, 2)}</pre>
                  </div>
                ),
              })
              if (c.result != null) {
                steps.push({
                  n: n++, kind: 'output',
                  title: <>ToolNode runs <span className={`font-mono ${accent.text}`}>{c.name}</span> · result flows back as a ToolMessage</>,
                  hint: 'The graph re-enters the agent node — the model now sees this string in its message history.',
                  body: (
                    <pre className="overflow-x-auto rounded bg-black/50 p-2 text-[11px] leading-relaxed text-violet-100 whitespace-pre-wrap max-h-56">{c.result}</pre>
                  ),
                })
              }
            })
          }
          if (t.is_final) {
            steps.push({
              n: n++, kind: 'success',
              title: <>Turn {t.turn} · model emits final answer (no more tool_calls)</>,
              hint: 'tools_condition sees a plain AIMessage → routes to END. Loop stops.',
              body: <div className="text-slate-100"><ReportView text={t.thought} /></div>,
            })
          }
        })
        const totalCalls = turns.reduce((n, t) => n + (t.calls?.length || 0), 0)
        steps.push({
          n: n++, kind: 'note', title: 'Loop summary',
          hint: 'The graph itself is a while-loop: agent → (tool? → agent : end).',
          body: (
            <div className="flex flex-wrap gap-3 text-[11px] text-slate-300">
              <span>⛓ turns: <span className="font-mono text-slate-100">{turns.length}</span></span>
              <span>·</span>
              <span>🔧 tool calls: <span className="font-mono text-slate-100">{totalCalls}</span></span>
              <span>·</span>
              <span>stop reason: <span className={accent.text}>agent produced a message with no tool_calls → tools_condition routed to END</span></span>
            </div>
          ),
        })
      } else {
        // Fallback for the older shape (no per-turn trace)
        const picks = data.tool_calls || []
        if (picks.length) {
          picks.forEach((c) => {
            steps.push({
              n: n++, kind: 'decision',
              title: <>Model decides to call <span className={`font-mono ${accent.text}`}>{c.name}(…)</span></>,
              body: <pre className="overflow-x-auto rounded bg-black/50 p-2 text-[11px] text-amber-100">{JSON.stringify(c.args, null, 2)}</pre>,
            })
          })
        } else {
          steps.push({
            n: n++, kind: 'decision', title: 'Model answers directly (no tool needed)',
            hint: 'The LLM decided the question is answerable from its own knowledge.',
          })
        }
        if (data.final) {
          steps.push({
            n: n++, kind: 'success', title: 'Final answer',
            body: <div className="text-slate-100"><ReportView text={data.final} /></div>,
          })
        }
      }

      return <StepFlow steps={steps} accent={accent} />
    }

    case 'tool_belt': {
      // ── T1 · INSPECTOR STRIP + TOOL CARDS ────────────────────────────
      // Distinct visual identity: a horizontal arrow strip across the top
      // showing the plain-fn -> @tool -> bind_tools -> schema pipeline,
      // followed by a GRID of tool inspector cards. Not a numbered step
      // flow (T2 uses that) — this is an inspection view, no time axis.
      const arrow = (
        <svg className="shrink-0 h-4 w-4 text-slate-600" viewBox="0 0 20 20" fill="currentColor"><path d="M7.293 4.293a1 1 0 011.414 0l5 5a1 1 0 010 1.414l-5 5a1 1 0 01-1.414-1.414L11.586 10 7.293 5.707a1 1 0 010-1.414z"/></svg>
      )
      const stages = [
        { tag: 'plain fn', code: 'def retrieve_documents(q):\n  return format(get_retriever().invoke(q))', color: 'text-slate-300' },
        { tag: '@tool', code: '@tool\ndef retrieve_documents(q: str) -> str:\n  """Docstring becomes the prompt."""', color: 'text-fuchsia-300' },
        { tag: 'bind_tools', code: 'llm.bind_tools([retrieve, web_search, summarize])', color: 'text-amber-300' },
        { tag: 'schema (what model sees)', code: '{\n  "name": "retrieve_documents",\n  "parameters": { "query": "string" },\n  "description": "..."\n}', color: 'text-emerald-300' },
      ]
      return (
        <div className="space-y-4">
          {/* Transform strip: shows the code MUTATION that happens when you add @tool + bind_tools */}
          <div className="rounded-xl bg-slate-950/50 ring-1 ring-white/10 p-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">Pipeline · how a plain Python function becomes a tool the LLM can see</p>
            <div className="flex items-stretch gap-2 overflow-x-auto">
              {stages.map((s, i) => (
                <div key={s.tag} className="flex items-stretch gap-2">
                  <div className="shrink-0 w-64 rounded-lg bg-black/40 ring-1 ring-white/5 p-2">
                    <p className={`text-[10px] font-bold uppercase tracking-wider mb-1 ${s.color}`}>{s.tag}</p>
                    <pre className="text-[10px] font-mono text-slate-300 whitespace-pre overflow-x-auto leading-snug">{s.code}</pre>
                  </div>
                  {i < stages.length - 1 && <div className="flex items-center">{arrow}</div>}
                </div>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-slate-500">The model NEVER sees your Python source — it only sees the last box (the JSON schema).</p>
          </div>

          {/* Grid of tool inspector cards */}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">The {data.tools.length} tools currently bound · name + schema + a live sample invocation</p>
            <div className="grid gap-2 md:grid-cols-3">
              {data.tools.map((t, i) => (
                <div key={i} className="rounded-xl bg-slate-900/40 ring-1 ring-white/10 overflow-hidden">
                  <div className={`px-3 py-1.5 ${accent.bg} border-b border-white/10 flex items-center gap-2`}>
                    <span className="text-[10px] uppercase tracking-wider text-slate-500">tool</span>
                    <span className={`font-mono font-bold text-sm ${accent.text}`}>{t.name}</span>
                  </div>
                  <div className="p-3 space-y-2">
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">args (typed)</p>
                      <div className="space-y-0.5">
                        {t.args.map((a, j) => (
                          <p key={j} className="text-[11px] font-mono">
                            <span className="text-slate-200">{a.name}</span>
                            <span className="text-slate-500">: </span>
                            <span className="text-amber-300">{a.type}</span>
                          </p>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">description (the prompt the model reads)</p>
                      <p className="text-[11px] text-slate-300 whitespace-pre-wrap max-h-24 overflow-y-auto border-l-2 border-slate-700 pl-2">{t.description}</p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">sample invocation (no LLM)</p>
                      <p className="text-[10px] font-mono text-slate-400">.invoke({JSON.stringify(t.sample_input)})</p>
                      <pre className="mt-1 rounded bg-black/60 p-1.5 text-[10px] font-mono text-emerald-200 whitespace-pre-wrap max-h-20 overflow-y-auto">{t.sample_output}</pre>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )
    }

    case 'routing':
      return (
        <Panel title="Tool selection — the model picks per question">
          <p className="text-[11px] text-slate-500 mb-3">
            Each row shows the expected pick (from the docstrings), what the model actually did, and WHY. A green dot means the model matched the intent.
          </p>
          <div className="space-y-2">
            {data.cases.map((c, i) => {
              const match = c.match !== undefined ? c.match : (c.tools && c.tools[0] === c.expected)
              return (
                <div key={i} className="rounded-lg bg-black/20 p-3 ring-1 ring-white/5">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm text-slate-200 flex-1">{c.question}</p>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${match ? 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/40' : 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-400/40'}`}>
                      {match ? '● match' : '● mismatch'}
                    </span>
                  </div>
                  <div className="mt-2 grid gap-1.5 text-[11px]">
                    {c.expected && (
                      <div className="flex items-center gap-2">
                        <span className="w-20 text-slate-500">expected</span>
                        <span className={`rounded-md ${accent.bg} px-1.5 py-0.5 font-mono ${accent.text}`}>{c.expected}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <span className="w-20 text-slate-500">actual</span>
                      <div className="flex flex-wrap gap-1">
                        {(c.picks && c.picks.length ? c.picks.map((p, j) => (
                          <span key={j} className={`rounded-md bg-black/40 px-1.5 py-0.5 font-mono text-slate-200 ring-1 ring-white/10`}>
                            {p.name}({Object.values(p.args)[0]?.toString().slice(0, 40)})
                          </span>
                        )) : (c.tools || []).map((t, j) => (
                          <span key={j} className={`rounded-md ${accent.bg} px-1.5 py-0.5 font-mono ${accent.text}`}>{t}</span>
                        )))}
                      </div>
                    </div>
                    {c.reason && (
                      <div className="flex items-start gap-2">
                        <span className="w-20 text-slate-500">why</span>
                        <span className="text-slate-400">{c.reason}</span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </Panel>
      )

    case 'vague_vs_specific': {
      // ── T4 · SPLIT-SCREEN A/B — side-by-side cards with big outcome
      // ribbons on top so the pedagogy (vague=skipped vs specific=called)
      // reads at a glance. Deliberately different from T1 (grid) and T2
      // (numbered steps) so learners see 3 clearly-different demos.
      const RIBBON = {
        'calc-used':  { text: '✓ tool CALLED with clean args', cls: 'bg-emerald-500/25 text-emerald-100 ring-emerald-400/60' },
        'wrong-tool': { text: '⚠ wrong tool picked',           cls: 'bg-amber-500/25 text-amber-100 ring-amber-400/60' },
        'no-tool':    { text: '✗ tool SKIPPED entirely',       cls: 'bg-rose-500/25 text-rose-100 ring-rose-400/60' },
      }
      const Side = ({ side, label, tone }) => {
        const r = data[side]
        if (!r) return null
        const rib = RIBBON[r.outcome] || { text: r.outcome, cls: 'bg-slate-500/25 text-slate-100 ring-slate-500/60' }
        return (
          <div className={`rounded-2xl overflow-hidden ring-2 ${tone}`}>
            <div className={`px-4 py-2 text-center text-xs font-black uppercase tracking-widest ring-1 ${rib.cls}`}>
              {rib.text}
            </div>
            <div className="p-4 bg-slate-900/40 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-wider text-slate-500">{label}</span>
                <code className={`rounded ${accent.bg} px-2 py-0.5 text-[11px] font-bold ${accent.text}`}>{r.tool_name}(…)</code>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">docstring the model saw</p>
                <pre className="rounded bg-black/50 p-2 text-[11px] leading-relaxed text-slate-300 whitespace-pre-wrap max-h-32 overflow-y-auto">{r.docstring}</pre>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">what the model did</p>
                {r.picks?.length ? (
                  <ul className="space-y-1">
                    {r.picks.map((p, i) => (
                      <li key={i} className="rounded bg-black/50 p-2 text-[11px] font-mono">
                        <span className="text-fuchsia-300">{p.name}</span>
                        <span className="text-slate-500">(</span>
                        <span className="text-emerald-200">{JSON.stringify(p.args)}</span>
                        <span className="text-slate-500">)</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="rounded bg-rose-500/10 ring-1 ring-rose-500/30 p-2 text-[11px] text-rose-200 italic">
                    (no tool call — the model answered from its own knowledge, ignoring the tool)
                  </p>
                )}
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">final answer</p>
                <p className="text-sm text-slate-100 font-semibold">{r.final || '—'}</p>
              </div>
            </div>
          </div>
        )
      }
      return (
        <div className="space-y-3">
          <div className="rounded-lg bg-gradient-to-r from-rose-500/10 via-slate-900/40 to-emerald-500/10 ring-1 ring-white/10 p-3 text-center">
            <p className="text-[10px] uppercase tracking-widest text-slate-500">A/B experiment · the ONLY difference is the tool's name + docstring</p>
            <p className="mt-1 text-base text-slate-100 font-semibold italic">"{data.question}"</p>
            <p className="mt-1 text-[11px] text-slate-500">same LLM · same graph · same Python body · same question</p>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Side side="vague"    label="RUN A · misleading name + vague docstring" tone="ring-rose-500/40" />
            <Side side="specific" label="RUN B · aligned name + rich docstring"     tone="ring-emerald-500/40" />
          </div>
          <div className="rounded-lg bg-black/20 ring-1 ring-white/5 p-3 text-[11px] text-slate-400">
            💡 <span className="text-slate-200 font-semibold">Lesson:</span> docstrings ARE prompts. A misleading name (<code className="text-rose-300">notes</code>) with a vague description gives the model no signal that the tool can do arithmetic, so a strong model <span className="text-rose-300">skips it</span>. Naming it <code className="text-emerald-300">calculator</code> and listing allowed operators + examples flips the outcome to <span className="text-emerald-300">called with a clean expression</span>.
          </div>
        </div>
      )
    }

    case 'resilience': {
      const s1 = data.stage1
      const s2 = data.stage2
      const retry = data.retry || []
      // Old shape: {crash: string, retry: [strings]}
      const isLegacy = !s1 && Array.isArray(retry) && retry.length && typeof retry[0] === 'string'
      if (isLegacy) {
        return (
          <Panel title="Crash vs graceful recovery">
            <p className="text-sm text-red-300">✗ unhandled: {data.crash}</p>
            <ul className="mt-1 text-sm">{retry.map((r, i) => <li key={i} className={r.includes('recovered') ? 'text-emerald-300' : 'text-amber-300'}>↻ {r}</li>)}</ul>
          </Panel>
        )
      }
      return (
        <div className="space-y-3">
          <Panel title="Stage 1 · Unhandled exception (this is what a crash looks like)">
            <p className="text-[11px] text-slate-500 mb-1">{s1?.label}</p>
            {s1?.ok
              ? <p className="text-sm text-emerald-300">✓ lucky: {s1.result}</p>
              : <p className="text-sm text-red-300">✗ {s1?.error} — an unhandled raise here would kill the whole run.</p>}
          </Panel>
          <Panel title="Stage 2 · Error returned as a STRING (agent can read it)">
            <p className="text-[11px] text-slate-500 mb-1">{s2?.label}</p>
            <pre className="overflow-x-auto rounded bg-black/40 p-2 text-[11px] leading-relaxed text-amber-200 whitespace-pre-wrap">{s2?.result}</pre>
            <p className="text-[11px] text-slate-500 mt-2">On the next agent turn the model sees this text as ordinary tool output and can pivot to another tool.</p>
          </Panel>
          <Panel title="Stage 3 · Retry loop (recovers on the next attempt)">
            <ul className="text-sm space-y-1">
              {retry.map((r, i) => (
                <li key={i} className={r.outcome === 'recovered' ? 'text-emerald-300' : 'text-amber-300'}>
                  ↻ attempt {r.attempt}: {r.outcome} → <span className="text-slate-300">{r.detail}</span>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      )
    }

    case 'backoff': {
      // ── T6 · HORIZONTAL TIMELINE CHART — one shared time axis across
      // both runs, coloured bars show wait+call ticks, exhausted marker
      // fills the tail red. Deliberately NOT a numbered step flow (T2
      // owns that visual) so T6 reads as "time-based chart" at a glance.
      const COLORS = {
        recovered: { chip: 'bg-emerald-500/15 text-emerald-300', text: 'text-emerald-200', tick: 'bg-emerald-400', wait: 'bg-emerald-400/25' },
        exhausted: { chip: 'bg-rose-500/15 text-rose-300',       text: 'text-rose-200',    tick: 'bg-rose-400',    wait: 'bg-rose-400/30' },
        failed:    { chip: 'bg-amber-500/15 text-amber-300',     text: 'text-amber-200',   tick: 'bg-amber-400',   wait: 'bg-amber-400/25' },
      }
      const totalMax = Math.max(data.recovers.total || 0, data.exhausts.total || 0, 0.05)
      const Timeline = ({ title, run, caseTag }) => (
        <div className="rounded-xl bg-slate-900/40 ring-1 ring-white/10 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 bg-black/40 border-b border-white/5">
            <div className="flex items-center gap-2">
              <span className={`rounded-full ${run.exhausted ? 'bg-rose-500/15 text-rose-300 ring-rose-400/40' : 'bg-emerald-500/15 text-emerald-300 ring-emerald-400/40'} ring-1 px-2 py-0.5 text-[10px] font-black uppercase tracking-widest`}>{caseTag}</span>
              <p className="text-xs font-semibold text-slate-200">{title}</p>
            </div>
            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ring-1 ${run.exhausted ? 'bg-rose-500/15 text-rose-200 ring-rose-400/40' : 'bg-emerald-500/15 text-emerald-200 ring-emerald-400/40'}`}>
              {run.exhausted ? '✗ RETRY_EXHAUSTED' : '✓ recovered'} · {run.total.toFixed(2)}s
            </span>
          </div>
          <div className="p-3 space-y-1.5">
            {run.attempts.map((a, i) => {
              const isTerminal = a.attempt == null
              const c = COLORS[a.outcome] || COLORS.failed
              const waitPct = a.delay ? Math.min(100, (a.delay / totalMax) * 100) : 0
              const cumPct = Math.min(100, ((a.cum || 0) / totalMax) * 100)
              return (
                <div key={i} className="grid grid-cols-[3rem_1fr_11rem] items-center gap-2 text-[11px]">
                  <span className="text-slate-500 font-mono">{isTerminal ? 'give up' : `try ${a.attempt}`}</span>
                  <div className="relative h-5 rounded bg-black/50 overflow-hidden ring-1 ring-white/5">
                    {a.delay > 0 && (
                      <div
                        className={`absolute inset-y-0 ${c.wait}`}
                        style={{ left: `${cumPct - waitPct}%`, width: `${waitPct}%` }}
                        title={`waited ${a.delay.toFixed(2)}s before this attempt`}
                      />
                    )}
                    {!isTerminal && (
                      <div
                        className={`absolute top-0 bottom-0 w-1 ${c.tick}`}
                        style={{ left: `calc(${cumPct}% - 2px)` }}
                        title={`call fired at t=${(a.cum || 0).toFixed(2)}s`}
                      />
                    )}
                    {isTerminal && (
                      <div
                        className="absolute inset-y-0 bg-rose-500/30 flex items-center justify-center"
                        style={{ left: `${cumPct}%`, right: 0 }}
                      >
                        <span className="text-[10px] font-bold text-rose-200">give up</span>
                      </div>
                    )}
                  </div>
                  <span className={`${c.text} font-mono truncate`} title={a.detail}>
                    {a.outcome}{a.delay > 0 && !isTerminal && <span className="ml-1 text-slate-500">· waited {a.delay.toFixed(2)}s</span>}
                  </span>
                </div>
              )
            })}
            <div className="grid grid-cols-[3rem_1fr_11rem] items-center gap-2 pt-1 border-t border-white/5">
              <span></span>
              <div className="relative h-3 text-[10px] text-slate-500">
                <span className="absolute left-0">0s</span>
                <span className="absolute left-1/2 -translate-x-1/2">{(totalMax / 2).toFixed(2)}s</span>
                <span className="absolute right-0">{totalMax.toFixed(2)}s</span>
              </div>
              <span></span>
            </div>
            <p className="text-[11px] text-slate-400 pt-1">
              final: <span className={run.exhausted ? 'text-rose-300 font-mono' : 'text-emerald-300 font-mono'}>{run.result}</span>
            </p>
          </div>
        </div>
      )
      return (
        <div className="space-y-3">
          <div className="rounded-lg bg-black/30 ring-1 ring-white/10 p-3">
            <p className="text-[11px] text-slate-400">
              ⏱ <span className="font-bold text-slate-200">Timeline chart</span> — each row is one retry attempt.
              The <span className="text-amber-300">amber block</span> is the sleep before the call, the coloured tick is the call itself, and if we exhaust retries a <span className="text-rose-300">red bar</span> fills the tail. Both runs share <span className={accent.text}>ONE horizontal time axis</span> so you can compare them side-by-side.
            </p>
          </div>
          <Timeline title="Flaky call — recovers on attempt #3" caseTag="CASE A" run={data.recovers} />
          <Timeline title="Permanently broken — returns RETRY_EXHAUSTED string (no raise)" caseTag="CASE B" run={data.exhausts} />
          <div className="rounded-lg bg-black/20 ring-1 ring-white/5 p-3 text-[11px] text-slate-400">
            💡 <span className="text-slate-200 font-semibold">Rule:</span> only retry <span className="italic">idempotent</span> operations (GETs, reads, searches). Wrapping a write without a dedup key can cause double-charges, duplicate emails, etc. The wrapper returns a <span className="font-mono text-slate-300">"RETRY_EXHAUSTED: …"</span> string in the failure case so the agent loop keeps flowing — never an unhandled raise.
          </div>
        </div>
      )
    }

    case 'memory_short':
      return (
        <Panel title="Short-term memory (checkpointer + thread_id)">
          <p className="text-sm text-slate-400">Turn 1 → <span className="text-slate-200">{data.turn1}</span></p>
          <p className="text-sm text-slate-400 mt-1">Turn 2 (“what was it?”) → <span className="text-emerald-300">{data.turn2}</span></p>
        </Panel>
      )

    case 'memory_state': {
      const snap = data.snapshot || {}
      return (
        <div className="space-y-3">
          <Panel title="Explicit State (TypedDict)">
            <p className="text-[11px] text-slate-500 mb-3">Every field below is checkpointed. The <span className={accent.text}>add_messages</span> reducer on <span className="font-mono text-slate-200">messages</span> makes updates MERGE (append) instead of overwriting — that's how chat memory grows without clobber.</p>
            <div className="rounded-lg bg-black/30 ring-1 ring-white/10 divide-y divide-white/5">
              {(data.fields || []).map((f) => (
                <div key={f.name} className="px-3 py-2 grid grid-cols-[9rem_1fr_2fr] gap-3 items-baseline text-xs">
                  <span className={`font-mono font-semibold ${accent.text}`}>{f.name}</span>
                  <span className="font-mono text-slate-400">{f.type}</span>
                  <span className="text-slate-300">{f.note}</span>
                </div>
              ))}
            </div>
          </Panel>
          <Panel title={`Persisted snapshot · thread_id = ${data.thread_id}`}>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
              {[
                ['messages', snap.messages], ['cursor', snap.cursor],
                ['plan len', (snap.plan || []).length], ['findings', snap.findings],
                ['tool_outputs', snap.tool_outputs], ['compactions', snap.compaction_count],
              ].map(([k, v]) => (
                <div key={k} className="rounded-md bg-black/30 ring-1 ring-white/10 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">{k}</div>
                  <div className={`font-mono ${accent.text}`}>{String(v)}</div>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-slate-500 mt-3">next node → <span className={`font-mono ${accent.text}`}>{JSON.stringify(snap.next)}</span></p>
            {(data.messages_preview || []).length > 0 && (
              <div className="mt-3 rounded-md bg-black/20 p-2 space-y-1">
                {data.messages_preview.map((m, i) => (
                  <p key={i} className="text-[11px]"><span className={`font-mono font-bold ${accent.text}`}>{m.role}:</span> <span className="text-slate-300">{m.text}</span></p>
                ))}
              </div>
            )}
          </Panel>
        </div>
      )
    }

    case 'memory_checkpointer':
      return (
        <div className="space-y-3">
          <Panel title={`Checkpointer + thread_id = ${data.thread_id}`}>
            <p className="text-[11px] text-slate-500 mb-3">Same <span className="font-mono text-slate-200">thread_id</span>, two separate <span className="font-mono text-slate-200">.invoke()</span> calls. The 2nd call had ZERO context of its own — the checkpointer replayed turn 1's messages from <span className="font-mono text-slate-200">{data.checkpoint_file}</span>.</p>
            <div className="space-y-2">
              <div className="rounded-md bg-black/30 ring-1 ring-white/10 p-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Turn 1 · user set a fact</div>
                <p className="text-sm text-slate-200">{data.turn1}</p>
              </div>
              <div className={`rounded-md ${accent.bg} ${accent.ring} ring-1 p-3`}>
                <div className={`text-[10px] uppercase tracking-wider ${accent.text} mb-1`}>Turn 2 · agent recalls it purely from the checkpoint</div>
                <p className="text-sm text-emerald-300">{data.turn2}</p>
              </div>
            </div>
            <p className="text-[11px] text-slate-500 mt-3">persisted messages on disk: <span className={`font-mono ${accent.text}`}>{data.persisted_messages}</span></p>
          </Panel>
        </div>
      )

    case 'memory_long':
      return (
        <div className="space-y-3">
          <Panel title="Saved to long-term vector store">
            <ul className="text-sm text-slate-200 space-y-1">{(data.saved || []).map((s, i) => <li key={i}>• {s}</li>)}</ul>
          </Panel>
          <Panel title={`Recall (query: “${data.query}”)`}>
            <p className="text-[11px] text-slate-500 mb-2">The store returns semantically NEAREST facts — not keyword matches — via the same Chroma retriever Day 2 uses for documents.</p>
            <ul className="text-sm text-emerald-300 space-y-1">{(data.recall || []).map((h, i) => <li key={i}>✓ {h}</li>)}</ul>
          </Panel>
        </div>
      )

    case 'memory_compaction': {
      const b = data.before || {}
      const a = data.after || {}
      const shrink = b.tokens > 0 ? Math.round((1 - a.tokens / b.tokens) * 100) : 0
      return (
        <div className="space-y-3">
          <Panel title={`Compaction · threshold ${data.threshold}, keep last ${data.keep_last}`}>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div className="rounded-lg bg-black/30 ring-1 ring-white/10 p-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">BEFORE</div>
                <div className="font-mono text-lg text-slate-200">{b.count} msgs · ~{b.tokens} tok</div>
              </div>
              <div className={`rounded-lg ${accent.bg} ${accent.ring} ring-1 p-3`}>
                <div className={`text-[10px] uppercase tracking-wider ${accent.text}`}>AFTER</div>
                <div className={`font-mono text-lg ${accent.text}`}>{a.count} msgs · ~{a.tokens} tok</div>
              </div>
            </div>
            <p className="text-xs text-emerald-300">↓ shrunk by <span className="font-bold">{shrink}%</span> — the older turns became one system summary; last {data.keep_last} kept verbatim.</p>
          </Panel>
          <Panel title="Summary message that replaced the oldest turns">
            <p className="text-sm text-slate-200 whitespace-pre-wrap">{data.summary}</p>
          </Panel>
          <Panel title="Message list after compaction">
            <div className="rounded-md bg-black/20 p-2 space-y-1">
              {(a.messages || []).map((m, i) => (
                <p key={i} className="text-[11px]"><span className={`font-mono font-bold ${accent.text}`}>{m.role}:</span> <span className="text-slate-300">{m.text}</span></p>
              ))}
            </div>
          </Panel>
        </div>
      )
    }

    case 'memory_crash': {
      const s = data.state_on_disk || {}
      return (
        <div className="space-y-3">
          <Panel title={`Run 1 — plan → step 1 → 💥 crash · thread_id = ${data.thread_id}`}>
            <ol className="space-y-1.5">
              {(data.steps || []).map((st, i) => {
                const bad = st.outcome === 'CRASH'
                return (
                  <li key={i} className={`flex items-start gap-2 rounded-md ring-1 px-2 py-1.5 text-xs ${bad ? 'bg-rose-500/10 ring-rose-500/30' : 'bg-black/20 ring-white/10'}`}>
                    <span className={`shrink-0 inline-flex h-5 w-5 items-center justify-center rounded font-bold ${bad ? 'bg-rose-500/30 text-rose-200' : `${accent.bg} ${accent.text}`}`}>{i + 1}</span>
                    <div>
                      <div className={`font-mono font-semibold ${bad ? 'text-rose-200' : 'text-slate-200'}`}>{st.node} · {st.outcome}</div>
                      <div className="text-[11px] text-slate-400">{st.note}</div>
                    </div>
                  </li>
                )
              })}
            </ol>
            {data.crash && <p className="mt-2 text-[11px] text-rose-300 font-mono">raised: {data.crash}</p>}
          </Panel>
          <Panel title="State on disk after the crash (the whole point)">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="rounded-md bg-black/30 ring-1 ring-white/10 px-3 py-2">
                <div className="text-[10px] uppercase text-slate-500">plan len</div>
                <div className={`font-mono ${accent.text}`}>{(s.plan || []).length}</div>
              </div>
              <div className="rounded-md bg-black/30 ring-1 ring-white/10 px-3 py-2">
                <div className="text-[10px] uppercase text-slate-500">cursor</div>
                <div className={`font-mono ${accent.text}`}>{s.cursor}</div>
              </div>
              <div className="rounded-md bg-black/30 ring-1 ring-white/10 px-3 py-2">
                <div className="text-[10px] uppercase text-slate-500">findings</div>
                <div className={`font-mono ${accent.text}`}>{s.findings}</div>
              </div>
              <div className="rounded-md bg-black/30 ring-1 ring-white/10 px-3 py-2">
                <div className="text-[10px] uppercase text-slate-500">next</div>
                <div className={`font-mono ${accent.text}`}>{JSON.stringify(s.next)}</div>
              </div>
            </div>
            <p className="text-[11px] text-slate-500 mt-3">dedup keys already checkpointed: <span className="font-mono text-slate-300">{JSON.stringify(s.tool_outputs_keys || [])}</span></p>
            <p className="text-[11px] text-amber-300 mt-2">👉 Now click <span className="font-semibold">P6 · Resume</span> — the SAME thread_id will pick up from cursor {s.cursor}.</p>
          </Panel>
        </div>
      )
    }

    case 'memory_resume': {
      if (data.error) {
        return <Panel title="Resume"><p className="text-sm text-amber-300">{data.error}</p></Panel>
      }
      const b = data.before || {}
      const a = data.after || {}
      return (
        <div className="space-y-3">
          <Panel title={`Run 2 · SAME thread_id = ${data.thread_id}`}>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-black/30 ring-1 ring-white/10 p-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Before resume (loaded from disk)</div>
                <div className="text-xs text-slate-300">cursor: <span className={`font-mono ${accent.text}`}>{b.cursor}</span></div>
                <div className="text-xs text-slate-300">findings: <span className={`font-mono ${accent.text}`}>{b.findings}</span></div>
                <div className="text-xs text-slate-300">next: <span className={`font-mono ${accent.text}`}>{JSON.stringify(b.next)}</span></div>
              </div>
              <div className={`rounded-lg ${accent.bg} ${accent.ring} ring-1 p-3`}>
                <div className={`text-[10px] uppercase tracking-wider ${accent.text} mb-1`}>After resume (graph continued)</div>
                <div className="text-xs text-slate-300">cursor: <span className={`font-mono ${accent.text}`}>{a.cursor}</span></div>
                <div className="text-xs text-slate-300">findings: <span className={`font-mono ${accent.text}`}>{a.findings}</span></div>
                <div className="text-xs text-emerald-300">idempotent: <span className="font-mono">✓ no double-fire</span></div>
              </div>
            </div>
            <p className="text-[11px] text-slate-500 mt-3">Passing <span className="font-mono text-slate-300">None</span> to <span className="font-mono text-slate-300">.invoke()</span> tells LangGraph: don't push new input, just continue from the persisted checkpoint. The <span className="font-mono text-slate-300">act</span> node's dedup keys prevent replayed steps from re-calling the LLM.</p>
          </Panel>
          {(data.findings || []).length > 0 && (
            <Panel title="Findings (survived the crash + gathered post-resume)">
              <ul className="space-y-1 text-sm text-slate-200">
                {data.findings.map((f, i) => (
                  <li key={i} className="rounded bg-black/20 p-2">
                    <div className={`text-[11px] font-semibold ${accent.text}`}>{f.sub_question}</div>
                    <div className="text-xs text-slate-300 mt-0.5">{f.answer}</div>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
          {data.final && <Panel title="Final answer"><ReportView text={data.final} /></Panel>}
        </div>
      )
    }

    case 'memory_long_legacy':
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

/*
 * StepFlow — numbered vertical processing pipeline used across Day 4 tabs.
 *
 * Each step:
 *   {
 *     n:     number shown in the circle
 *     kind:  input | decision | action | output | success | failure | note
 *     title: short bold header
 *     hint:  optional small grey subtitle
 *     body:  arbitrary React node (the actual content)
 *   }
 *
 * The visual identity is: a circled number on the left, a colored vertical
 * connector line between steps, and a colored border on the body card
 * (green success / red failure / amber decision / slate action).
 * This gives every Day-4 demo the same "look at the pipeline" feel while the
 * step contents themselves stay very different per tab.
 */
function StepFlow({ steps, accent }) {
  const TONES = {
    input:    { ring: 'ring-slate-500/40',   badge: 'bg-slate-700 text-slate-100',           bar: 'bg-slate-600' },
    decision: { ring: 'ring-amber-500/40',   badge: 'bg-amber-500/20 text-amber-200',        bar: 'bg-amber-500/50' },
    action:   { ring: 'ring-sky-500/40',     badge: 'bg-sky-500/20 text-sky-200',            bar: 'bg-sky-500/50' },
    output:   { ring: 'ring-violet-500/40',  badge: 'bg-violet-500/20 text-violet-200',      bar: 'bg-violet-500/50' },
    success:  { ring: 'ring-emerald-500/40', badge: 'bg-emerald-500/20 text-emerald-200',    bar: 'bg-emerald-500/50' },
    failure:  { ring: 'ring-rose-500/40',    badge: 'bg-rose-500/20 text-rose-200',          bar: 'bg-rose-500/50' },
    note:     { ring: 'ring-white/10',       badge: `${accent?.bg || 'bg-white/10'} ${accent?.text || 'text-slate-200'}`, bar: 'bg-white/10' },
  }
  const KIND_LABEL = {
    input: 'input', decision: 'decision', action: 'run', output: 'output',
    success: 'success', failure: 'failure', note: 'note',
  }
  return (
    <ol className="relative space-y-3">
      {steps.map((s, i) => {
        const t = TONES[s.kind] || TONES.note
        const isLast = i === steps.length - 1
        return (
          <li key={i} className="relative flex gap-3 animate-fadeInUp" style={{ animationDelay: `${i * 40}ms` }}>
            {/* left rail: number badge + connector */}
            <div className="flex flex-col items-center shrink-0">
              <div className={`flex h-9 w-9 items-center justify-center rounded-full ${t.badge} ring-1 ${t.ring} font-bold text-sm shadow`}>
                {s.n ?? (i + 1)}
              </div>
              {!isLast && <div className={`w-0.5 flex-1 mt-1 ${t.bar} opacity-70`} style={{ minHeight: '1.5rem' }} />}
            </div>
            {/* right side: content card */}
            <div className={`flex-1 rounded-xl bg-slate-900/40 ring-1 ${t.ring} p-3 mb-1`}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-bold text-slate-100">{s.title}</span>
                <span className={`ml-auto rounded px-1.5 py-0.5 text-[10px] uppercase font-bold tracking-wider ${t.badge}`}>
                  {KIND_LABEL[s.kind] || s.kind || 'step'}
                </span>
              </div>
              {s.hint && <p className="text-[11px] text-slate-500 mb-2">{s.hint}</p>}
              {s.body && <div className="text-xs text-slate-200">{s.body}</div>}
            </div>
          </li>
        )
      })}
    </ol>
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
