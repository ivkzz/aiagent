<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import BaseToast from '@/components/common/BaseToast.vue'
</script>

<template>
  <div class="flex h-full overflow-hidden">
    <AppSidebar />
    <main class="flex-1 overflow-hidden">
      <slot />
    </main>
  </div>
  <BaseToast />
</template>
