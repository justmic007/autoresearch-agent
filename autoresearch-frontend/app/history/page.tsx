'use client'

import { useEffect, useState } from 'react'
import { getJob, deleteJob } from '@/lib/api'
import Link from 'next/link'
import { marked } from 'marked'

interface HistoryItem {
    thread_id: string
    query: string
    quality_score: number
    finished_at: number
    report?: string  // stored locally to survive Redis TTL expiry
    quality_score_detail?: {
        total: number
        completeness: number
        accuracy: number
        coherence: number
        feedback: string
    }
}

interface JobResult {
    query: string
    report: string
    finished_at: number
    quality_score: {
        total: number
        completeness: number
        accuracy: number
        coherence: number
        feedback: string
    }
}

const LS_KEY = 'autoresearch_history'

function loadHistory(): HistoryItem[] {
    try {
        const raw = localStorage.getItem(LS_KEY)
        if (!raw) return []
        return (JSON.parse(raw) as HistoryItem[]).sort((a, b) => b.finished_at - a.finished_at)
    } catch {
        return []
    }
}

function saveHistory(jobs: HistoryItem[]) {
    localStorage.setItem(LS_KEY, JSON.stringify(jobs.slice(0, 50)))
}

export default function HistoryPage() {
    const [jobs, setJobs] = useState<HistoryItem[]>([])
    const [selected, setSelected] = useState<JobResult | null>(null)
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const [loading, setLoading] = useState(false)
    const [expired, setExpired] = useState(false)

    useEffect(() => {
        setJobs(loadHistory())
    }, [])

    async function viewJob(job: HistoryItem) {
        setExpired(false)

        // Try localStorage first — survives Redis TTL expiry
        if (job.report) {
            setSelected({
                query: job.query,
                report: job.report,
                finished_at: job.finished_at,
                quality_score: job.quality_score_detail ?? {
                    total: job.quality_score,
                    completeness: 0,
                    accuracy: 0,
                    coherence: 0,
                    feedback: '',
                },
            })
            setSelectedId(job.thread_id)
            return
        }

        // Fall back to API
        setLoading(true)
        setSelected(null)
        setSelectedId(job.thread_id)
        try {
            const data = await getJob(job.thread_id) as JobResult
            setSelected(data)

            // Cache report locally for future views
            const updated = jobs.map(j =>
                j.thread_id === job.thread_id
                    ? { ...j, report: data.report, quality_score_detail: data.quality_score }
                    : j
            )
            setJobs(updated)
            saveHistory(updated)
        } catch {
            setExpired(true)
        } finally {
            setLoading(false)
        }
    }

    function deleteItem(e: React.MouseEvent, thread_id: string) {
        e.stopPropagation()
        const updated = jobs.filter(j => j.thread_id !== thread_id)
        setJobs(updated)
        saveHistory(updated)
        if (selectedId === thread_id) {
            setSelected(null)
            setSelectedId(null)
        }
        // Best-effort delete from Redis too
        deleteJob(thread_id)
    }

    function clearHistory() {
        if (confirm('Clear all history? This cannot be undone.')) {
            jobs.forEach(j => deleteJob(j.thread_id))
            localStorage.removeItem(LS_KEY)
            setJobs([])
            setSelected(null)
            setSelectedId(null)
        }
    }

    function formatDate(ts: number) {
        return new Date(ts * 1000).toLocaleString()
    }

    return (
        <div className="min-h-screen" style={{ background: 'var(--paper)' }}>

            {/* Header */}
            <header className="border-b px-4 md:px-8 py-4 md:py-6 flex items-center justify-between"
                style={{ borderColor: 'var(--border)' }}>
                <div>
                    <h1 className="font-serif text-3xl md:text-4xl tracking-tight">
                        Auto<em className="italic" style={{ color: 'var(--accent)' }}>Research</em>
                    </h1>
                    <p className="font-mono text-xs mt-1 tracking-widest uppercase hidden sm:block"
                        style={{ color: 'var(--muted)' }}>
                        Research History
                    </p>
                </div>
                <div className="flex gap-2 items-center">
                    <Link
                        href="/"
                        className="font-mono text-xs uppercase tracking-widest px-3 py-2 border transition-colors"
                        style={{ borderColor: 'var(--ink)', color: 'var(--ink)' }}>
                        ← New
                    </Link>
                    {jobs.length > 0 && (
                        <button
                            onClick={clearHistory}
                            className="font-mono text-xs uppercase tracking-widest px-3 py-2 border transition-colors"
                            style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}>
                            Clear All
                        </button>
                    )}
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-4 py-10">

                {jobs.length === 0 && !selected ? (
                    <div className="text-center py-24">
                        <p className="font-serif text-2xl mb-3" style={{ color: 'var(--ink)' }}>
                            No research history yet
                        </p>
                        <p className="font-mono text-xs uppercase tracking-widest mb-8"
                            style={{ color: 'var(--muted)' }}>
                            Your completed research jobs will appear here
                        </p>
                        <Link
                            href="/"
                            className="font-mono text-xs uppercase tracking-widest px-6 py-3 inline-block"
                            style={{ background: 'var(--ink)', color: 'var(--paper)' }}>
                            Start Researching →
                        </Link>
                    </div>

                ) : selected ? (
                    <div>
                        <button
                            onClick={() => { setSelected(null); setSelectedId(null); setExpired(false) }}
                            className="font-mono text-xs uppercase tracking-widest mb-6 flex items-center gap-2"
                            style={{ color: 'var(--muted)' }}>
                            ← Back to History
                        </button>

                        <div className="flex items-center justify-between mb-4 pb-3 border-b"
                            style={{ borderColor: 'var(--border)' }}>
                            <h2 className="font-serif text-lg">{selected.query}</h2>
                            <div className="flex gap-2">
                                <span className="font-mono text-xs px-2 py-1 rounded-sm"
                                    style={{ background: 'var(--cream)', color: 'var(--muted)' }}>
                                    {formatDate(selected.finished_at)}
                                </span>
                                <span className="font-mono text-xs px-2 py-1 rounded-sm"
                                    style={{ background: 'var(--ink)', color: 'var(--paper)' }}>
                                    {selected.quality_score?.total}/30
                                </span>
                            </div>
                        </div>

                        <div
                            className="bg-white border p-4 md:p-8 mb-4 report-content"
                            style={{ borderColor: 'var(--border)', boxShadow: '3px 3px 0 var(--border)' }}
                            dangerouslySetInnerHTML={{ __html: marked(selected.report || '') as string }}
                        />

                        {selected.quality_score?.feedback && (
                            <div className="bg-white border p-4 mb-3" style={{ borderColor: 'var(--border)' }}>
                                <p className="font-mono text-xs uppercase tracking-widest mb-1"
                                    style={{ color: 'var(--accent)' }}>
                                    Critic&apos;s Verdict
                                </p>
                                <p className="text-sm italic" style={{ color: 'var(--ink)', lineHeight: 1.6 }}>
                                    {selected.quality_score.feedback}
                                </p>
                            </div>
                        )}
                    </div>

                ) : expired && selectedId ? (
                    <div className="text-center py-24">
                        <p className="font-serif text-2xl mb-3" style={{ color: 'var(--ink)' }}>
                            Report expired
                        </p>
                        <p className="font-mono text-xs uppercase tracking-widest mb-8"
                            style={{ color: 'var(--muted)' }}>
                            This report is no longer available — Redis TTL exceeded 24h
                        </p>
                        <button
                            onClick={() => { setExpired(false); setSelectedId(null) }}
                            className="font-mono text-xs uppercase tracking-widest px-6 py-3"
                            style={{ background: 'var(--ink)', color: 'var(--paper)' }}>
                            ← Back to History
                        </button>
                    </div>

                ) : (
                    <div>
                        <p className="font-mono text-xs uppercase tracking-widest mb-4"
                            style={{ color: 'var(--muted)' }}>
                            {jobs.length} research job{jobs.length !== 1 ? 's' : ''}
                        </p>
                        <div className="space-y-2">
                            {jobs.map((job, i) => (
                                <div
                                    key={`history-${job.thread_id}-${i}`}
                                    className="bg-white border p-4 cursor-pointer transition-all flex items-center justify-between gap-4"
                                    style={{ borderColor: 'var(--border)' }}
                                    onClick={() => viewJob(job)}
                                    onMouseEnter={e => {
                                        (e.currentTarget as HTMLDivElement).style.boxShadow = '2px 2px 0 var(--ink)'
                                    }}
                                    onMouseLeave={e => {
                                        (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'
                                    }}
                                >
                                    <div className="flex-1 min-w-0">
                                        <p className="font-serif text-base truncate" style={{ color: 'var(--ink)' }}>
                                            {job.query}
                                        </p>
                                        <p className="font-mono text-xs mt-1" style={{ color: 'var(--muted)' }}>
                                            {formatDate(job.finished_at)}
                                            {job.report && (
                                                <span className="ml-2" style={{ color: 'var(--accent)' }}>● cached</span>
                                            )}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-3 shrink-0">
                                        <span className="font-mono text-xs px-2 py-1 rounded-sm"
                                            style={{ background: 'var(--ink)', color: 'var(--paper)' }}>
                                            {job.quality_score}/30
                                        </span>
                                        <span className="font-mono text-xs" style={{ color: 'var(--muted)' }}>
                                            View →
                                        </span>
                                        <button
                                            onClick={e => deleteItem(e, job.thread_id)}
                                            className="font-mono text-xs px-2 py-1 border transition-colors"
                                            style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}
                                            title="Delete this report"
                                        >
                                            ✕
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {loading && (
                    <div className="fixed inset-0 flex items-center justify-center"
                        style={{ background: 'rgba(245,240,232,0.8)' }}>
                        <p className="font-mono text-xs uppercase tracking-widest animate-pulse"
                            style={{ color: 'var(--ink)' }}>
                            Loading report…
                        </p>
                    </div>
                )}
            </main>
        </div>
    )
}
