<script setup lang="ts">
import { useToastStore } from '@/stores/useToastStore'

const toast = useToastStore()
</script>

<template>
  <Teleport to="body">
    <div class="fixed bottom-4 right-4 flex flex-col gap-2 z-50">
      <TransitionGroup
        enter-active-class="transition-all duration-300"
        enter-from-class="opacity-0 translate-y-2"
        leave-active-class="transition-all duration-200"
        leave-to-class="opacity-0 translate-y-2"
      >
        <div
          v-for="t in toast.toasts"
          :key="t.id"
          :class="[
            'flex items-center gap-3 px-4 py-3 rounded-lg text-sm shadow-lg cursor-pointer max-w-sm',
            t.type === 'success' && 'bg-success/10 border border-success/20 text-success',
            t.type === 'error' && 'bg-error/10 border border-error/20 text-error',
            t.type === 'info' && 'bg-surface border border-border text-text',
          ]"
          @click="toast.remove(t.id)"
        >
          {{ t.message }}
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
