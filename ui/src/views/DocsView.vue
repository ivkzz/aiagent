<script setup lang="ts">
import { useDocsStore } from '@/stores/useDocsStore'
import { useFileUpload } from '@/composables/useFileUpload'
import BaseDropzone from '@/components/common/BaseDropzone.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseBadge from '@/components/common/BaseBadge.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'

const docs = useDocsStore()
const { files, addFiles, removeFile, clear, buildFormData } = useFileUpload()

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function upload(): Promise<void> {
  if (!files.value.length) return
  await docs.ingest(buildFormData())
  if (!docs.lastResult?.errors.length) clear()
}

async function onDeleteDocument(filename: string): Promise<void> {
  if (confirm(`Удалить файл "${filename}" из базы знаний?`)) {
    await docs.removeDocument(filename)
  }
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '—'
  try {
    return new Date(dateStr).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  } catch {
    return '—'
  }
}
</script>

<template>
  <div class="h-full overflow-y-auto scrollbar-thin px-8 py-8">
    <div class="max-w-4xl mx-auto flex flex-col gap-6">
      <!-- Заголовок -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-lg font-semibold text-text">Загрузка документов</h1>
          <p class="text-sm text-muted mt-1">База знаний агента (RAG)</p>
        </div>
        <RouterLink to="/">
          <BaseButton variant="primary">
            Перейти к чату
          </BaseButton>
        </RouterLink>
      </div>

      <!-- Dropzone -->
      <BaseDropzone @drop="addFiles" />

      <!-- Список загруженных документов -->
      <div class="flex flex-col gap-3">
        <h2 class="text-base font-medium text-text">
          Загруженные документы ({{ docs.documents.length }})
        </h2>

        <div v-if="docs.isLoading" class="flex justify-center py-8">
          <BaseSpinner />
        </div>

        <div v-else-if="!docs.documents.length" class="text-center py-8 text-muted text-sm bg-surface rounded-lg border border-border">
          Нет загруженных документов
        </div>

        <div v-else class="flex flex-col gap-2">
          <div
            v-for="doc in docs.documents"
            :key="doc.filename"
            class="flex items-center gap-4 px-4 py-3 bg-surface border border-border rounded-lg"
          >
            <svg class="size-5 text-muted shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>

            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-text truncate">{{ doc.filename }}</p>
              <div class="flex gap-3 text-xs text-muted mt-0.5">
                <span>{{ doc.chunks }} чанков</span>
                <span v-if="doc.file_type">{{ doc.file_type }}</span>
                <span v-if="formatDate(doc.uploaded_at)">{{ formatDate(doc.uploaded_at) }}</span>
              </div>
            </div>

            <BaseButton
              variant="danger"
              size="sm"
              :loading="docs.isLoading"
              @click="onDeleteDocument(doc.filename)"
              title="Удалить"
            >
              <svg class="size-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </BaseButton>
          </div>
        </div>
      </div>

      <!-- Файлы для загрузки -->
      <div v-if="files.length" class="flex flex-col gap-2 mt-4 border-t border-border pt-4">
        <div class="text-sm font-medium text-text">Загрузить новые файлы</div>
        <div
          v-for="(file, i) in files"
          :key="file.name"
          class="flex items-center gap-3 px-3 py-2.5 bg-surface border border-border rounded-lg"
        >
          <svg class="size-4 text-muted shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span class="flex-1 text-sm text-text truncate">{{ file.name }}</span>
          <span class="text-xs text-muted shrink-0">{{ formatSize(file.size) }}</span>
          <BaseButton variant="danger" size="sm" @click="removeFile(i)">
            <svg class="size-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </BaseButton>
        </div>

        <BaseButton :loading="docs.isLoading" class="mt-2 self-start" @click="upload">
          Загрузить в RAG ({{ files.length }})
        </BaseButton>
      </div>

      <!-- Результат последней загрузки -->
      <div
        v-if="docs.lastResult"
        class="p-4 bg-surface border border-border rounded-xl flex flex-col gap-3"
      >
        <div class="flex items-center gap-2">
          <BaseBadge variant="success">Готово</BaseBadge>
          <span class="text-sm text-text">Индексация завершена</span>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="bg-surface-2 rounded-lg p-3 text-center">
            <p class="text-2xl font-semibold text-text">{{ docs.lastResult.documents_processed }}</p>
            <p class="text-xs text-muted mt-0.5">файлов обработано</p>
          </div>
          <div class="bg-surface-2 rounded-lg p-3 text-center">
            <p class="text-2xl font-semibold text-accent">{{ docs.lastResult.chunks_added }}</p>
            <p class="text-xs text-muted mt-0.5">чанков добавлено</p>
          </div>
        </div>
        <div v-if="docs.lastResult.errors.length" class="flex flex-col gap-1">
          <p class="text-xs text-error font-medium">Ошибки:</p>
          <p v-for="err in docs.lastResult.errors" :key="err" class="text-xs text-muted font-mono">
            {{ err }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
