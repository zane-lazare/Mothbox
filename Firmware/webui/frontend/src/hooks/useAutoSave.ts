import { useState, useEffect, useRef, useCallback } from 'react'
import deepEqual from '../utils/deepEqual'

type AutoSaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export interface UseAutoSaveOptions<T> {
  data: T
  onSave: (data: T) => Promise<void>
  delay?: number
  enabled?: boolean
}

export interface UseAutoSaveResult {
  status: AutoSaveStatus
  saveNow: () => void
  error: Error | null
}

/**
 * Auto-save hook with debouncing
 *
 * @param options - Auto-save configuration
 * @param options.data - The data to save
 * @param options.onSave - Async function that saves the data
 * @param options.delay - Debounce delay in milliseconds (default: 2000)
 * @param options.enabled - Whether auto-save is active (default: true)
 *
 * @returns Auto-save state and controls
 * - status: 'idle' | 'saving' | 'saved' | 'error'
 * - saveNow: Function to immediately trigger save
 * - error: Error object if status is 'error', null otherwise
 *
 * @example
 * const { status, saveNow, error } = useAutoSave({
 *   data: formData,
 *   onSave: async (data) => {
 *     await api.post('/save', data)
 *   },
 *   delay: 2000,
 *   enabled: true
 * })
 */
export default function useAutoSave<T>({
  data,
  onSave,
  delay = 2000,
  enabled = true
}: UseAutoSaveOptions<T>): UseAutoSaveResult {
  const [status, setStatus] = useState<AutoSaveStatus>('idle')
  const [error, setError] = useState<Error | null>(null)

  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const dataRef = useRef<T>(data)
  const initialDataRef = useRef<T>(data)
  const statusResetTimerRef = useRef<NodeJS.Timeout | null>(null)
  const isMountedRef = useRef(true)

  // Keep data ref updated
  useEffect(() => {
    dataRef.current = data
  }, [data])

  const performSave = useCallback(async () => {
    if (!enabled) return

    // Don't save if data hasn't changed from initial
    if (deepEqual(dataRef.current, initialDataRef.current)) {
      return
    }

    setStatus('saving')
    setError(null)

    try {
      await onSave(dataRef.current)
      setStatus('saved')
      initialDataRef.current = dataRef.current

      // Reset to idle after short delay
      if (statusResetTimerRef.current) {
        clearTimeout(statusResetTimerRef.current)
      }
      statusResetTimerRef.current = setTimeout(() => {
        // Guard against state updates after unmount
        if (isMountedRef.current) {
          setStatus('idle')
        }
      }, 1500)
    } catch (err) {
      setStatus('error')
      setError(err as Error)
    }
  }, [onSave, enabled])

  // Debounced auto-save on data changes
  useEffect(() => {
    if (!enabled) return

    // Clear existing timer
    if (timerRef.current) {
      clearTimeout(timerRef.current)
    }

    // Don't set timer if data hasn't changed
    if (deepEqual(data, initialDataRef.current)) {
      return
    }

    // Set new timer
    timerRef.current = setTimeout(() => {
      performSave()
    }, delay)

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
    }
  }, [data, delay, enabled, performSave])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
      if (statusResetTimerRef.current) {
        clearTimeout(statusResetTimerRef.current)
      }
    }
  }, [])

  const saveNow = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
    }
    performSave()
  }, [performSave])

  return { status, saveNow, error }
}
