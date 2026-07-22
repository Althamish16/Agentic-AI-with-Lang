import CapstoneRunner from './CapstoneRunner.jsx'

// The Studio tab is now a thin shell around CapstoneRunner — the same live,
// SSE-driven, human-in-the-loop capstone experience is also embedded inside
// Day 7 · M6 · Full run (via DayResult -> live_capstone), so there's exactly
// one source of truth for the interactive HITL flow.
export default function StudioTab() {
  return <CapstoneRunner threadPrefix="studio" showQuestionBar autoRun={false} />
}
