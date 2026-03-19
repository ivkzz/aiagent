import type { StreamChunk } from '@/types'
import { postStream } from '@/api/client'

interface SSEHandlers {
  onToken: (token: string) => void
  onSources: (sources: string[]) => void
  onDone: (threadId: string) => void
  onError: (detail: string) => void
  onStepStart?: (step: number, total: number) => void
  onToolCall?: (tool: string, args: Record<string, unknown>) => void
  onToolResult?: (tool: string, result: string) => void
}

export function useSSE() {
  async function stream(
    path: string,
    body: unknown,
    handlers: SSEHandlers,
  ): Promise<void> {
    const res = await postStream(path, body)

    if (!res.ok || !res.body) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      handlers.onError(err.detail ?? res.statusText)
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const raw = line.slice(6).trim()
        if (!raw) continue

        try {
          const chunk = JSON.parse(raw) as StreamChunk
          if (chunk.type === 'token' && chunk.content) handlers.onToken(chunk.content)
          else if (chunk.type === 'sources' && chunk.sources) handlers.onSources(chunk.sources)
          else if (chunk.type === 'done') handlers.onDone(chunk.thread_id ?? '')
          else if (chunk.type === 'error') handlers.onError(chunk.detail ?? 'Ошибка агента')
          else if (chunk.type === 'step_start' && chunk.step !== undefined && chunk.total !== undefined)
            handlers.onStepStart?.(chunk.step, chunk.total)
          else if (chunk.type === 'tool_call' && chunk.tool && chunk.args !== undefined)
            handlers.onToolCall?.(chunk.tool, chunk.args)
          else if (chunk.type === 'tool_result' && chunk.tool && chunk.result)
            handlers.onToolResult?.(chunk.tool, chunk.result)
        } catch {
          // пропускаем невалидный JSON
        }
      }
    }
  }

  return { stream }
}
