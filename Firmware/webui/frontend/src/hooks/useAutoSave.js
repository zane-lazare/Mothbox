import { useState, useEffect, useRef, useCallback } from 'react'
import deepEqual from '../utils/deepEqual'

/**
 * Auto-save hook with debouncing
 *
 * @param {Object} options
 * @param {*} options.data - The data to save
 * @param {Function} options.onSave - Async function that saves the data
 * @param {number} options.delay - Debounce delay in milliseconds (default: 2000)
 * @param {boolean} options.enabled - Whether auto-save is active (default: true)
 *
 * @returns {Object} { status, saveNow, error }
 * - status: 'idle' | 'saving' | 'saved' | 'error'
 * - saveNow: Function to immediately trigger save
 * - error: Error object if status is 'error', null otherwise
 */
export default function useAutoSave({
  data,
  onSave,
  delay = 2000,
  enabled = true
}) {
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)

  const timerRef = useRef(null)
  const dataRef = useRef(data)
  const initialDataRef = useRef(data)
  const statusResetTimerRef = useRef(null)

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
        setStatus('idle')
      }, 1500)
    } catch (err) {
      setStatus('error')
      setError(err)
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
