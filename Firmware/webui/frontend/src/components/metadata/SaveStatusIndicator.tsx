import { useState, useEffect } from 'react'
import { CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

interface SaveStatusIndicatorProps {
  status: SaveStatus
  onRetry?: () => void
  errorMessage?: string
}

export default function SaveStatusIndicator({
  status,
  onRetry,
  errorMessage
}: SaveStatusIndicatorProps) {
  const [visible, setVisible] = useState<boolean>(false)

  useEffect(() => {
    if (status === 'idle') {
      setVisible(false)
      return
    }

    setVisible(true)

    if (status === 'saved') {
      const timer = setTimeout(() => setVisible(false), 2000)
      return () => clearTimeout(timer)
    }
  }, [status])

  if (!visible) return null

  return (
    <div
      className="flex items-center gap-2 text-sm"
      aria-live="polite"
      role="status"
    >
      {status === 'saving' && (
        <>
          <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
          <span className="text-gray-600 dark:text-gray-400">Saving...</span>
        </>
      )}

      {status === 'saved' && (
        <>
          <CheckCircleIcon className="w-4 h-4 text-green-500" />
          <span className="text-green-600 dark:text-green-400">Saved</span>
        </>
      )}

      {status === 'error' && (
        <>
          <ExclamationCircleIcon className="w-4 h-4 text-red-500" />
          <span className="text-red-600 dark:text-red-400">
            {errorMessage || 'Save failed'}
          </span>
          {onRetry && (
            <button
              onClick={onRetry}
              className="ml-2 text-blue-600 hover:text-blue-700 underline"
            >
              Retry
            </button>
          )}
        </>
      )}
    </div>
  )
}
