'use client'

import { useState, useRef, useCallback } from 'react'
import { streamResearch } from '@/lib/api'
import type { PipelineState, ResearchResult, AgentDoneEvent } from '@/types/research'
import { marked } from 'marked'
import Link from 'next/link'
import posthog from 'posthog-js'


const AGENTS = ['planner', 'search', 'rag', 'writer', 'critic'] as const

const AGENT_META = {
  planner: { icon: '🧠', label: 'Planner' },
  search: { icon: '🔍', label: 'Search' },
  rag: { icon: '📚', label: 'RAG' },
  writer: { icon: '✍️', label: 'Writer' },
  critic: { icon: '🎯', label: 'Critic' },
}

const initialPipeline: PipelineState = {
  planner: 'idle', search: 'idle', rag: 'idle', writer: 'idle', critic: 'idle',
}

// Writer active state color — use inline style instead of Tailwind
// dynamic class so it works reliably in production builds
function agentBg(status: string): React.CSSProperties {
  if (status === 'done') return { background: '#0a0a0a' }
  if (status === 'active') return { background: '#ede8dc' }
  return { background: '#ffffff' }
}

function agentTextColor(status: string): React.CSSProperties {
  if (status === 'done') return { color: '#f5f0e8' }
  if (status === 'active') return { color: '#0a0a0a' }
  return { color: '#7a7165' }
}

