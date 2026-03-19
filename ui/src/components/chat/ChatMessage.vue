<script setup lang="ts">
import type { ChatMessage } from '@/types'
import ChatSources from './ChatSources.vue'

interface Props {
  message: ChatMessage
}
defineProps<Props>()
</script>

<template>
  <div :class="['flex gap-3', message.role === 'user' ? 'flex-row-reverse' : 'flex-row']">
    <!-- Аватар -->
    <div
      :class="[
        'size-7 shrink-0 rounded-full flex items-center justify-center text-xs font-semibold mt-0.5',
        message.role === 'user' ? 'bg-accent/20 text-accent' : 'bg-surface-2 text-muted',
      ]"
    >
      {{ message.role === 'user' ? 'Вы' : 'AI' }}
    </div>

    <!-- Контент -->
    <div :class="['max-w-[75%]', message.role === 'user' ? 'items-end' : 'items-start', 'flex flex-col']">
      <!-- Статус выполнения (только для agent) -->
      <div v-if="message.role === 'agent' && (message.step || message.tool || message.toolResult)" class="mb-2 space-y-1">
        <!-- Шаг -->
        <div v-if="message.step" class="text-xs text-muted opacity-70 flex items-center gap-2">
          <svg class="size-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <span>Шаг {{ message.step }}</span>
        </div>

        <!-- Вызов инструмента -->
        <div v-if="message.tool" class="text-xs bg-surface-2 rounded px-2 py-1 inline-flex items-center gap-2">
          <svg class="size-3 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span class="font-medium text-accent">{{ message.tool }}</span>
          <span v-if="message.toolArgs" class="text-muted text-xs opacity-80">
            ({{ typeof message.toolArgs === 'object' ? JSON.stringify(message.toolArgs).slice(0, 50) : message.toolArgs }})
          </span>
        </div>

        <!-- Результат инструмента -->
        <div v-if="message.toolResult" class="text-xs text-muted opacity-70 bg-surface-2 rounded px-2 py-1">
          <span class="text-green-500">✓</span>
          <span class="ml-1 truncate">{{ message.toolResult }}</span>
        </div>
      </div>

      <!-- Основное сообщение -->
      <div
        :class="[
          'px-4 py-3 rounded-2xl text-sm leading-relaxed',
          message.role === 'user'
            ? 'bg-accent/10 text-text rounded-tr-sm'
            : 'bg-surface text-text rounded-tl-sm border border-border',
        ]"
      >
        <span class="whitespace-pre-wrap break-words">{{ message.content }}</span>
        <span
          v-if="message.isStreaming"
          class="inline-block w-0.5 h-4 bg-stream ml-0.5 align-middle animate-pulse"
        />
      </div>
      <ChatSources v-if="message.role === 'agent'" :sources="message.sources" />
    </div>
  </div>
</template>
