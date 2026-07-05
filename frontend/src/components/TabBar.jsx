import { DAYS } from '../data/days.js'

const TABS = [
  { key: 'overview', label: 'Overview' },
  ...DAYS.map((d) => ({ key: d.key, label: `Day ${d.n}` })),
  { key: 'studio', label: 'Studio ▶' },
]

export default function TabBar({ active, onChange }) {
  return (
    <nav className="flex gap-1 overflow-x-auto pb-1">
      {TABS.map((t) => {
        const on = active === t.key
        const isStudio = t.key === 'studio'
        return (
          <button
            key={t.key}
            onClick={() => onChange(t.key)}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              on
                ? isStudio
                  ? 'bg-gradient-to-r from-brand-500 to-fuchsia-500 text-white shadow-lg shadow-brand-500/30'
                  : 'bg-white/10 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            {t.label}
          </button>
        )
      })}
    </nav>
  )
}
