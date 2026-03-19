import { ref } from 'vue'
import { ACCEPTED_MIME_TYPES } from '@/utils/constants'

export function useFileUpload() {
  const files = ref<File[]>([])

  function addFiles(incoming: FileList | File[]): void {
    const valid = Array.from(incoming).filter(
      (f) => ACCEPTED_MIME_TYPES.includes(f.type) || f.name.match(/\.(txt|md|pdf|docx|html|csv)$/i),
    )
    const existing = new Set(files.value.map((f) => f.name))
    files.value.push(...valid.filter((f) => !existing.has(f.name)))
  }

  function removeFile(index: number): void {
    files.value.splice(index, 1)
  }

  function clear(): void {
    files.value = []
  }

  function buildFormData(): FormData {
    const form = new FormData()
    files.value.forEach((f) => form.append('files', f))
    return form
  }

  return { files, addFiles, removeFile, clear, buildFormData }
}
