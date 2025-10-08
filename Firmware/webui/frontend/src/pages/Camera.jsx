import { useState } from 'react'
import { capturePhoto } from '../utils/api'

export default function Camera() {
  const [capturing, setCapturing] = useState(false)
  const [lastCapture, setLastCapture] = useState(null)

  const handleCapture = async () => {
    setCapturing(true)
    try {
      const response = await capturePhoto()
      setLastCapture(response.data)
      alert('Photo captured successfully!')
    } catch (error) {
      console.error('Capture failed:', error)
      alert('Failed to capture photo')
    } finally {
      setCapturing(false)
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Camera Control</h2>

      {/* Camera Preview Placeholder */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Live Preview</h3>
        <div className="bg-gray-200 rounded-lg h-96 flex items-center justify-center">
          <p className="text-gray-500">Live preview coming soon (WebSocket)</p>
        </div>
      </div>

      {/* Capture Controls */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Capture Control</h3>
        <button
          onClick={handleCapture}
          disabled={capturing}
          className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 text-lg font-semibold"
        >
          {capturing ? 'Capturing...' : 'Capture Photo'}
        </button>

        {lastCapture && (
          <div className="mt-4 p-4 bg-green-50 rounded-lg">
            <p className="text-green-800 font-medium">Last capture successful!</p>
            {lastCapture.latest_photo && (
              <p className="text-sm text-green-600 mt-1">
                Photo: {lastCapture.latest_photo}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
