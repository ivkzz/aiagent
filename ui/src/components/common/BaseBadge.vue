<script setup lang="ts">
interface Props {
  variant?: 'success' | 'error' | 'warning' | 'neutral'
}
defineProps<Props>()
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
      {
        'bg-success/10 text-success': variant === 'success',
        'bg-error/10 text-error': variant === 'error',
        'bg-warning/10 text-warning': variant === 'warning',
        'bg-surface-2 text-muted': !variant || variant === 'neutral',
      },
    ]"
  >
    <slot />
  </span>
</template>
