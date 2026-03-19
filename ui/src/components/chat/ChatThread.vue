<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { ChatMessage } from '@/types'
import ChatMessageItem from './ChatMessage.vue'

interface Props {
  messages: ChatMessage[]
}
const props = defineProps<Props>()

const bottomRef = ref<HTMLDivElement>()

watch(
  () => props.messages.map((m) => m.content).join(''),
  () => nextTick(() => bottomRef.value?.scrollIntoView({ behavior: 'smooth' })),
)
</script>

<template>
  <div class="flex-1 overflow-y-auto scrollbar-thin px-6 py-6 flex flex-col gap-4">
    <div
      v-if="!messages.length"
      class="flex-1 flex flex-col items-center justify-center text-center text-muted gap-3 py-20"
    >
      <svg class="size-12 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
      </svg>
      <p class="text-sm">Начните диалог с агентом</p>
      <p class="text-xs opacity-60">Агент использует RAG для поиска по загруженным документам</p>
    </div>

    <ChatMessageItem v-for="msg in messages" :key="msg.id" :message="msg" />
    <div ref="bottomRef" />
  </div>
</template>