export default function Home() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [pipeline, setPipeline] = useState<PipelineState>(initialPipeline)
  const [result, setResult] = useState<ResearchResult | null>(null)
  const [liveReport, setLiveReport] = useState('')
  const [error, setError] = useState('')
  const [subtasks, setSubtasks] = useState<string[]>([])
  const outputRef = useRef<HTMLDivElement>(null)

  const setAgentStatus = useCallback((agent: string, status: 'active' | 'done') => {
    setPipeline(prev => ({ ...prev, [agent]: status }))
  }, [])

  // reset all state properly before each new research
  function resetState() {
    setResult(null)
    setLiveReport('')
    setError('')
    setSubtasks([])
    setPipeline(initialPipeline)
  }

  async function handleSubmit() {
    if (!query.trim() || loading) return

    resetState()
    setLoading(true)

    posthog.capture('research_started', { query })

    // Activate first agent immediately
    setAgentStatus('planner', 'active')

    try {
      for await (const { event, data } of streamResearch(query)) {

        if (event === 'agent_done') {
          const d = data as AgentDoneEvent

          // Mark current agent done
          setAgentStatus(d.agent, 'done')

          // Capture data from each agent
          if (d.subtasks && d.subtasks.length > 0) setSubtasks(d.subtasks)
          if (d.report && d.report.length > 0) setLiveReport(d.report)

          // Activate next agent in pipeline
          const idx = AGENTS.indexOf(d.agent as typeof AGENTS[number])
          if (idx >= 0 && idx < AGENTS.length - 1) {
            setAgentStatus(AGENTS[idx + 1], 'active')
          }
        }

        // complete event — set result AND re-enable button
        if (event === 'complete') {
          const completeData = data as ResearchResult
          setResult(completeData)
          posthog.capture('research_completed', {
            query: completeData.query,
            quality_score: completeData.quality_score?.total,
            duration_seconds: completeData.duration_seconds,
            total_tokens: completeData.total_tokens,
            thread_id: completeData.thread_id,
          })
          setLoading(false)
          AGENTS.forEach(a => setAgentStatus(a, 'done'))

          // save to localStorage
          const historyItem = {
            thread_id: completeData.thread_id,
            query: completeData.query,
            quality_score: completeData.quality_score?.total ?? 0,
            finished_at: completeData.duration_seconds
              ? Math.floor(Date.now() / 1000)
              : Math.floor(Date.now() / 1000),
          }
          const existing = JSON.parse(localStorage.getItem('autoresearch_history') || '[]')
          existing.unshift(historyItem)
          localStorage.setItem('autoresearch_history', JSON.stringify(existing.slice(0, 50)))

          setTimeout(() => {
            outputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }, 150)
        }

        if (event === 'error') {
          setError(data.message || 'An error occurred. Please try again.')
          setLoading(false)   // ← re-enables button on error too
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to connect to API. Make sure the backend is running.')
      setLoading(false)   // ← re-enables button on exception too
    }
  }

  // Show report body as soon as writer finishes, even before complete event
  const reportToShow = result?.report || liveReport

  return (
    <div className="min-h-screen" style={{ background: 'var(--paper)' }}>

      {/* ── Header ─────────────────────────────────────────── */}
      <header className="border-b px-8 py-6 flex items-end justify-between"
        style={{ borderColor: 'var(--border)' }}>
        <div>
          <h1 className="font-serif text-4xl tracking-tight">
            Auto<em className="italic" style={{ color: 'var(--accent)' }}>Research</em>
          </h1>
          <p className="font-mono text-xs mt-1 tracking-widest uppercase"
            style={{ color: 'var(--muted)' }}>
            Multi-Agent Research System · Claude Sonnet · LangGraph
          </p>
        </div>
        <div className="hidden md:flex gap-2">
          {AGENTS.map(a => (
            <span key={a} className="font-mono text-xs px-2 py-1 border rounded-sm"
              style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
              {AGENT_META[a].label}
            </span>
          ))}
        </div>
        <Link href="/history"
          className="font-mono text-xs uppercase tracking-widest px-4 py-2 border ml-4"
          style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
          History
        </Link>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-12">

        {/* ── Search box ──────────────────────────────────── */}
        <div className="mb-10">
          <label className="font-mono text-xs uppercase tracking-widest mb-2 block"
            style={{ color: 'var(--muted)' }}>
            Research Query
          </label>
          <div className="flex border-2 bg-white transition-all"
            style={{
              borderColor: loading ? 'var(--muted)' : 'var(--ink)',
              boxShadow: loading ? '4px 4px 0 var(--muted)' : '4px 4px 0 #0a0a0a',
            }}>
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="Ask anything — What is the state of nuclear fusion in 2025?"
              className="flex-1 px-4 py-3 outline-none font-serif text-lg bg-transparent placeholder:italic"
              style={{ color: 'var(--ink)', caretColor: 'var(--accent)' }}
              disabled={loading}
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !query.trim()}
              className="px-6 font-mono text-xs uppercase tracking-widest transition-colors"
              style={{
                background: loading ? 'var(--muted)' : 'var(--ink)',
                color: 'var(--paper)',
                opacity: (!loading && query.trim()) ? 1 : 0.6,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Researching…' : 'Research →'}
            </button>
          </div>
        </div>

        {/* ── Pipeline ────────────────────────────────────── */}
        {(loading || result) && (
          <div className="mb-8">
            <p className="font-mono text-xs uppercase tracking-widest mb-3"
              style={{ color: 'var(--muted)' }}>
              Agent Pipeline
            </p>
            <div className="flex border bg-white overflow-hidden"
              style={{ borderColor: 'var(--border)' }}>
              {AGENTS.map((agent, i) => {
                const status = pipeline[agent]
                return (
                  <div
                    key={`${agent}-${i}`}
                    className="flex-1 py-3 text-center border-r last:border-r-0 transition-colors duration-300"
                    style={{ ...agentBg(status), borderColor: 'var(--border)' }}
                  >
                    <div className={`text-lg mb-1 ${status === 'active' ? 'animate-pulse' : ''}`}>
                      {AGENT_META[agent].icon}
                      {status === 'done' && <span className="text-xs"> ✓</span>}
                    </div>
                    <div className="font-mono text-xs uppercase tracking-wider"
                      style={agentTextColor(status)}>
                      {AGENT_META[agent].label}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* ── Live subtasks ────────────────────────────────── */}
        {loading && subtasks.length > 0 && (
          <div className="mb-6 border bg-white p-4" style={{ borderColor: 'var(--border)' }}>
            <p className="font-mono text-xs uppercase tracking-widest mb-2"
              style={{ color: 'var(--muted)' }}>
              Researching
            </p>
            <ul className="space-y-1">
              {subtasks.map((t, i) => (
                <li key={`live-subtask-${i}`} className="flex gap-2 text-sm"
                  style={{ color: 'var(--ink)' }}>
                  <span className="font-mono text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                    0{i + 1}
                  </span>
                  {t}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* ── Error ───────────────────────────────────────── */}
        {error && (
          <div className="mb-6 p-4 border font-mono text-sm"
            style={{ borderColor: 'var(--accent)', background: '#fff5f3', color: 'var(--accent)' }}>
            ⚠ {error}
          </div>
        )}

        {/* ── Output ──────────────────────────────────────── */}
        {reportToShow && (
          <div ref={outputRef}>

            {/* Meta row — only shown after complete */}
            {result && (
              <div className="flex items-center justify-between mb-4 pb-3 border-b"
                style={{ borderColor: 'var(--border)' }}>
                <h2 className="font-serif text-lg">Research Report</h2>
                <div className="flex gap-2 flex-wrap justify-end">
                  <span className="font-mono text-xs px-2 py-1 rounded-sm"
                    style={{ background: 'var(--cream)', color: 'var(--muted)' }}>
                    {result.duration_seconds}s
                  </span>
                  <span className="font-mono text-xs px-2 py-1 rounded-sm"
                    style={{ background: 'var(--cream)', color: 'var(--muted)' }}>
                    {result.total_tokens} tokens
                  </span>
                  <span className="font-mono text-xs px-2 py-1 rounded-sm"
                    style={{ background: 'var(--ink)', color: 'var(--paper)' }}>
                    {result.quality_score?.total}/30
                  </span>
                </div>
              </div>
            )}

            {/* Report body */}
            <div
              className="bg-white border p-8 mb-4 report-content"
              style={{ borderColor: 'var(--border)', boxShadow: '3px 3px 0 var(--border)' }}
              dangerouslySetInnerHTML={{ __html: marked(reportToShow) as string }}
            />

            {/* Bottom panels — only after complete */}
            {result && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">

                  {/* Quality score */}
                  <div className="bg-white border p-4" style={{ borderColor: 'var(--border)' }}>
                    <p className="font-mono text-xs uppercase tracking-widest mb-3"
                      style={{ color: 'var(--muted)' }}>Quality Score</p>
                    {(['completeness', 'accuracy', 'coherence'] as const).map((k, i) => (
                      <div key={`score-${k}-${i}`} className="flex items-center gap-2 mb-2">
                        <span className="text-sm w-24 capitalize">{k}</span>
                        <div className="flex-1 h-1 rounded-full overflow-hidden"
                          style={{ background: 'var(--cream)' }}>
                          <div className="h-full rounded-full transition-all duration-1000"
                            style={{
                              width: `${((result.quality_score?.[k] ?? 0) / 10) * 100}%`,
                              background: 'var(--ink)',
                            }} />
                        </div>
                        <span className="font-mono text-xs w-8 text-right"
                          style={{ color: 'var(--muted)' }}>
                          {result.quality_score?.[k] ?? 0}/10
                        </span>
                      </div>
                    ))}
                    <div className="mt-3 pt-2 border-t flex justify-between items-center"
                      style={{ borderColor: 'var(--border)' }}>
                      <span className="font-mono text-xs uppercase tracking-wider"
                        style={{ color: 'var(--muted)' }}>Total</span>
                      <span className="font-serif text-2xl">
                        {result.quality_score?.total ?? 0}/30
                      </span>
                    </div>
                    {result.quality_score?.feedback && (
                      <div className="mt-3 pt-2 border-t" style={{ borderColor: 'var(--border)' }}>
                        <p className="font-mono text-xs uppercase tracking-widest mb-1"
                          style={{ color: 'var(--accent)' }}>
                          Critic's Verdict
                        </p>
                        <p className="text-sm italic" style={{ color: 'var(--ink)', lineHeight: 1.6 }}>
                          {result.quality_score.feedback}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Agent metrics */}
                  <div className="bg-white border p-4" style={{ borderColor: 'var(--border)' }}>
                    <p className="font-mono text-xs uppercase tracking-widest mb-3"
                      style={{ color: 'var(--muted)' }}>Agent Metrics</p>
                    <table className="w-full text-xs font-mono">
                      <thead>
                        <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                          <th className="text-left pb-2" style={{ color: 'var(--muted)' }}>Agent</th>
                          <th className="text-right pb-2" style={{ color: 'var(--muted)' }}>Latency</th>
                          <th className="text-right pb-2" style={{ color: 'var(--muted)' }}>Tokens</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(result.metrics ?? []).map((m, i) => (
                          <tr key={`metric-${m.agent}-${i}`} className="border-b last:border-b-0"
                            style={{ borderColor: 'var(--cream)' }}>
                            <td className="py-1.5 capitalize">{m.agent}</td>
                            <td className="py-1.5 text-right">{Math.round(m.latency_ms)}ms</td>
                            <td className="py-1.5 text-right">{m.tokens_used || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Subtasks */}
                <div className="bg-white border p-4" style={{ borderColor: 'var(--border)' }}>
                  <p className="font-mono text-xs uppercase tracking-widest mb-3"
                    style={{ color: 'var(--muted)' }}>Research Subtasks</p>
                  <ul className="space-y-2">
                    {(result.subtasks ?? []).map((t, i) => (
                      <li key={`subtask-${i}`}
                        className="flex gap-2 text-sm border-b last:border-b-0 pb-2 last:pb-0"
                        style={{ borderColor: 'var(--cream)' }}>
                        <span className="font-mono text-xs mt-0.5 shrink-0"
                          style={{ color: 'var(--muted)' }}>
                          0{i + 1}
                        </span>
                        {t}
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
