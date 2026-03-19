import { ref, onMounted } from 'vue'
import { defineStore } from 'pinia'
import type { DocumentMetadata, IngestResponse } from '@/types'
import { get, postForm, del } from '@/api/client'
import { useToastStore } from './useToastStore'

export const useDocsStore = defineStore('docs', () => {
  const isLoading = ref(false)
  const documents = ref<DocumentMetadata[]>([])
  const lastResult = ref<IngestResponse | null>(null)

  const toast = useToastStore()

  // Загрузка списка документов
  async function loadDocuments(): Promise<void> {
    isLoading.value = true
    try {
      const data = await get<DocumentMetadata[]>('/documents/list')
      documents.value = data
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ошибка загрузки списка документов'
      toast.add('error', msg)
      documents.value = []
    } finally {
      isLoading.value = false
    }
  }

  // Загрузка файлов (индексация)
  async function ingest(form: FormData): Promise<void> {
    isLoading.value = true
    lastResult.value = null

    try {
      const res = await postForm<IngestResponse>('/documents/ingest', form)
      lastResult.value = res
      toast.add('success', `Загружено: ${res.documents_processed} файлов, ${res.chunks_added} чанков`)

      // После успешной индексации обновляем список
      await loadDocuments()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ошибка загрузки'
      toast.add('error', msg)
    } finally {
      isLoading.value = false
    }
  }

  // Удаление документа
  async function removeDocument(filename: string): Promise<void> {
    try {
      await del(`/documents/${encodeURIComponent(filename)}`)
      toast.add('success', `Файл "${filename}" удалён`)
      // Обновляем список
      await loadDocuments()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ошибка удаления'
      toast.add('error', msg)
    }
  }

  // Автоматически загружаем список при монтировании store
  onMounted(() => {
    loadDocuments().catch(() => {
      // Ошибка уже логируется в loadDocuments
    })
  })

  return {
    isLoading,
    documents,
    lastResult,
    ingest,
    loadDocuments,
    removeDocument,
  }
})
