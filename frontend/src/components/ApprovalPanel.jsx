import { useState } from 'react'
import ReportView from './ReportView.jsx'
import { IconApprove } from './Icons.jsx'

// The human-in-the-loop gate: shows the draft and lets the reviewer approve or
// send it back with feedback. Wired to POST-like GET /api/resume in App.jsx.
export default function ApprovalPanel({ payload, busy, onApprove, onReject }) {
  const [feedback, setFeedback] = useState('')

  return (
    <div className="glass rounded-2xl p-5 animate-fadeInUp ring-1 ring-amber-400/30">
      <div className="flex items-center gap-2 mb-3">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-amber-400/15 text-amber-300">
          ⏸
        </span>
        <div>
          <h3 className="font-semibold text-amber-200">Human approval required</h3>
          <p className="text-xs text-slate-400">Review the draft below before it is published.</p>
        </div>
      </div>

      {payload?.critique && (
        <div className="mb-3 rounded-lg bg-slate-800/50 p-3 text-xs text-slate-300">
          <span className="font-semibold text-slate-200">Self-critique: </span>
          {payload.critique.slice(0, 400)}
          {payload.critique.length > 400 ? '…' : ''}
        </div>
      )}

      <div className="max-h-64 overflow-y-auto rounded-lg border border-white/5 bg-black/20 p-4 mb-4">
        <ReportView text={payload?.draft} />
      </div>

      <textarea
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder="Optional: request changes (e.g. 'add a concrete example')…"
        className="w-full resize-none rounded-lg bg-slate-900/60 border border-white/10 p-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50 mb-3"
        rows={2}
      />

      <div className="flex flex-wrap gap-2">
        <button
          disabled={busy}
          onClick={() => onApprove()}
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-400 disabled:opacity-50 transition"
        >
          <IconApprove width={16} height={16} /> Approve &amp; publish
        </button>
        <button
          disabled={busy}
          onClick={() => onReject(feedback || 'Please revise and improve the draft.')}
          className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-slate-100 hover:bg-slate-600 disabled:opacity-50 transition"
        >
          Request changes
        </button>
      </div>
    </div>
  )
}
