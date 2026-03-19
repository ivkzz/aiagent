<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useChatStore } from '@/stores/useChatStore'
import BaseBadge from '@/components/common/BaseBadge.vue'
import BaseButton from '@/components/common/BaseButton.vue'

const route = useRoute()
const chat = useChatStore()

const localThreadId = ref(chat.threadId)
const localApiKey = ref(chat.apiKey)
const showApiKey = ref(false)
const copyTooltip = ref('Копировать')

function copyThreadId(): void {
  navigator.clipboard.writeText(localThreadId.value).then(() => {
    copyTooltip.value = 'Скопировано!'
    setTimeout(() => {
      copyTooltip.value = 'Копировать'
    }, 2000)
  }).catch(() => {
    copyTooltip.value = 'Ошибка'
  })
}

// Debounced save для threadId (в браузере setTimeout возвращает number)
let threadSaveTimeout: number | null = null
watch(localThreadId, (v) => {
  if (threadSaveTimeout !== null) {
    clearTimeout(threadSaveTimeout)
  }
  threadSaveTimeout = window.setTimeout(() => {
    chat.saveThreadId(v)
  }, 500)
})

watch(localApiKey, (v) => chat.saveApiKey(v))

onMounted(() => chat.checkHealth())
</script>

<template>
  <aside class="w-60 shrink-0 flex flex-col bg-surface border-r border-border h-full">
    <!-- Логотип -->
    <div class="px-5 py-4 border-b border-border">
      <div class="flex items-center gap-2">
        <div class="size-7 rounded-lg bg-accent/20 flex items-center justify-center">
          <svg class="size-4 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
        </div>
        <span class="font-semibold text-sm text-text">AI Agent</span>
      </div>
    </div>

    <!-- Навигация -->
    <nav class="px-3 py-3 flex flex-col gap-1">
      <RouterLink
        to="/"
        :class="[
          'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
          route.path === '/' ? 'bg-accent/10 text-accent' : 'text-muted hover:text-text hover:bg-surface-2',
        ]"
      >
        <svg class="size-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        Чат
      </RouterLink>
      <RouterLink
        to="/docs"
        :class="[
          'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
          route.path === '/docs' ? 'bg-accent/10 text-accent' : 'text-muted hover:text-text hover:bg-surface-2',
        ]"
      >
        <svg class="size-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        Документы
      </RouterLink>
    </nav>

    <div class="flex-1" />

    <!-- Настройки -->
    <div class="px-4 py-4 border-t border-border flex flex-col gap-3">
      <!-- Thread ID -->
      <div class="flex flex-col gap-1">
        <span class="text-xs text-muted">Сессия</span>
        <div class="flex gap-1">
          <input
            v-model="localThreadId"
            class="flex-1 min-w-0 bg-surface-2 border border-border rounded-lg px-2 py-1.5 text-xs text-text font-mono focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <BaseButton variant="ghost" size="sm" :title="copyTooltip" @click="copyThreadId">
            <svg class="size-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </BaseButton>
          <BaseButton variant="ghost" size="sm" title="Новая сессия" @click="chat.newSession">
            <svg class="size-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </BaseButton>
        </div>
      </div>

      <!-- API Key -->
      <div class="flex flex-col gap-1">
        <span class="text-xs text-muted">API Key</span>
        <div v-if="!localApiKey" class="text-xs text-warning bg-warning/10 rounded-lg px-2 py-1.5">
          Введите API Key для работы
        </div>
        <div class="flex gap-1">
          <input
            v-model="localApiKey"
            :type="showApiKey ? 'text' : 'password'"
            placeholder="your-secret-api-key"
            :class="[
              'flex-1 min-w-0 bg-surface-2 border rounded-lg px-2 py-1.5 text-xs text-text font-mono focus:outline-none focus:ring-1',
              localApiKey ? 'border-border focus:ring-accent' : 'border-warning/50 focus:ring-warning',
            ]"
          />
          <BaseButton variant="ghost" size="sm" @click="showApiKey = !showApiKey">
            <svg class="size-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="showApiKey" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          </BaseButton>
        </div>
      </div>

      <!-- Статус бэкенда -->
      <div class="flex items-center justify-between">
        <span class="text-xs text-muted">Бэкенд</span>
        <BaseBadge
          :variant="chat.backendStatus === 'ok' ? 'success' : chat.backendStatus === 'error' ? 'error' : 'neutral'"
        >
          {{ chat.backendStatus === 'ok' ? 'online' : chat.backendStatus === 'error' ? 'offline' : '...' }}
        </BaseBadge>
      </div>
    </div>
  </aside>
</template>
