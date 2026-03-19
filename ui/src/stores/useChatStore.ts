import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import type { ChatMessage, HistoryResponse, HealthResponse, DocumentMetadata } from '@/types'
import { useSSE } from '@/composables/useSSE'
import { get } from '@/api/client'
import { useToastStore } from './useToastStore'
import { LS_THREAD_ID, LS_API_KEY } from '@/utils/constants'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const threadId = ref(localStorage.getItem(LS_THREAD_ID) ?? crypto.randomUUID())
  const apiKey = ref(localStorage.getItem(LS_API_KEY) ?? '')
  const backendStatus = ref<'unknown' | 'ok' | 'error'>('unknown')
  // Состояние выполнения агента
  const currentStep = ref<number>(0)
  const currentTool = ref<string | null>(null)
  const toolArgs = ref<Record<string, unknown> | null>(null)
  const toolResults = ref<Array<{tool: string; result: string; step: number}>>([])
  // Список загруженных документов
  const documents = ref<DocumentMetadata[]>([])
  // Ошибки текущей сессии (для анализа)
  const errors = ref<Array<{timestamp: Date; message: string; details?: string}>>([])

  const { stream } = useSSE()
  const toast = useToastStore()

  // client.ts читает ключ напрямую из localStorage

  const hasMessages = computed(() => messages.value.length > 0)

  function saveThreadId(id: string): void {
    threadId.value = id
    localStorage.setItem(LS_THREAD_ID, id)
  }

  function saveApiKey(key: string): void {
    apiKey.value = key
    localStorage.setItem(LS_API_KEY, key)
  }

  function newSession(): void {
    saveThreadId(crypto.randomUUID())
    messages.value = []
  }

  async function loadHistory(): Promise<void> {
    try {
      const res = await get<HistoryResponse>(`/chat/history/${threadId.value}`)
      messages.value = res.messages.map((m) => ({
        id: crypto.randomUUID(),
        role: m.role as 'user' | 'agent',
        content: m.content,
        sources: [],
        isStreaming: false,
        timestamp: new Date(),
      }))
    } catch (err) {
      // История недоступна — начинаем с пустого чата
      const msg = err instanceof Error ? err.message : 'Ошибка загрузки истории'
      toast.add('info', msg)
      messages.value = []
    }
  }

  async function checkHealth(): Promise<void> {
    try {
      const res = await get<HealthResponse>('/health')
      backendStatus.value = res.status === 'ok' ? 'ok' : 'error'
    } catch {
      backendStatus.value = 'error'
    }
  }

  async function loadDocuments(): Promise<void> {
    try {
      const docs = await get<DocumentMetadata[]>('/documents/list')
      documents.value = docs
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ошибка загрузки документов'
      toast.add('error', msg)
      documents.value = []
    }
  }

  function recordError(message: string, details?: string): void {
    errors.value.push({
      timestamp: new Date(),
      message,
      details,
    })
  }

  // Автоматически загружать историю при изменении threadId
  watch(
    threadId,
    () => {
      loadHistory()
    },
    { immediate: false }
  )

  async function sendMessage(text: string): Promise<void> {
    if (isStreaming.value || !text.trim()) return

    const toast = useToastStore()

    // Сбрасываем состояние выполнения
    currentStep.value = 0
    currentTool.value = null
    toolArgs.value = null
    toolResults.value = []

    messages.value.push({
      id: crypto.randomUUID(),
      role: 'user',
      content: text.trim(),
      sources: [],
      isStreaming: false,
      timestamp: new Date(),
    })

    messages.value.push({
      id: crypto.randomUUID(),
      role: 'agent',
      content: '',
      sources: [],
      isStreaming: true,
      timestamp: new Date(),
      executionEvents: [],
    })
    isStreaming.value = true

    const agentIdx = messages.value.length - 1

    try {
      await stream(
        '/chat',
        { message: text.trim(), thread_id: threadId.value },
        {
          onToken: (token) => { messages.value[agentIdx]!.content += token },
          onSources: (sources) => { messages.value[agentIdx]!.sources = sources },
          onDone: () => {
            messages.value[agentIdx]!.isStreaming = false
            isStreaming.value = false
            // Очищаем статус после завершения
            currentStep.value = 0
            currentTool.value = null
            toolArgs.value = null
          },
          onError: (detail) => {
            messages.value[agentIdx]!.content = detail
            messages.value[agentIdx]!.isStreaming = false
            isStreaming.value = false
            toast.add('error', detail)
            recordError('Ошибка потока', detail)
            currentStep.value = 0
            currentTool.value = null
            toolArgs.value = null
          },
          // Новые обработчики статуса
          onStepStart: (step, total) => {
            currentStep.value = step
            // Обновляем сообщение агента
            const msg = messages.value[agentIdx]!
            msg.step = step
            msg.tool = undefined
            msg.toolArgs = undefined
            msg.toolResult = undefined
            // Добавляем событие в историю
            if (!msg.executionEvents) msg.executionEvents = []
            msg.executionEvents.push({
              step,
              type: 'step_start',
              timestamp: new Date(),
            })
          },
          onToolCall: (tool, args) => {
            currentTool.value = tool
            toolArgs.value = args
            // Обновляем сообщение агента
            const msg = messages.value[agentIdx]!
            msg.tool = tool
            msg.toolArgs = args
            msg.toolResult = undefined
            // Добавляем событие в историю
            if (!msg.executionEvents) msg.executionEvents = []
            msg.executionEvents.push({
              step: currentStep.value,
              type: 'tool_call',
              tool,
              args,
              timestamp: new Date(),
            })
          },
          onToolResult: (tool, result) => {
            toolResults.value.push({ tool, result, step: currentStep.value })
            // Сохраняем результат в сообщении
            const msg = messages.value[agentIdx]!
            msg.toolResult = result
            // Добавляем событие в историю
            if (!msg.executionEvents) msg.executionEvents = []
            msg.executionEvents.push({
              step: currentStep.value,
              type: 'tool_result',
              tool,
              result,
              timestamp: new Date(),
            })
            // Очищаем текущий инструмент, но результат остаётся в сообщении
            currentTool.value = null
            toolArgs.value = null
          },
        },
      )
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ошибка соединения'
      messages.value[agentIdx]!.content = msg
      messages.value[agentIdx]!.isStreaming = false
      isStreaming.value = false
      toast.add('error', msg)
      recordError('Ошибка соединения', msg)
      currentStep.value = 0
      currentTool.value = null
      toolArgs.value = null
    }
  }

  return {
    messages,
    isStreaming,
    threadId,
    apiKey,
    backendStatus,
    hasMessages,
    currentStep,       // текущий шаг агента
    currentTool,       // текущий инструмент (в процессе вызова)
    toolArgs,          // аргументы текущего инструмента
    toolResults,       // история результатов инструментов
    documents,         // загруженные документы
    errors,            // ошибки сессии
    saveThreadId,
    saveApiKey,
    newSession,
    checkHealth,
    loadHistory,
    loadDocuments,
    recordError,
    sendMessage,
  }
})
