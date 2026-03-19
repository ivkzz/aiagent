<script setup lang="ts">
interface Props {
  size?: 'sm' | 'md' | 'lg'
}
defineProps<Props>()
</script>

<template>
  <span
    :class="[
      'inline-block border-2 border-accent border-t-transparent rounded-full animate-spin',
      { 'size-4': size === 'sm' || !size, 'size-6': size === 'md', 'size-8': size === 'lg' },
    ]"
  />
</template>
