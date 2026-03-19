<script setup lang="ts">
interface Props {
  variant?: 'primary' | 'ghost' | 'danger'
  size?: 'sm' | 'md'
  disabled?: boolean
  loading?: boolean
  type?: 'button' | 'submit'
}

const { variant = 'primary', size = 'md', disabled = false, loading = false, type = 'button' } =
  defineProps<Props>()
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="[
      'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-40 disabled:cursor-not-allowed',
      size === 'sm' ? 'px-3 py-1.5 text-xs' : 'px-4 py-2 text-sm',
      variant === 'primary' && 'bg-accent text-white hover:bg-accent-hover',
      variant === 'ghost' && 'bg-transparent text-muted hover:text-text hover:bg-surface-2',
      variant === 'danger' && 'bg-transparent text-error hover:bg-error/10',
    ]"
  >
    <span v-if="loading" class="size-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
    <slot />
  </button>
</template>
