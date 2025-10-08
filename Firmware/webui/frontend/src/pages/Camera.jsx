import { useState, useEffect, useRef } from 'react'
import { capturePhoto } from '../utils/api'
import { io } from 'socket.io-client'

export default function Camera() {
  const [capturing, setCapturing] = useState(false)
  const [lastCapture, setLastCapture] = useState(null)
  const [previewActive, setPreviewActive] = useState(false)
  const [currentFrame, setCurrentFrame] = useState(null)
  const [connected, setConnected] = useState(false)
  const socketRef = useRef(null)

  useEffect(() => {
    // Connect to WebSocket server using current window location
    // This ensures it works whether accessed via localhost, IP, or hostname
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    const port = window.location.port || (window.location.protocol === 'https:' ? '443' : '80')
    const wsUrl = `${window.location.protocol}//${host}:${port}`

    console.log('Connecting to WebSocket at:', wsUrl)

    socketRef.current = io(wsUrl, {
      transports: ['websocket', 'polling']
    })

    socketRef.current.on('connect', () => {
      console.log('WebSocket connected')
      setConnected(true)
    })

    socketRef.current.on('disconnect', () => {
      console.log('WebSocket disconnected')
      setConnected(false)
      setPreviewActive(false)
    })

    socketRef.current.on('camera_frame', (data) => {
      setCurrentFrame(data.image)
    })

    socketRef.current.on('preview_status', (data) => {
      setPreviewActive(data.streaming)
    })

    return () => {
      if (socketRef.current) {
        socketRef.current.emit('stop_preview')
        socketRef.current.disconnect()
      }
    }
  }, [])

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

  const togglePreview = () => {
    if (!socketRef.current) return

    if (previewActive) {
      socketRef.current.emit('stop_preview')
      setCurrentFrame(null)
    } else {
      socketRef.current.emit('start_preview')
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Camera Control</h2>

      {/* Connection Status */}
      <div className={`px-4 py-2 rounded-lg ${connected ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
        <p className="text-sm">
          WebSocket: {connected ? '✓ Connected' : '✗ Disconnected'}
        </p>
      </div>

      {/* Camera Preview */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Live Preview</h3>
          <button
            onClick={togglePreview}
            disabled={!connected}
            className={`px-4 py-2 rounded-lg font-medium ${
              previewActive
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-green-600 text-white hover:bg-green-700'
            } disabled:bg-gray-400`}
          >
            {previewActive ? 'Stop Preview' : 'Start Preview'}
          </button>
        </div>

        <div className="bg-gray-900 rounded-lg overflow-hidden" style={{ minHeight: '400px' }}>
          {currentFrame ? (
            <img
              src={currentFrame}
              alt="Camera preview"
              className="w-full h-auto"
            />
          ) : (
            <div className="h-96 flex items-center justify-center">
              <p className="text-gray-400">
                {previewActive ? 'Loading preview...' : 'Click "Start Preview" to begin'}
              </p>
            </div>
          )}
        </div>

        {previewActive && (
          <p className="text-xs text-gray-500 mt-2">
            Preview running at ~10 FPS (1024x768) with continuous autofocus
          </p>
        )}
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
