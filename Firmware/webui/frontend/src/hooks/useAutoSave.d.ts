/**
 * Type declarations for useAutoSave.js
 *
 * Provides TypeScript types during the gradual migration.
 * IMPORTANT: Keep in sync with useAutoSave.js.
 */

type AutoSaveStatus = 'idle' | 'saving' | 'saved' | 'error'

interface UseAutoSaveOptions<T> {
  data: T
  onSave: (data: T) => Promise<void>
  delay?: number
  enabled?: boolean
}

interface UseAutoSaveResult {
  status: AutoSaveStatus
  saveNow: () => void
  error: Error | null
}

declare function useAutoSave<T>(options: UseAutoSaveOptions<T>): UseAutoSaveResult
export default useAutoSave
