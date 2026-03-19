/** Сообщение в чате */
export interface ChatMessage {
  id: string
  role: 'user' | 'agent'
  content: string
  sources: string[]
  isStreaming: boolean
  timestamp: Date
  // Поля для статуса выполнения (только для agent сообщений во время стрима)
  step?: number
  tool?: string
  toolArgs?: Record<string, unknown>
  toolResult?: string
  // Полная история событий выполнения (для экспорта и анализа)
  executionEvents?: ExecutionEvent[]
}

/** Событие выполнения агента */
export interface ExecutionEvent {
  step: number
  type: 'step_start' | 'tool_call' | 'tool_result'
  tool?: string
  args?: Record<string, unknown>
  result?: string
  timestamp: Date
}

/** SSE чанк от бэкенда */
export interface StreamChunk {
  type: 'token' | 'sources' | 'done' | 'error' | 'step_start' | 'tool_call' | 'tool_result'
  content?: string
  sources?: string[]
  thread_id?: string
  detail?: string
  // Поля для статусных событий
  step?: number
  total?: number
  tool?: string
  args?: Record<string, unknown>
  result?: string
}

/** Ответ истории диалога */
export interface HistoryMessage {
  role: string
  content: string
}

export interface HistoryResponse {
  thread_id: string
  messages: HistoryMessage[]
}

/** Ответ health endpoint */
export interface HealthResponse {
  status: string
  version: string
}

/** Ответ загрузки документов */
export interface IngestResponse {
  status: string
  documents_processed: number
  chunks_added: number
  errors: string[]
}

/** Метаданные документа для отображения в списке */
export interface DocumentMetadata {
  filename: string
  chunks: number
  file_type?: string | null
  uploaded_at?: string | null  // ISO date string
}

/** Toast уведомление */
export interface Toast {
  id: string
  type: 'success' | 'error' | 'info'
  message: string
}
