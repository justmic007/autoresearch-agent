'use client'

import { useState, useRef } from 'react'
import { streamResearch } from '@/lib/api'
import type { PipelineState, ResearchResult, AgentDoneEvent } from '@/types/research'
import { marked } from 'marked'

const AGENTS = ['planner', 'search', 'rag', 'writer', 'critic'] as const

const AGENT_META = {
  planner: { icon: '🧠', label: 'Planner' },
  search: { icon: '🔍', label: 'Search' },
  rag: { icon: '📚', label: 'RAG' },
  writer: { icon: '✍️', label: 'Writer' },
  critic: { icon: '🎯', label: 'Critic' },
}

const initialPipeline: PipelineState = {
  planner: 'idle', search: 'idle', rag: 'idle', writer: 'idle', critic: 'idle'
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

  const setAgentStatus = (agent: string, status: 'active' | 'done') => {
    setPipeline(prev => ({ ...prev, [agent]: status }))
  }

  async function handleSubmit() {
    if (!query.trim() || loading) return
    setLoading(true)
    setResult(null)
    setLiveReport('')
    setError('')
    setSubtasks([])
    setPipeline(initialPipeline)

    try {
      for await (const { event, data } of streamResearch(query)) {
        if (event === 'agent_done') {
          const d = data as AgentDoneEvent
          setAgentStatus(d.agent, 'done')

          if (d.subtasks) setSubtasks(d.subtasks)
          if (d.report) setLiveReport(d.report)

          // Activate next agent
          const idx = AGENTS.indexOf(d.agent as typeof AGENTS[number])
          if (idx >= 0 && idx < AGENTS.length - 1) {
            setAgentStatus(AGENTS[idx + 1], 'active')
          }
        }

        if (event === 'complete') {
          setResult(data as ResearchResult)
          setLoading(false)
          setTimeout(() => outputRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
        }

        if (event === 'error') {
          setError(data.message || 'Unknown error')
          setLoading(false)
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to connect to API')
      setLoading(false)
    }
  }

  const finalResult = result || (liveReport ? { report: liveReport } as ResearchResult : null)

  return (
    <div className="min-h-screen" style={{ background: 'var(--paper)' }}>

      {/* Header */}
      <header className="border-b px-8 py-6 flex items-end justify-between" style={{ borderColor: 'var(--border)' }}>
        <div>
          <h1 className="font-serif text-4xl tracking-tight">
            Auto<em className="italic" style={{ color: 'var(--accent)' }}>Research</em>
          </h1>
          <p className="font-mono text-xs mt-1 tracking-widest uppercase" style={{ color: 'var(--muted)' }}>
            Multi-Agent Research System · Claude Sonnet · LangGraph
          </p>
        </div>
        <div className="hidden md:flex gap-2">
          {AGENTS.map(a => (
            <span key={a} className="font-mono text-xs px-2 py-1 border rounded-sm" style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
              {AGENT_META[a].label}
            </span>
          ))}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-12">

        {/* Search box */}
        <div className="mb-10">
          <label className="font-mono text-xs uppercase tracking-widest mb-2 block" style={{ color: 'var(--muted)' }}>
            Research Query
          </label>
          <div className="flex border-2 bg-white shadow-[4px_4px_0_#0a0a0a] focus-within:shadow-[6px_6px_0_#c84b2f] focus-within:border-[#c84b2f] transition-all" style={{ borderColor: 'var(--ink)' }}>
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
              className="px-6 font-mono text-xs uppercase tracking-widest transition-colors disabled:opacity-50"
              style={{ background: loading ? 'var(--muted)' : 'var(--ink)', color: 'var(--paper)' }}
            >
              {loading ? 'Researching…' : 'Research →'}
            </button>
          </div>
        </div>

        {/* Pipeline */}
        {loading && (
          <div className="mb-8">
            <p className="font-mono text-xs uppercase tracking-widest mb-3" style={{ color: 'var(--muted)' }}>
              Agent Pipeline
            </p>
            <div className="flex border bg-white overflow-hidden" style={{ borderColor: 'var(--border)' }}>
              {AGENTS.map((agent, i) => {
                const status = pipeline[agent]
                return (
                  <div key={agent} className={`flex-1 py-3 text-center border-r last:border-r-0 transition-colors ${status === 'done' ? 'bg-[#0a0a0a]' :
                      status === 'active' ? 'bg-[#ede8dc]' : ''
                    }`} style={{ borderColor: 'var(--border)' }}>
                    <div className={`text-lg mb-1 ${status === 'active' ? 'animate-pulse' : ''}`}>
                      {AGENT_META[agent].icon}
                      {status === 'done' && <span className="text-xs"> ✓</span>}
                    </div>
                    <div className={`font-mono text-xs uppercase tracking-wider ${status === 'done' ? 'text-[var(--paper)]' :
                        status === 'active' ? 'text-[var(--ink)]' : ''
                      }`} style={{ color: status === 'idle' ? 'var(--muted)' : undefined }}>
                      {AGENT_META[agent].label}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Live subtasks while loading */}
        {loading && subtasks.length > 0 && (
          <div className="mb-6 border bg-white p-4" style={{ borderColor: 'var(--border)' }}>
            <p className="font-mono text-xs uppercase tracking-widest mb-2" style={{ color: 'var(--muted)' }}>Researching</p>
            <ul className="space-y-1">
              {subtasks.map((t, i) => (
                <li key={i} className="flex gap-2 text-sm" style={{ color: 'var(--ink)' }}>
                  <span className="font-mono text-xs mt-0.5" style={{ color: 'var(--muted)' }}>0{i + 1}</span>
                  {t}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 border font-mono text-sm" style={{ borderColor: 'var(--accent)', background: '#fff5f3', color: 'var(--accent)' }}>
            Error: {error}
          </div>
        )}

        {/* Output */}
        {finalResult && (
          <div ref={outputRef}>
            {/* Meta row */}
            {result && (
              <div className="flex items-center justify-between mb-4 pb-3 border-b" style={{ borderColor: 'var(--border)' }}>
                <h2 className="font-serif text-lg">Research Report</h2>
                <div className="flex gap-2">
                  <span className="font-mono text-xs px-2 py-1 rounded-sm" style={{ background: 'var(--cream)', color: 'var(--muted)' }}>
                    {result.duration_seconds}s
                  </span>
                  <span className="font-mono text-xs px-2 py-1 rounded-sm" style={{ background: 'var(--cream)', color: 'var(--muted)' }}>
                    {result.total_tokens} tokens
                  </span>
                  <span className="font-mono text-xs px-2 py-1 rounded-sm" style={{ background: 'var(--ink)', color: 'var(--paper)' }}>
                    {result.quality_score?.total}/30
                  </span>
                </div>
              </div>
            )}

            {/* Report body */}
            <div className="bg-white border p-8 shadow-[3px_3px_0_var(--border)] mb-4 report-content" style={{ borderColor: 'var(--border)' }}
              dangerouslySetInnerHTML={{ __html: marked(finalResult.report || '') as string }}
            />

            {/* Bottom panels */}
            {result && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">

                {/* Quality */}
                <div className="bg-white border p-4" style={{ borderColor: 'var(--border)' }}>
                  <p className="font-mono text-xs uppercase tracking-widest mb-3" style={{ color: 'var(--muted)' }}>Quality Score</p>
                  {(['completeness', 'accuracy', 'coherence'] as const).map(k => (
                    <div key={k} className="flex items-center gap-2 mb-2">
                      <span className="text-sm w-24 capitalize">{k}</span>
                      <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'var(--cream)' }}>
                        <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${(result.quality_score[k] / 10) * 100}%`, background: 'var(--ink)' }} />
                      </div>
                      <span className="font-mono text-xs w-8 text-right" style={{ color: 'var(--muted)' }}>{result.quality_score[k]}/10</span>
                    </div>
                  ))}
                  <div className="mt-3 pt-2 border-t flex justify-between items-center" style={{ borderColor: 'var(--border)' }}>
                    <span className="font-mono text-xs uppercase tracking-wider" style={{ color: 'var(--muted)' }}>Total</span>
                    <span className="font-serif text-2xl">{result.quality_score.total}/30</span>
                  </div>
                  <p className="text-xs italic mt-2 pt-2 border-t" style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
                    {result.quality_score.feedback}
                  </p>
                </div>

                {/* Metrics */}
                <div className="bg-white border p-4" style={{ borderColor: 'var(--border)' }}>
                  <p className="font-mono text-xs uppercase tracking-widest mb-3" style={{ color: 'var(--muted)' }}>Agent Metrics</p>
                  <table className="w-full text-xs font-mono">
                    <thead>
                      <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                        <th className="text-left pb-2" style={{ color: 'var(--muted)' }}>Agent</th>
                        <th className="text-right pb-2" style={{ color: 'var(--muted)' }}>Latency</th>
                        <th className="text-right pb-2" style={{ color: 'var(--muted)' }}>Tokens</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.metrics.map(m => (
                        <tr key={m.agent} className="border-b last:border-b-0" style={{ borderColor: 'var(--cream)' }}>
                          <td className="py-1.5 capitalize">{m.agent}</td>
                          <td className="py-1.5 text-right">{Math.round(m.latency_ms)}ms</td>
                          <td className="py-1.5 text-right">{m.tokens_used || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Subtasks */}
            {result && (
              <div className="bg-white border p-4" style={{ borderColor: 'var(--border)' }}>
                <p className="font-mono text-xs uppercase tracking-widest mb-3" style={{ color: 'var(--muted)' }}>Research Subtasks</p>
                <ul className="space-y-2">
                  {result.subtasks.map((t, i) => (
                    <li key={i} className="flex gap-2 text-sm border-b last:border-b-0 pb-2 last:pb-0" style={{ borderColor: 'var(--cream)' }}>
                      <span className="font-mono text-xs mt-0.5 shrink-0" style={{ color: 'var(--muted)' }}>0{i + 1}</span>
                      {t}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}