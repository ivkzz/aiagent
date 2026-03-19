import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { Toast } from '@/types'

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])

  function add(type: Toast['type'], message: string): void {
    const id = crypto.randomUUID()
    toasts.value.push({ id, type, message })
    setTimeout(() => remove(id), 4000)
  }

  function remove(id: string): void {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  return { toasts, add, remove }
})
