<script setup lang="ts">
interface Props {
  label?: string
  error?: string
  type?: string
}

defineProps<Props>()
const model = defineModel<string>()
</script>

<template>
  <label class="flex flex-col gap-1">
    <span v-if="label" class="text-xs text-muted">{{ label }}</span>
    <input
      v-model="model"
      :type="type ?? 'text'"
      :class="[
        'bg-surface-2 border rounded-lg px-3 py-2 text-sm text-text placeholder:text-muted focus:outline-none focus:ring-1 transition-colors',
        error ? 'border-error focus:ring-error' : 'border-border focus:ring-accent',
      ]"
    />
    <span v-if="error" class="text-xs text-error">{{ error }}</span>
  </label>
</template>
