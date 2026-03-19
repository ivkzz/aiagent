/**
 * Утилиты для экспорта истории чата
 *
 * ПРИМЕЧАНИЕ: Текущая реализация хранит в каждом сообщении только последние
 * значения step/tool/toolArgs/toolResult. Если в ответе агента было несколько
 * вызовов инструментов, в экспорт попадёт только последний. Полная история
 * вызовов хранится в toolResults (только для последнего ответа).
 */

import type { ChatMessage } from '@/types'

export interface ExportData {
  thread_id: string
  exported_at: string
  messages: ExportedMessage[]
  tool_results: Array<{
    tool: string
    result: string
    step: number
  }>
  documents: Array<{
    filename: string
    chunks: number
    file_type?: string | null
    uploaded_at?: string | null
  }>
  errors: Array<{
    timestamp: string
    message: string
    details?: string
  }>
}

export interface ExportedMessage {
  id: string
  role: 'user' | 'agent'
  content: string
  timestamp: string
  sources: string[]
  step?: number
  tool?: string
  tool_args?: Record<string, unknown>
  tool_result?: string
  execution_events?: Array<{
    step: number
    type: 'step_start' | 'tool_call' | 'tool_result'
    tool?: string
    args?: Record<string, unknown>
    result?: string
    timestamp: string
  }>
}

/**
 * Экспорт истории чата в JSON
 */
export function exportToJSON(
  messages: ChatMessage[],
  threadId: string,
  toolResults: Array<{tool: string; result: string; step: number}>,
  documents: Array<{filename: string; chunks: number; file_type?: string | null; uploaded_at?: string | null}>,
  errors: Array<{timestamp: Date; message: string; details?: string}>
): string {
  const exportData: ExportData = {
    thread_id: threadId,
    exported_at: new Date().toISOString(),
    messages: messages.map(msg => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      timestamp: msg.timestamp.toISOString(),
      sources: msg.sources,
      step: msg.step,
      tool: msg.tool,
      tool_args: msg.toolArgs,
      tool_result: msg.toolResult,
      execution_events: msg.executionEvents?.map(e => ({
        step: e.step,
        type: e.type,
        tool: e.tool,
        args: e.args,
        result: e.result,
        timestamp: e.timestamp.toISOString()
      }))
    })),
    tool_results: toolResults,
    documents: documents.map(doc => ({
      filename: doc.filename,
      chunks: doc.chunks,
      file_type: doc.file_type,
      uploaded_at: doc.uploaded_at
    })),
    errors: errors.map(err => ({
      timestamp: err.timestamp.toISOString(),
      message: err.message,
      details: err.details
    }))
  }

  return JSON.stringify(exportData, null, 2)
}

/**
 * Экспорт истории чата в Markdown
 */
