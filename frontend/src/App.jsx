import { useEffect, useState } from 'react'
import { DAYS } from './data/days.js'
import DayTab from './components/DayTab.jsx'
import OverviewTab from './components/OverviewTab.jsx'
import StudioTab from './components/StudioTab.jsx'
import TabBar from './components/TabBar.jsx'
import { IconSpark } from './components/Icons.jsx'

export default function App() {
  const [active, setActive] = useState('overview')
  const [health, setHealth] = useState(null)

  useEffect(() => {
    fetch('/api/health').then((r) => r.json()).then(setHealth).catch(() => {})
  }, [])

  const day = DAYS.find((d) => d.key === active)

  return (
    <div className="min-h-full flex flex-col">
      {/* Shell header */}
      <header className="sticky top-0 z-20 border-b border-white/10 bg-[#0b1020]/80 backdrop-blur px-4 sm:px-6 py-3">
        <div className="mx-auto max-w-6xl">
          <div className="flex items-center justify-between gap-4">
            <button onClick={() => setActive('overview')} className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-fuchsia-500 text-white shadow-lg shadow-brand-500/30">
                <IconSpark width={20} height={20} />
              </span>
              <div className="text-left">
                <h1 className="text-base font-extrabold tracking-tight bg-gradient-to-r from-brand-300 to-fuchsia-300 bg-clip-text text-transparent">
                  Research Assistant Studio
                </h1>
                <p className="text-[11px] text-slate-400">Agentic AI with LangChain × LangGraph</p>
              </div>
            </button>
            {health && (
              <div className="hidden md:flex flex-wrap items-center gap-2 text-[11px]">
                <Chip label={`LLM: ${health.config.llm_provider}`} />
                <Chip label={health.config.azure_chat_deployment || health.config.openai_model} />
                <Chip label={`embed: ${health.config.embeddings_provider}`} />
                <Chip label={`LangSmith: ${health.langsmith ? 'on' : 'off'}`} tone={health.langsmith ? 'good' : 'muted'} />
              </div>
            )}
          </div>
          <div className="mt-3">
            <TabBar active={active} onChange={setActive} />
          </div>
        </div>
      </header>

      {/* Tab content */}
      <main className="px-4 sm:px-6 py-6 flex-1">
        <div className="mx-auto max-w-6xl">
          {active === 'overview' && <OverviewTab onNavigate={setActive} />}
          {active === 'studio' && <StudioTab />}
          {day && <DayTab key={day.key} day={day} />}
        </div>
      </main>

      <footer className="px-6 py-4 text-center text-xs text-slate-600">
        Research Assistant Labs · learn each station on Days 1–7, then watch the whole kitchen run in the Studio
      </footer>
    </div>
  )
}

function Chip({ label, tone }) {
  const tones = {
    good: 'bg-emerald-500/15 text-emerald-300 border-emerald-400/30',
    muted: 'bg-slate-700/40 text-slate-400 border-white/10',
  }
  return <span className={`rounded-full border px-2.5 py-1 font-medium ${tones[tone] || 'bg-white/5 text-slate-300 border-white/10'}`}>{label}</span>
}
