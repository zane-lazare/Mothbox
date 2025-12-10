import { useState } from 'react'
import { CameraIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { instantCapture } from '../utils/api'

/**
 * InstantCaptureButton component
 *
 * Provides a button to capture instant photos from the live stream
 * using the current camera settings.
 *
 * Features:
 * - Triggers instant capture via API
 * - Shows loading state during capture
 * - Prevents concurrent captures
 * - Displays success/error notifications
 *
 * @param {Object} props - Component props
 * @param {string} [props.className] - Additional CSS classes
 * @param {boolean} [props.disabled] - Whether the button is disabled
 */
export default function InstantCaptureButton({ className = '', disabled = false }) {
  const [isCapturing, setIsCapturing] = useState(false)

  const handleInstantCapture = async () => {
    if (isCapturing || disabled) return

    setIsCapturing(true)

    try {
      const response = await instantCapture()
      const { photo_path } = response.data

      // Extract filename from path for display
      const filename = photo_path.split('/').pop()

      toast.success(`Instant captured: ${filename}`)
    } catch (error) {
      const message = error.response?.data?.error || 'Failed instant capture'
      toast.error(message)
      console.error('Instant capture error:', error)
    } finally {
      setIsCapturing(false)
    }
  }

  return (
    <button
      type="button"
      onClick={handleInstantCapture}
      disabled={isCapturing || disabled}
      className={`flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors ${className}`}
      aria-label={isCapturing ? 'Capturing...' : 'Instant Capture'}
    >
      <CameraIcon className="w-5 h-5" />
      <span>{isCapturing ? 'Capturing...' : 'Instant Capture'}</span>
    </button>
  )
}
