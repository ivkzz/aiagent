<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  sources: string[]
}
defineProps<Props>()

const isOpen = ref(false)
</script>

<template>
  <div v-if="sources.length" class="mt-2">
    <button
      class="flex items-center gap-1.5 text-xs text-muted hover:text-text transition-colors"
      @click="isOpen = !isOpen"
    >
      <svg
        :class="['size-3 transition-transform', isOpen && 'rotate-90']"
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
      </svg>
      {{ sources.length }} {{ sources.length === 1 ? 'источник' : 'источника' }}
    </button>
    <div v-if="isOpen" class="mt-1.5 flex flex-wrap gap-1.5">
      <span
        v-for="src in sources"
        :key="src"
        class="px-2 py-0.5 bg-surface-2 border border-border rounded text-xs font-mono text-muted"
      >
        {{ src }}
      </span>
    </div>
  </div>
</template>
