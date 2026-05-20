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
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let eventType = ''
        let dataLine = ''

        for (const line of lines) {
            if (line.startsWith('event: ')) {
                eventType = line.slice(7).trim()
            } else if (line.startsWith('data: ')) {
                dataLine = line.slice(6).trim()
            } else if (line === '' && eventType && dataLine) {
                try {
                    yield { event: eventType, data: JSON.parse(dataLine) }
                } catch { }
                eventType = ''
                dataLine = ''
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
    return res.json()
}