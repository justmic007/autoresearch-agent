export interface AgentMetric {
    agent: string
    latency_ms: number
    tokens_used: number
}

export interface QualityScore {
    completeness: number
    accuracy: number
    coherence: number
    total: number
    feedback: string
}

export interface ResearchResult {
    thread_id: string
    query: string
    report: string
    quality_score: QualityScore
    subtasks: string[]
    metrics: AgentMetric[]
    total_tokens: number
    duration_seconds: number
}

export interface AgentDoneEvent {
    agent: string
    latency: number
    subtasks?: string[]
    sources?: number
    chunks?: number
    report?: string
    quality_score?: QualityScore
    status?: string
}

export type AgentStatus = 'idle' | 'active' | 'done'

export interface PipelineState {
    planner: AgentStatus
    search: AgentStatus
    rag: AgentStatus
    writer: AgentStatus
    critic: AgentStatus
}