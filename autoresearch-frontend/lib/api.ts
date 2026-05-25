const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function* streamResearch(query: string) {
    const response = await fetch(`${API_URL}/research/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
    })

    if (!response.ok) throw new Error(`API error ${response.status}`)
    if (!response.body) throw new Error('No response body')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // SSE messages are separated by double newlines
        // Split on double newline to get complete messages
        const messages = buffer.split('\n\n')

        // Keep the last incomplete message in buffer
        buffer = messages.pop() || ''

        for (const message of messages) {
            if (!message.trim()) continue

            let eventType = ''
            let dataLine = ''

            for (const line of message.split('\n')) {
                if (line.startsWith('event: ')) {
                    eventType = line.slice(7).trim()
                } else if (line.startsWith('data: ')) {
                    dataLine = line.slice(6).trim()
                }
            }

            if (eventType && dataLine) {
                try {
                    yield { event: eventType, data: JSON.parse(dataLine) }
                } catch (e) {
                    console.error('Failed to parse SSE data:', e, dataLine)
                }
            }
        }
    }
}

export async function getJobs() {
    const res = await fetch(`${API_URL}/jobs`)
    return res.json()
}

export async function getJob(threadId: string) {
    const res = await fetch(`${API_URL}/research/${threadId}`)
    if (!res.ok) throw new Error(`${res.status}`)
    return res.json()
}

export async function deleteJob(threadId: string) {
    const res = await fetch(`${API_URL}/research/${threadId}`, { method: 'DELETE' })
    return res.ok
}