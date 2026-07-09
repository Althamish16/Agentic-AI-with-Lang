import { useRef, useState } from 'react'
import { IconBolt, IconDoc } from './Icons.jsx'

// ─────────────────────────────────────────────────────────────────────────────
// Day2Upload — the DYNAMIC part of Day 2: drop in your own .txt/.md/.pdf files,
// POST them to /api/day2/ingest, and watch the indexing pipeline run LIVE and
// TRANSPARENTLY (load → split → embed → store), stage by stage. On success we
// hand the parent a session id; every Day-2 tab then retrieves from YOUR files.
// ─────────────────────────────────────────────────────────────────────────────
export default function Day2Upload({ accent, corpus, onIndexed, onClear }) {
  const [files, setFiles] = useState([])
  const [busy, setBusy] = useState(false)
  const [stages, setStages] = useState(null)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  function pick(list) {
    setError('')
    setFiles(Array.from(list || []))
  }

  async function index() {
    if (!files.length) return
    setBusy(true); setError(''); setStages(null)
    try {
      const fd = new FormData()
      files.forEach((f) => fd.append('files', f))
      const r = await fetch('/api/day2/ingest', { method: 'POST', body: fd })
      const data = await r.json()
      if (data.error) { setError(data.error); return }
      setStages(data.stages)
      onIndexed(data.session, data.meta)
    } catch (e) {
      setError(`Backend unreachable on :5000 — is it running? (${e})`)
    } finally {
      setBusy(false)
    }
  }

  function reset() {
    setFiles([]); setStages(null); setError('')
    if (inputRef.current) inputRef.current.value = ''
    onClear()
  }

  return (
    <div className="glass rounded-2xl p-5 space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h3 className="text-sm font-bold text-slate-100">📤 Use your own documents</h3>
          <p className="mt-1 text-[11px] text-slate-500">
            Upload .txt / .md / .pdf files — watch them get indexed live, then every tab below runs on YOUR corpus.
          </p>
        </div>
        {corpus && (
          <span className={`shrink-0 rounded-full ${accent.bg} ${accent.ring} ring-1 px-3 py-1 text-[11px] font-semibold ${accent.text}`}>
            ● now running on your {corpus.files?.length} file(s) · {corpus.chunks} chunks
          </span>
        )}
      </div>

      {/* Dropzone-style picker */}
      <label
        htmlFor="day2-files"
        className="flex flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed border-white/15 hover:border-white/30 bg-black/20 px-4 py-6 cursor-pointer transition"
      >
        <span className="text-2xl">🗂️</span>
        <span className="text-sm text-slate-200 font-medium">Click to choose files</span>
        <span className="text-[11px] text-slate-500">.txt · .md · .pdf — up to 8 files</span>
        <input
          id="day2-files"
          ref={inputRef}
          type="file"
          multiple
          accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf"
          className="hidden"
          onChange={(e) => pick(e.target.files)}
        />
      </label>

      {/* Selected files */}
      {files.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          {files.map((f, i) => (
            <span key={i} className="inline-flex items-center gap-1 rounded-md bg-white/5 border border-white/10 px-2 py-1 text-[11px] text-slate-300">
              <IconDoc width={11} height={11} /> {f.name} <span className="text-slate-500">· {(f.size / 1024).toFixed(0)} KB</span>
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={index}
          disabled={busy || !files.length}
          className={`inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-r ${accent.grad} px-4 py-2 text-sm font-semibold text-white shadow disabled:opacity-40 transition`}
        >
          <IconBolt width={15} height={15} /> {busy ? 'Indexing…' : 'Index my files'}
        </button>
        {(corpus || stages) && (
          <button onClick={reset} className="text-xs text-slate-400 hover:text-slate-200 underline underline-offset-2">
            ↺ back to built-in sample docs
          </button>
        )}
      </div>

      {busy && (
        <div className="h-2.5 w-1/3 rounded bg-white/10 overflow-hidden relative">
          <span className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/25 to-transparent" />
        </div>
      )}

      {error && (
        <div className="rounded-xl bg-red-500/10 ring-1 ring-red-500/40 p-3 text-sm text-red-200">{error}</div>
      )}

      {/* LIVE, TRANSPARENT pipeline trace — one card per stage, cascaded in */}
      {stages && <PipelineTrace stages={stages} accent={accent} />}
    </div>
  )
}

// The indexing phase, made visible: load → split → embed → store, each with the
// real numbers from the backend. Cascades in so the room sees it run "live".
function PipelineTrace({ stages, accent }) {
  return (
    <div className="space-y-2 pt-1">
      <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
        Indexing pipeline — what just happened to your files
      </div>
      <div className="relative pl-5">
        <span className="absolute left-[7px] top-1 bottom-1 w-px bg-white/10" />
        {stages.map((s, i) => (
          <div key={s.stage} className="relative mb-2 animate-fadeInUp" style={{ animationDelay: `${i * 180}ms` }}>
            <span className={`absolute -left-5 top-1.5 h-3.5 w-3.5 rounded-full bg-gradient-to-br ${accent.grad} ring-4 ring-slate-950`} />
            <div className="rounded-xl bg-black/25 border border-white/5 px-3 py-2">
              <div className="flex items-baseline justify-between gap-2">
                <span className={`text-sm font-bold ${accent.text}`}>{s.label}</span>
                <span className="text-xs text-slate-300">{s.detail}</span>
              </div>

              {s.items && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {s.items.map((it, j) => (
                    <span key={j} className="inline-flex items-center gap-1 rounded-md bg-white/5 px-1.5 py-0.5 text-[11px] text-slate-300">
                      <IconDoc width={10} height={10} /> {it.source} <span className="text-slate-500">· {it.chars.toLocaleString()} chars</span>
                    </span>
                  ))}
                </div>
              )}

              {s.sample && (
                <pre className="mt-1.5 overflow-x-auto whitespace-pre-wrap rounded-lg bg-black/40 p-2 text-[11px] text-slate-400">{s.sample}…</pre>
              )}
            </div>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-slate-500">✅ Your corpus is indexed. Now run any tab below — it retrieves from these chunks.</p>
    </div>
  )
}
