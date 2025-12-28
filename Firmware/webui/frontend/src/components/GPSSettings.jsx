import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getGpsConfig, updateGpsConfig, getGpsStatus, syncGps } from '../utils/api'
import { formatTimestamp } from '../utils/helpers'
import { validateDevicePath, validateBaudrate } from '../utils/gpsValidation'
import { formatCoordinateDisplay } from '../utils/gpsCoordinates'
import { GPS_PRECISION_OPTIONS, getGpsPrecision, setGpsPrecision } from '../utils/gpsPrecision'
import { QUERY_KEYS } from '../utils/queryKeys'
import { useState, useEffect, useMemo } from 'react'
import toast from 'react-hot-toast'
import CollapsibleCard from './CollapsibleCard'
import ConfirmDialog from './common/ConfirmDialog'

export default function GPSSettings() {
  const queryClient = useQueryClient()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [timeoutsCollapsed, setTimeoutsCollapsed] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [localConfig, setLocalConfig] = useState(null)
  const [validationErrors, setValidationErrors] = useState({})
  const [showRestartConfirm, setShowRestartConfirm] = useState(false)
  const [gpsPrecision, setGpsPrecisionState] = useState(() => getGpsPrecision())

  // Handle precision change
  const handlePrecisionChange = (newPrecision) => {
    const precision = parseInt(newPrecision, 10)
    setGpsPrecisionState(precision)
    setGpsPrecision(precision)
  }

  const { data: gpsConfig, isLoading: configLoading } = useQuery({
    queryKey: QUERY_KEYS.GPS_CONFIG,
    queryFn: () => getGpsConfig().then(res => res.data),
  })

  // Sync local config with query data (replaces deprecated onSuccess)
  useEffect(() => {
    if (gpsConfig) {
      setLocalConfig(gpsConfig)
    }
  }, [gpsConfig])

  const { data: gpsStatus } = useQuery({
    queryKey: QUERY_KEYS.GPS_STATUS,
    queryFn: () => getGpsStatus().then(res => res.data),
    // Pause polling during sync to avoid spam, otherwise poll every 15s
    refetchInterval: () => syncing ? false : 15000,
  })

  // Memoize formatted coordinates to avoid unnecessary re-renders
  // Defensive: parseFloat("N/A") returns NaN, which would throw in formatCoordinateDisplay
  const formattedCurrentLat = useMemo(() => {
    const val = parseFloat(gpsStatus?.latitude)
    return !Number.isNaN(val) ? formatCoordinateDisplay(val, true, 'dms', gpsPrecision) : null
  }, [gpsStatus?.latitude, gpsPrecision])

  const formattedCurrentLon = useMemo(() => {
    const val = parseFloat(gpsStatus?.longitude)
    return !Number.isNaN(val) ? formatCoordinateDisplay(val, false, 'dms', gpsPrecision) : null
  }, [gpsStatus?.longitude, gpsPrecision])

  const formattedLastLat = useMemo(() => {
    const val = parseFloat(gpsStatus?.last_known_lat)
    return !Number.isNaN(val) ? formatCoordinateDisplay(val, true, 'dms', gpsPrecision) : null
  }, [gpsStatus?.last_known_lat, gpsPrecision])

  const formattedLastLon = useMemo(() => {
    const val = parseFloat(gpsStatus?.last_known_lon)
    return !Number.isNaN(val) ? formatCoordinateDisplay(val, false, 'dms', gpsPrecision) : null
  }, [gpsStatus?.last_known_lon, gpsPrecision])

  const updateConfigMutation = useMutation({
    mutationFn: updateGpsConfig,
    onSuccess: (response) => {
      queryClient.invalidateQueries(QUERY_KEYS.GPS_CONFIG)
      queryClient.invalidateQueries(QUERY_KEYS.GPS_STATUS)

      if (response.data.gpsd_restarted) {
        toast.success('GPS configuration updated and service restarted!', { duration: 4000 })
      } else {
        toast.success('GPS configuration updated successfully!')
      }
    },
    onError: (error) => {
      const message = error.response?.data?.message || error.response?.data?.error || 'Failed to update GPS config'
      toast.error(`Error: ${message}`, { duration: 6000 })
    },
  })

  // Helper to format GPS state description
  const formatGpsStateInfo = (gpstime) => {
    if (gpstime === 0) {
      return { state: 'almanac_expired', time: '5-20 min', description: 'First sync (almanac download)' }
    }
    const hoursSince = (Date.now() / 1000 - gpstime) / 3600
    if (hoursSince < 4) {
      return { state: 'hot_start', time: '~15s', description: 'Hot start (recent data)' }
    } else if (hoursSince < 144) {
      return { state: 'warm_start', time: '~60s', description: 'Warm start (ephemeris refresh)' }
    } else if (hoursSince < 672) {
      return { state: 'cold_start', time: '~90s', description: 'Cold start (ephemeris download)' }
    } else {
      return { state: 'almanac_expired', time: '5-20 min', description: 'Almanac expired (full download)' }
    }
  }

  const handleSyncGPS = async () => {
    if (!gpsConfig?.enabled) {
      toast.error('GPS is disabled. Enable it first.')
      return
    }

    setSyncing(true)

    // Get expected GPS state based on last sync
    const stateInfo = formatGpsStateInfo(gpsStatus?.gpstime || 0)

    // Use actual configured timeout values based on GPS state
    const timeoutMap = {
      'hot_start': localConfig?.timeout_hot || 15,
      'warm_start': localConfig?.timeout_warm || 60,
      'cold_start': localConfig?.timeout_cold || 90,
      'almanac_expired': localConfig?.timeout_almanac || 1200
    }
    const expectedSeconds = timeoutMap[stateInfo.state] || 60

    // Show initial progress toast
    let toastId = toast.loading(
      `🛰️ Acquiring GPS fix... (0s elapsed)\n` +
      `Expected: ${stateInfo.description}\n` +
      `Est. time: ${stateInfo.time}`,
      { duration: Infinity }
    )

    // Recreate toast every 20 seconds to reset React Hot Toast's internal duration timer
    // (React Hot Toast auto-dismisses after ~60s even with duration:Infinity)
    const startTime = Date.now()
    const progressInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000)
      const remaining = Math.max(0, expectedSeconds - elapsed)

      // Dismiss old toast and create new one to reset duration timer
      toast.dismiss(toastId)
      toastId = toast.loading(
        `🛰️ Acquiring GPS fix... (${elapsed}s elapsed)\n` +
        `Expected: ${stateInfo.description}\n` +
        `Est. remaining: ~${remaining}s`,
        { duration: Infinity }
      )
    }, 20000)  // Every 20 seconds (provides safety margin against 60s auto-dismiss)

    try {
      const result = await syncGps()
      clearInterval(progressInterval)
      toast.dismiss(toastId)

      if (result.data.success) {
        const stateLabel = result.data.gps_state?.replace('_', ' ') || 'sync'
        toast.success(
          `✅ GPS synced successfully! (${stateLabel})\n` +
          `📍 Location: ${result.data.latitude}, ${result.data.longitude}\n` +
          `🕐 Time: ${result.data.gpstime || 'synced'}\n` +
          `🛰️ Satellites: ${result.data.satellites_used || '?'} used\n` +
          `📊 Timeout used: ${result.data.timeout_used}s`,
          { duration: 6000 }
        )
      } else {
        toast.error(
          `⚠️ GPS sync timeout: No fix acquired\n\n` +
          `Troubleshooting:\n` +
          `• Ensure GPS module is connected to GPIO pins\n` +
          `• Move to location with clear sky view\n` +
          `• Check antenna connection\n` +
          `• Allow 1-2 minutes for cold start\n` +
          `• Verify device path in configuration`,
          { duration: 8000 }
        )
      }
      queryClient.invalidateQueries(QUERY_KEYS.GPS_STATUS)
      queryClient.invalidateQueries(QUERY_KEYS.SYSTEM_STATUS)
    } catch (error) {
      clearInterval(progressInterval)
      toast.dismiss(toastId)
      const message = error.response?.data?.message || error.message
      const isTimeout = message.includes('timeout') || error.response?.status === 408

      if (isTimeout) {
        const timeoutValue = localConfig?.timeout || 60
        toast.error(
          `⏱️ GPS sync timeout (${timeoutValue}s)\n\n` +
          `Troubleshooting:\n` +
          `• Increase timeout in settings (currently ${timeoutValue}s)\n` +
          `• Move to location with clear sky view\n` +
          `• Check GPS module LED for activity\n` +
          `• Verify hardware connections\n` +
          `• Cold start can take 30-60s`,
          { duration: 10000 }
        )
      } else {
        toast.error(
          `❌ GPS sync failed: ${message}\n\n` +
          `Check:\n` +
          `• GPS device path (${gpsConfig?.device})\n` +
          `• Hardware connections\n` +
          `• System logs for details`,
          { duration: 8000 }
        )
      }
    } finally {
      setSyncing(false)
    }
  }

  // Validate config changes in real-time
  const handleDeviceChange = (newDevice) => {
    setLocalConfig({...localConfig, device: newDevice})
    const validation = validateDevicePath(newDevice)
    setValidationErrors(prev => ({
      ...prev,
      device: validation.valid ? null : validation.error
    }))
  }

  const handleBaudrateChange = (newBaudrate) => {
    setLocalConfig({...localConfig, baudrate: newBaudrate})
    const validation = validateBaudrate(newBaudrate)
    setValidationErrors(prev => ({
      ...prev,
      baudrate: validation.valid ? null : validation.error
    }))
  }

  // Removed - timeout field no longer used (replaced by adaptive timeouts)

  // Check if form is valid
  const isFormValid = () => {
    if (!localConfig) return false
    return !validationErrors.device && !validationErrors.baudrate && !validationErrors.timeout
  }

  const handleSaveConfig = () => {
    if (!isFormValid()) {
      toast.error('Please fix validation errors before saving')
      return
    }

    // Check if device or baudrate changed (requires gpsd restart)
    const deviceChanged = localConfig.device !== gpsConfig.device
    const baudrateChanged = localConfig.baudrate !== gpsConfig.baudrate

    if (deviceChanged || baudrateChanged) {
      // Show warning that gpsd will restart
      setShowRestartConfirm(true)
      return
    }

    doSaveConfig()
  }

  const doSaveConfig = () => {
    setShowRestartConfirm(false)
    updateConfigMutation.mutate({
      gps_enabled: localConfig.enabled,
      gps_device: localConfig.device,
      gps_baudrate: localConfig.baudrate,
      gps_timeout: localConfig.timeout,
      gps_timeout_hot: localConfig.timeout_hot,
      gps_timeout_warm: localConfig.timeout_warm,
      gps_timeout_cold: localConfig.timeout_cold,
      gps_timeout_almanac: localConfig.timeout_almanac
    })
  }

  if (configLoading) {
    return <div className="text-gray-500">Loading GPS configuration...</div>
  }

  return (
    <CollapsibleCard
      id="gpsConfig"
      title="🛰️ GPS Module Configuration"
      isCollapsed={isCollapsed}
      onToggle={() => setIsCollapsed(!isCollapsed)}
      className="settings-card-lg"
    >
      <div className="space-y-4">
        {/* GPS Enable/Disable Toggle */}
        <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
          <div>
            <label className="font-medium text-gray-700">Enable GPS Module</label>
            <p className="text-xs text-gray-500">NEO-M8N GPS for time sync and location</p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={localConfig?.enabled || false}
              onChange={(e) => setLocalConfig({...localConfig, enabled: e.target.checked})}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>

        {localConfig?.enabled && (
          <>
            {/* Current GPS Status */}
            {gpsStatus && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded">
                <h5 className="font-medium text-blue-900 mb-2">Current GPS Status</h5>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {/* Left Column: Fix Status and Location */}
                  <div className="space-y-1">
                    <div className="flex items-center">
                      <div className={`w-2 h-2 rounded-full mr-2 ${
                        gpsStatus.has_fix ? 'bg-green-500' : 'bg-red-500'
                      }`}></div>
                      <span className="text-blue-800 font-medium">
                        {gpsStatus.has_fix ? (
                          gpsStatus.fix_mode === 3 ? '3D Fix' : gpsStatus.fix_mode === 2 ? '2D Fix' : 'GPS Fix'
                        ) : 'No GPS Fix'}
                      </span>
                    </div>
                    {gpsStatus.has_fix && (
                      <>
                        <p className="text-blue-700 text-xs">
                          <span className="font-medium">Lat:</span>{' '}
                          {formattedCurrentLat}
                        </p>
                        <p className="text-blue-700 text-xs">
                          <span className="font-medium">Lon:</span>{' '}
                          {formattedCurrentLon}
                        </p>
                        <p className="text-blue-700 text-xs">
                          <span className="font-medium">UTC Offset:</span> {gpsStatus.utc_offset}h
                        </p>
                      </>
                    )}
                    <p className="text-blue-700 text-xs">
                      <span className="font-medium">Last Sync:</span> {formatTimestamp(gpsStatus.gpstime)}
                    </p>

                    {/* Last Known Position */}
                    {gpsStatus.has_last_known_position && !gpsStatus.has_fix && (
                      <div className="mt-2 pt-2 border-t border-blue-300">
                        <p className="text-blue-700 font-medium mb-1 text-xs">Last Known Position:</p>
                        <p className="text-blue-700 text-xs">
                          📍 {formattedLastLat},{' '}
                          {formattedLastLon}
                        </p>
                        <p className="text-blue-700 text-xs">
                          <span className="font-medium">Acquired:</span> {formatTimestamp(gpsStatus.last_position_time)}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Right Column: Quality Metrics */}
                  <div className="space-y-1">
                    <p className="text-blue-800 font-medium text-xs mb-1">Signal Quality:</p>
                    <p className="text-blue-700 text-xs">
                      <span className="font-medium">🛰️ Satellites:</span>{' '}
                      {gpsStatus.satellites_used || 0}/{gpsStatus.satellites_visible || 0}
                    </p>
                    <p className="text-blue-700 text-xs">
                      <span className="font-medium">HDOP:</span>{' '}
                      <span className={
                        gpsStatus.hdop < 2 ? 'text-green-700 font-medium' :
                        gpsStatus.hdop < 5 ? 'text-yellow-700' :
                        'text-red-700'
                      }>
                        {gpsStatus.hdop?.toFixed(2) || 'N/A'}
                      </span>
                      {gpsStatus.hdop < 2 && ' (Excellent)'}
                      {gpsStatus.hdop >= 2 && gpsStatus.hdop < 5 && ' (Good)'}
                      {gpsStatus.hdop >= 5 && gpsStatus.hdop < 10 && ' (Fair)'}
                      {gpsStatus.hdop >= 10 && ' (Poor)'}
                    </p>
                    <p className="text-blue-700 text-xs">
                      <span className="font-medium">PDOP:</span> {gpsStatus.pdop?.toFixed(2) || 'N/A'}
                    </p>
                    {(() => {
                      const stateInfo = formatGpsStateInfo(gpsStatus.gpstime || 0)
                      return (
                        <p className="text-blue-700 text-xs">
                          <span className="font-medium">Next sync:</span>{' '}
                          {stateInfo.time} ({stateInfo.state.replace('_', ' ')})
                        </p>
                      )
                    })()}
                  </div>
                </div>
              </div>
            )}

            {/* GPS Configuration */}
            <div className="space-y-3">
              {/* Device Path */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  GPS Device Path
                  {validationErrors.device && (
                    <span className="ml-2 text-red-600 text-xs">✗</span>
                  )}
                  {!validationErrors.device && localConfig?.device && (
                    <span className="ml-2 text-green-600 text-xs">✓</span>
                  )}
                </label>
                <input
                  type="text"
                  value={localConfig?.device || ''}
                  onChange={(e) => handleDeviceChange(e.target.value)}
                  placeholder="/dev/ttyAMA0"
                  aria-label="GPS Device Path"
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
                    validationErrors.device
                      ? 'border-red-300 focus:ring-red-500 bg-red-50'
                      : localConfig?.device
                      ? 'border-green-300 focus:ring-green-500 bg-green-50'
                      : 'border-gray-300 focus:ring-blue-500'
                  }`}
                />
                {validationErrors.device ? (
                  <p className="text-xs text-red-600 mt-1">
                    ⚠️ {validationErrors.device}
                  </p>
                ) : (
                  <p className="text-xs text-gray-500 mt-1">
                    UART device path (typically /dev/ttyAMA0 for Pi GPIO UART)
                  </p>
                )}
              </div>

              {/* Baud Rate */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Baud Rate
                  {!validationErrors.baudrate && (
                    <span className="ml-2 text-green-600 text-xs">✓</span>
                  )}
                </label>
                <select
                  value={localConfig?.baudrate || 9600}
                  onChange={(e) => handleBaudrateChange(parseInt(e.target.value))}
                  aria-label="Baud Rate"
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
                    validationErrors.baudrate
                      ? 'border-red-300 focus:ring-red-500 bg-red-50'
                      : 'border-green-300 focus:ring-green-500 bg-green-50'
                  }`}
                >
                  <option value="4800">4800</option>
                  <option value="9600">9600 (Default)</option>
                  <option value="19200">19200</option>
                  <option value="38400">38400</option>
                  <option value="57600">57600</option>
                  <option value="115200">115200</option>
                </select>
                {validationErrors.baudrate ? (
                  <p className="text-xs text-red-600 mt-1">
                    ⚠️ {validationErrors.baudrate}
                  </p>
                ) : (
                  <p className="text-xs text-gray-500 mt-1">
                    Serial communication speed (9600 is default for NEO-M8N)
                  </p>
                )}
              </div>

              {/* GPS Coordinate Precision */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Coordinate Display Precision
                </label>
                <select
                  value={gpsPrecision}
                  onChange={(e) => handlePrecisionChange(e.target.value)}
                  aria-label="GPS Coordinate Precision"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {GPS_PRECISION_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label} - {option.description}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Controls decimal places shown for GPS coordinates throughout the UI (display only - does not affect GPS accuracy)
                </p>
              </div>

              {/* Advanced Timeout Configuration */}
              <div className="border border-gray-300 rounded-md p-3">
                <div
                  className="flex justify-between items-center cursor-pointer select-none"
                  onClick={() => setTimeoutsCollapsed(!timeoutsCollapsed)}
                >
                  <h5 className="text-sm font-medium text-gray-700">⚙️ Advanced Timeout Configuration</h5>
                  <span className="text-gray-500 text-sm">
                    {timeoutsCollapsed ? '▶' : '▼'}
                  </span>
                </div>

                {!timeoutsCollapsed && (
                  <div className="mt-3 space-y-3">
                    <p className="text-xs text-gray-600">
                      Adaptive timeouts automatically adjust based on GPS state. Customize for your environment:
                    </p>

                    {/* Hot Start Timeout */}
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        🟢 Hot Start (&lt;4 hours): {localConfig?.timeout_hot || 15}s
                      </label>
                      <input
                        type="range"
                        min="5"
                        max="60"
                        step="5"
                        value={localConfig?.timeout_hot || 15}
                        onChange={(e) => setLocalConfig({...localConfig, timeout_hot: parseInt(e.target.value)})}
                        className="w-full"
                      />
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>5s</span>
                        <span>60s</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">GPS has recent data, ~1s TTFF</p>
                    </div>

                    {/* Warm Start Timeout */}
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        🟡 Warm Start (4h-6d): {localConfig?.timeout_warm || 60}s
                      </label>
                      <input
                        type="range"
                        min="30"
                        max="180"
                        step="10"
                        value={localConfig?.timeout_warm || 60}
                        onChange={(e) => setLocalConfig({...localConfig, timeout_warm: parseInt(e.target.value)})}
                        className="w-full"
                      />
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>30s</span>
                        <span>180s</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Needs fresh ephemeris, ~26s TTFF</p>
                    </div>

                    {/* Cold Start Timeout */}
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        🟠 Cold Start (6-28d): {localConfig?.timeout_cold || 90}s
                      </label>
                      <input
                        type="range"
                        min="60"
                        max="300"
                        step="10"
                        value={localConfig?.timeout_cold || 90}
                        onChange={(e) => setLocalConfig({...localConfig, timeout_cold: parseInt(e.target.value)})}
                        className="w-full"
                      />
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>60s</span>
                        <span>300s</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Downloads ephemeris, 26-57s TTFF</p>
                    </div>

                    {/* Almanac Expired Timeout */}
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        🔴 Almanac Expired (&gt;28d): {Math.floor((localConfig?.timeout_almanac || 1200) / 60)}m
                      </label>
                      <input
                        type="range"
                        min="300"
                        max="1800"
                        step="60"
                        value={localConfig?.timeout_almanac || 1200}
                        onChange={(e) => setLocalConfig({...localConfig, timeout_almanac: parseInt(e.target.value)})}
                        className="w-full"
                      />
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>5min</span>
                        <span>30min</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Full almanac download, 12-20min worst case</p>
                    </div>

                    {/* Reset to Defaults Button */}
                    <button
                      onClick={() => setLocalConfig({
                        ...localConfig,
                        timeout_hot: 15,
                        timeout_warm: 60,
                        timeout_cold: 90,
                        timeout_almanac: 1200
                      })}
                      className="w-full px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                    >
                      Reset to Defaults
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={handleSyncGPS}
                disabled={syncing}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {syncing ? 'Syncing...' : '🛰️ Sync GPS Now'}
              </button>
              <button
                onClick={handleSaveConfig}
                disabled={updateConfigMutation.isLoading || !isFormValid()}
                className="flex-1 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                title={!isFormValid() ? 'Please fix validation errors' : ''}
              >
                {updateConfigMutation.isLoading ? 'Saving...' : '💾 Save Configuration'}
              </button>
            </div>

            {/* Hardware Setup Info */}
            <div className="settings-info-box bg-blue-50 border-blue-200">
              <p className="text-xs text-blue-800 font-medium mb-1">📘 Hardware Setup Required:</p>
              <ul className="text-xs text-blue-700 space-y-0.5 ml-4 list-disc">
                <li>Connect NEO-M8N TX → Pi GPIO15 (RX)</li>
                <li>Connect NEO-M8N RX → Pi GPIO14 (TX)</li>
                <li>Enable UART in /boot/config.txt: <code className="bg-blue-100 px-1">enable_uart=1</code></li>
                <li>Install gpsd: <code className="bg-blue-100 px-1">sudo apt install gpsd gpsd-clients</code></li>
              </ul>
            </div>

            {/* Cold Start Information */}
            <div className="settings-info-box bg-yellow-50 border-yellow-200">
              <p className="text-xs text-yellow-800 font-medium mb-1">⏱️ GPS Sync Times (Time To First Fix):</p>
              <ul className="text-xs text-yellow-700 space-y-0.5 ml-4 list-disc">
                <li><strong>Hot Start (&lt;4 hours):</strong> ~15 seconds - GPS has recent satellite data</li>
                <li><strong>Warm Start (4 hours - 6 days):</strong> ~60 seconds - Needs fresh ephemeris</li>
                <li><strong>Cold Start (6-28 days):</strong> ~90 seconds - Must download ephemeris</li>
                <li><strong>Almanac Expired (&gt;28 days):</strong> 5-20 minutes - Full almanac download required</li>
              </ul>
              <p className="text-xs text-yellow-700 mt-2">
                💡 <strong>Tip:</strong> First sync after long power-off can take several minutes. Ensure clear sky view and be patient!
              </p>
            </div>
          </>
        )}
      </div>

      {/* GPS Service Restart Confirmation */}
      <ConfirmDialog
        isOpen={showRestartConfirm}
        onClose={() => setShowRestartConfirm(false)}
        onConfirm={doSaveConfig}
        title="Restart GPS Service?"
        message="Changing device or baud rate will restart the GPS service. Any GPS sync in progress will be interrupted."
        confirmLabel="Continue"
        variant="warning"
        isLoading={updateConfigMutation.isPending}
      />
    </CollapsibleCard>
  )
}
