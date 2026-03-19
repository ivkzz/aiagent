<script setup lang="ts">
import { ref, watch } from 'vue'
import BaseButton from '@/components/common/BaseButton.vue'

interface Props {
  disabled?: boolean
}
defineProps<Props>()
const emit = defineEmits<{ send: [text: string] }>()

const text = ref('')
const textareaRef = ref<HTMLTextAreaElement>()

function resize(): void {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 144) + 'px'
}

watch(text, () => resize())

function submit(): void {
  const trimmed = text.value.trim()
  if (!trimmed) return
  emit('send', trimmed)
  text.value = ''
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}
</script>

<template>
  <div class="px-6 py-4 border-t border-border bg-bg">
    <div class="flex gap-3 items-end bg-surface border border-border rounded-xl px-4 py-3 focus-within:ring-1 focus-within:ring-accent transition-all">
      <textarea
        ref="textareaRef"
        v-model="text"
        :disabled="disabled"
        placeholder="Задайте вопрос агенту... (Enter — отправить, Shift+Enter — новая строка)"
        rows="1"
        class="flex-1 bg-transparent resize-none text-sm text-text placeholder:text-muted focus:outline-none leading-relaxed disabled:opacity-50"
        style="max-height: 144px"
        @keydown="onKeydown"
      />
      <BaseButton
        :disabled="disabled || !text.trim()"
        :loading="disabled"
        size="sm"
        @click="submit"
      >
        <svg class="size-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
        </svg>
      </BaseButton>
    </div>
    <p class="text-xs text-muted mt-1.5 text-center opacity-50">
      Enter — отправить · Shift+Enter — новая строка
    </p>
  </div>
</template>
