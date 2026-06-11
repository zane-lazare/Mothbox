import { useState, useEffect, useRef } from 'react'
import { ClipboardIcon, CheckIcon } from '@heroicons/react/24/outline'

/**
 * CopyButton - Button to copy text to clipboard with visual feedback
 *
 * Provides a simple way to copy metadata values to the user's clipboard.
 * Shows a success indicator (check icon) for 2 seconds after successful copy.
 */

interface CopyButtonProps {
  text: string
}

export default function CopyButton({ text }: CopyButtonProps) {
  const [copied, setCopied] = useState<boolean>(false)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    // Cleanup timeout on unmount to prevent state updates after unmount
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)

      // Clear any existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }

      // Reset feedback after 2 seconds
      timeoutRef.current = setTimeout(() => {
        setCopied(false)
        timeoutRef.current = null
      }, 2000)
    } catch (error) {
      console.error('Failed to copy text to clipboard:', error)
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
      aria-label={copied ? 'Copied to clipboard' : 'Copy to clipboard'}
    >
      {copied ? (
        <CheckIcon data-icon="check" className="w-4 h-4 text-green-500" />
      ) : (
        <ClipboardIcon data-icon="clipboard" className="w-4 h-4" />
      )}
    </button>
  )
}