export function exportToMarkdown(
  messages: ChatMessage[],
  threadId: string,
  toolResults: Array<{tool: string; result: string; step: number}>,
  documents: Array<{filename: string; chunks: number; file_type?: string | null; uploaded_at?: string | null}>,
  errors: Array<{timestamp: Date; message: string; details?: string}>
): string {
  const lines: string[] = []

  lines.push('# Экспорт диалога')
  lines.push('')
  lines.push(`**ID потока:** \`${threadId}\``)
  lines.push(`**Дата экспорта:** ${new Date().toLocaleString('ru-RU')}`)
  lines.push('')
  lines.push('---')
  lines.push('')

  for (const msg of messages) {
    if (msg.role === 'user') {
      lines.push(`## 👤 Пользователь`)
      lines.push('')
      lines.push(msg.content)
      lines.push('')
    } else {
      lines.push(`## 🤖 Агент`)
      lines.push('')

      if (msg.content) {
        lines.push(msg.content)
        lines.push('')
      }

      // Текущее состояние (последние значения)
      if (msg.step || msg.tool || msg.toolResult) {
        lines.push('### 📋 Текущее состояние')
        lines.push('')
        if (msg.step) lines.push(`**Шаг:** ${msg.step}`)
        if (msg.tool) {
          lines.push(`**Инструмент:** \`${msg.tool}\``)
          if (msg.toolArgs && Object.keys(msg.toolArgs).length > 0) {
            lines.push('**Аргументы:**')
            lines.push('```json')
            lines.push(JSON.stringify(msg.toolArgs, null, 2))
            lines.push('```')
          }
        }
        if (msg.toolResult) {
          lines.push('**Результат:**')
          lines.push('```')
          lines.push(msg.toolResult)
          lines.push('```')
        }
        lines.push('')
      }

      // Полный лог событий выполнения
      if (msg.executionEvents && msg.executionEvents.length > 0) {
        lines.push('### 📊 Полный лог событий')
        lines.push('')
        lines.push('| Шаг | Тип события | Инструмент |')
        lines.push('|-----|-------------|------------|')
        for (const ev of msg.executionEvents) {
          const tool = ev.tool ? `\`${ev.tool}\`` : '-'
          lines.push(`| ${ev.step} | ${ev.type} | ${tool} |`)
        }
        lines.push('')
      }
    }

    // Источники
    if (msg.sources && msg.sources.length > 0) {
      lines.push('### 📚 Источники')
      for (const source of msg.sources) {
        lines.push(`- ${source}`)
      }
      lines.push('')
    }

    lines.push('---')
    lines.push('')
  }

  // Сводка по инструментам
  if (toolResults.length > 0) {
    lines.push('## 📊 Сводка вызовов инструментов')
    lines.push('')
    lines.push('| Шаг | Инструмент | Результат |')
    lines.push('|-----|------------|-----------|')

    for (const tr of toolResults) {
      const resultPreview = tr.result.length > 50
        ? tr.result.substring(0, 50) + '...'
        : tr.result
      lines.push(`| ${tr.step} | \`${tr.tool}\` | ${resultPreview} |`)
    }

    lines.push('')
  }

  // Список загруженных документов
  if (documents.length > 0) {
    lines.push('## 📚 Загруженные документы')
    lines.push('')
    lines.push('| Файл | Chunks | Тип | Загружен |')
    lines.push('|------|--------|-----|----------|')

    for (const doc of documents) {
      const uploaded = doc.uploaded_at
        ? new Date(doc.uploaded_at).toLocaleString('ru-RU')
        : '-'
      const fileType = doc.file_type || '-'
      lines.push(`| ${doc.filename} | ${doc.chunks} | ${fileType} | ${uploaded} |`)
    }

    lines.push('')
  }

  // Ошибки сессии
  if (errors.length > 0) {
    lines.push('## ⚠️ Ошибки сессии')
    lines.push('')
    lines.push('| Время | Сообщение | Детали |')
    lines.push('|-------|-----------|--------|')

    for (const err of errors) {
      const time = new Date(err.timestamp).toLocaleString('ru-RU')
      const details = err.details ? err.details.replace(/\|/g, '\\|') : '-'
      const message = err.message.replace(/\|/g, '\\|')
      lines.push(`| ${time} | ${message} | ${details} |`)
    }

    lines.push('')
  }

  return lines.join('\n')
}

/**
 * Скачивание файла
 */
export function downloadFile(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Основная функция экспорта
 */
export function exportChat(
  messages: ChatMessage[],
  threadId: string,
  toolResults: Array<{tool: string; result: string; step: number}>,
  documents: Array<{filename: string; chunks: number; file_type?: string | null; uploaded_at?: string | null}>,
  errors: Array<{timestamp: Date; message: string; details?: string}>,
  format: 'json' | 'markdown' = 'json'
): void {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  const filename = `chat-export-${threadId}-${timestamp}`

  if (format === 'json') {
    const content = exportToJSON(messages, threadId, toolResults, documents, errors)
    downloadFile(content, `${filename}.json`)
  } else {
    const content = exportToMarkdown(messages, threadId, toolResults, documents, errors)
    downloadFile(content, `${filename}.md`)
  }
}
