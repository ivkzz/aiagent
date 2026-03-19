<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/useChatStore'
import ChatThread from '@/components/chat/ChatThread.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { exportChat } from '@/utils/export'

const chat = useChatStore()
const showExportMenu = ref(false)

onMounted(() => {
  chat.loadHistory()
  chat.loadDocuments()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

function handleClickOutside(event: MouseEvent): void {
  const target = event.target as HTMLElement
  if (!target.closest('.relative')) {
    showExportMenu.value = false
  }
}

function handleExport(format: 'json' | 'markdown'): void {
  exportChat(
    chat.messages,
    chat.threadId,
    chat.toolResults,
    chat.documents,
    chat.errors,
    format
  )
  showExportMenu.value = false
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Заголовок с кнопками -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-border">
      <h1 class="text-lg font-semibold text-text">Чат</h1>
      <div class="flex gap-2">
        <!-- Кнопка экспорта -->
        <div class="relative">
          <BaseButton size="sm" @click="showExportMenu = !showExportMenu">
            <svg class="size-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>Экспорт</span>
          </BaseButton>

          <!-- Меню выбора формата -->
          <div v-if="showExportMenu" class="absolute right-0 top-full mt-2 bg-surface border border-border rounded-lg shadow-lg z-10 min-w-[160px]">
            <button
              @click="handleExport('json')"
              class="w-full px-4 py-2 text-left text-sm hover:bg-surface-2 transition-colors first:rounded-t-lg"
            >
              📄 JSON (для анализа)
            </button>
            <button
              @click="handleExport('markdown')"
              class="w-full px-4 py-2 text-left text-sm hover:bg-surface-2 transition-colors last:rounded-b-lg"
            >
              📝 Markdown (для чтения)
            </button>
          </div>
        </div>

        <!-- Кнопка нового чата -->
        <BaseButton size="sm" @click="chat.newSession">
          <svg class="size-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 4v16m8-8H4" />
          </svg>
          <span>Новый чат</span>
        </BaseButton>
      </div>
    </div>

    <ChatThread :messages="chat.messages" />
    <ChatInput :disabled="chat.isStreaming" @send="chat.sendMessage" />
  </div>
</template>
