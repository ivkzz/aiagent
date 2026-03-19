<script setup lang="ts">
import { ref } from 'vue'
import { ACCEPTED_FILE_TYPES } from '@/utils/constants'

const emit = defineEmits<{ drop: [files: FileList] }>()

const isDragging = ref(false)
const inputRef = ref<HTMLInputElement>()

function onDrop(e: DragEvent): void {
  isDragging.value = false
  if (e.dataTransfer?.files.length) emit('drop', e.dataTransfer.files)
}

function onFileInput(e: Event): void {
  const files = (e.target as HTMLInputElement).files
  if (files?.length) emit('drop', files)
}
</script>

<template>
  <div
    :class="[
      'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors',
      isDragging ? 'border-accent bg-accent/5' : 'border-border hover:border-accent/50',
    ]"
    @dragover.prevent="isDragging = true"
    @dragleave="isDragging = false"
    @drop.prevent="onDrop"
    @click="inputRef?.click()"
  >
    <input
      ref="inputRef"
      type="file"
      multiple
      :accept="ACCEPTED_FILE_TYPES"
      class="hidden"
      @change="onFileInput"
    />
    <div class="flex flex-col items-center gap-2 text-muted">
      <svg class="size-10 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
      </svg>
      <p class="text-sm">Перетащите файлы или <span class="text-accent">выберите</span></p>
      <p class="text-xs opacity-60">TXT · MD · PDF · DOCX · HTML · CSV</p>
    </div>
  </div>
</template>
