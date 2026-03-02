import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// @ts-expect-error — api.js has no type declarations (pre-migration)
import { getGpsConfig, updateGpsConfig, getGpsStatus, syncGps } from '../utils/api'
// @ts-expect-error — helpers.js has no type declarations (pre-migration)
import { formatTimestamp } from '../utils/helpers'
import { formatCoordinateDisplay } from '../utils/gpsCoordinates'
import { GPS_PRECISION_OPTIONS, getGpsPrecision, setGpsPrecision } from '../utils/gpsPrecision'
// @ts-expect-error — queryKeys.js has no type declarations (pre-migration)
import { QUERY_KEYS } from '../utils/queryKeys'
import { useEffect, useMemo, useRef, useState } from 'react'
// Resolver type import is only needed for the zodResolver cast workaround — remove with TODO(#485)
import { Controller, useForm, type Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  gpsSettingsSchema,
  GPS_SETTINGS_DEFAULTS,
  type GpsSettingsFormData,
} from '../schemas/gps-settings'
import toast from 'react-hot-toast'
// @ts-expect-error — CollapsibleCard.jsx has no type declarations (pre-migration)
import CollapsibleCard from './CollapsibleCard'
// @ts-expect-error — ConfirmDialog.jsx has no type declarations (pre-migration)
import ConfirmDialog from './common/ConfirmDialog'
// @ts-expect-error — useGpsExif.js has no type declarations (pre-migration)
import { useGpsExifStatus, useGpsExifConfig, useUpdateGpsExifConfig } from '../hooks/useGpsExif'

export default function GPSSettings() {
  const queryClient = useQueryClient()

  // zodResolver's Zod 4 overload expects $ZodType<Output, FieldValues> but
  // Zod 4's public ZodType uses `unknown` for its input parameter (z.coerce).
  // The cast through `unknown` is safe because the schema validates the same
  // shape at runtime. TODO(#485): Remove when @hookform/resolvers aligns with Zod 4.
  const { register, reset, handleSubmit, watch, getValues, setValue, control, formState: { errors, isDirty, isValid } } = useForm<GpsSettingsFormData>({
    resolver: zodResolver(gpsSettingsSchema as unknown as Parameters<typeof zodResolver>[0]) as unknown as Resolver<GpsSettingsFormData>,
    defaultValues: GPS_SETTINGS_DEFAULTS,
    mode: 'onTouched',
  })

  const pendingValues = useRef<GpsSettingsFormData | null>(null)

  const [isCollapsed, setIsCollapsed] = useState(false)
  const [timeoutsCollapsed, setTimeoutsCollapsed] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [showRestartConfirm, setShowRestartConfirm] = useState(false)
  const [gpsPrecision, setGpsPrecisionState] = useState(() => getGpsPrecision())
  const [exifSectionOpen, setExifSectionOpen] = useState(false)
  const [selectedSource, setSelectedSource] = useState('deployment,gps')

  const { data: exifStatus } = useGpsExifStatus()
  const { data: exifConfig } = useGpsExifConfig()
  const updateExifConfig = useUpdateGpsExifConfig()

  // Update selected source when config loads
  useEffect(() => {
    if (exifConfig?.default_sources) {
      setSelectedSource(exifConfig.default_sources.join(','))
    }
  }, [exifConfig])

  // Handle precision change
  const handlePrecisionChange = (newPrecision: string) => {
    const precision = parseInt(newPrecision, 10)
    setGpsPrecisionState(precision)
    if (!setGpsPrecision(precision)) {
      toast.error('Precision changed but could not be saved (private browsing?)', { duration: 4000 })
    }
  }

  const { data: gpsConfig, isLoading: configLoading } = useQuery({
    queryKey: QUERY_KEYS.GPS_CONFIG,
    queryFn: () => getGpsConfig().then((res: { data: unknown }) => {
      const result = gpsSettingsSchema.safeParse(res.data)
      if (!result.success) {
        console.warn('GPS config from server failed validation:', result.error)
        return { ...GPS_SETTINGS_DEFAULTS, ...(res.data as Partial<GpsSettingsFormData>) }
      }
      return result.data
    }),
  })

  // Sync form with query data. While the user is editing (isDirty), incoming
  // polling updates are ignored to prevent overwriting keystrokes. Config changes
  // made elsewhere will only take effect after the user saves or discards.
  useEffect(() => {
    if (gpsConfig && !isDirty) {
      reset(gpsConfig)
    }
  }, [gpsConfig, isDirty, reset])

  const { data: gpsStatus } = useQuery({
    queryKey: QUERY_KEYS.GPS_STATUS,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    queryFn: () => getGpsStatus().then((res: { data: any }) => res.data),
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

  // TODO(#197): Type mutation generics once api.js is migrated to TypeScript
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const updateConfigMutation = useMutation<any, any, Record<string, unknown>>({
    mutationFn: updateGpsConfig,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onSuccess: (response: any) => {
      queryClient.invalidateQueries(QUERY_KEYS.GPS_CONFIG)
      queryClient.invalidateQueries(QUERY_KEYS.GPS_STATUS)

      if (response.data.gpsd_restarted) {
        toast.success('GPS configuration updated and service restarted!', { duration: 4000 })
      } else {
        toast.success('GPS configuration updated successfully!')
      }
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      const message = error.response?.data?.message || error.response?.data?.error || 'Failed to update GPS config'
      toast.error(`Error: ${message}`, { duration: 6000 })
    },
  })

  // Helper to format GPS state description
  const formatGpsStateInfo = (gpstime: number) => {
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
    // Check server state, not form state — user may have toggled enabled without saving
    if (!gpsConfig?.enabled) {
      toast.error('GPS is disabled. Enable it first.')
      return
    }
    const values = getValues()

    setSyncing(true)

    // Get expected GPS state based on last sync
    const stateInfo = formatGpsStateInfo(gpsStatus?.gpstime || 0)

    // Read timeout values from the form (not server state) so the progress
    // timer reflects whatever the user currently sees in the UI sliders, even
    // if those values haven't been saved yet. This keeps the displayed estimate
    // consistent with the user's intent.
    const timeoutMap: Record<string, number> = {
      'hot_start': values.timeout_hot,
      'warm_start': values.timeout_warm,
      'cold_start': values.timeout_cold,
      'almanac_expired': values.timeout_almanac,
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
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (error: any) {
      clearInterval(progressInterval)
      toast.dismiss(toastId)
      const message = error.response?.data?.message || error.message
      const isTimeout = message.includes('timeout') || error.response?.status === 408

      if (isTimeout) {
        const timeoutValue = gpsConfig?.timeout ?? 60
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

  const submitConfig = (values: GpsSettingsFormData) => {
    updateConfigMutation.mutate({
      gps_enabled: values.enabled,
      gps_device: values.device,
      gps_baudrate: values.baudrate,
      gps_timeout: values.timeout,
      gps_timeout_hot: values.timeout_hot,
      gps_timeout_warm: values.timeout_warm,
      gps_timeout_cold: values.timeout_cold,
      gps_timeout_almanac: values.timeout_almanac,
    })
  }

  const handleSaveConfig = (values: GpsSettingsFormData) => {
    if (!gpsConfig) { submitConfig(values); return }

    const deviceChanged = values.device !== gpsConfig.device
    const baudrateChanged = values.baudrate !== gpsConfig.baudrate

    if (deviceChanged || baudrateChanged) {
      pendingValues.current = values
      setShowRestartConfirm(true)
      return
    }

    submitConfig(values)
  }

  const doSaveConfig = () => {
    setShowRestartConfirm(false)
    if (!pendingValues.current) {
      console.error('doSaveConfig called without pending values')
      toast.error('Unable to save — please try again.')
      return
    }
    submitConfig(pendingValues.current)
    pendingValues.current = null
  }

  const [enabled, device, timeout_hot, timeout_warm, timeout_cold, timeout_almanac] =
    watch(['enabled', 'device', 'timeout_hot', 'timeout_warm', 'timeout_cold', 'timeout_almanac'])

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
              {...register('enabled')}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>

        {enabled && (
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
                  {errors.device && (
                    <span className="ml-2 text-red-600 text-xs">✗</span>
                  )}
                  {!errors.device && device && (
                    <span className="ml-2 text-green-600 text-xs">✓</span>
                  )}
                </label>
                <input
                  type="text"
                  {...register('device')}
                  placeholder="/dev/ttyAMA0"
                  aria-label="GPS Device Path"
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
                    errors.device
                      ? 'border-red-300 focus:ring-red-500 bg-red-50'
                      : device
                      ? 'border-green-300 focus:ring-green-500 bg-green-50'
                      : 'border-gray-300 focus:ring-blue-500'
                  }`}
                />
                {errors.device ? (
                  <p className="text-xs text-red-600 mt-1">
                    ⚠️ {errors.device.message}
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
                  {!errors.baudrate && (
                    <span className="ml-2 text-green-600 text-xs">✓</span>
                  )}
                </label>
                {/* Controller keeps RHF's ref attached to the DOM element.
                    Manual Number() cast is needed because <select> produces
                    strings; z.coerce.number() only runs at validation time. */}
                <Controller
                  name="baudrate"
                  control={control}
                  render={({ field }) => (
                    <select
                      {...field}
                      value={String(field.value)}
                      onChange={(e) => field.onChange(Number(e.target.value))}
                      aria-label="Baud Rate"
                      className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
                        errors.baudrate
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
                  )}
                />
                {errors.baudrate ? (
                  <p className="text-xs text-red-600 mt-1">
                    ⚠️ {errors.baudrate.message}
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

              {/* EXIF Tagging Configuration */}
              <div className="border border-gray-300 rounded-md p-3">
                <div
                  className="flex justify-between items-center cursor-pointer select-none"
                  onClick={() => setExifSectionOpen(!exifSectionOpen)}
                >
                  <h5 className="text-sm font-medium text-gray-700">EXIF Tagging</h5>
                  <span className="text-gray-500 text-sm">
                    {exifSectionOpen ? '▼' : '▶'}
                  </span>
                </div>

                {exifSectionOpen && (
                  <div className="mt-3 space-y-3">
                    {/* Default Coordinate Source */}
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Default Coordinate Source
                      </label>
                      <select
                        value={selectedSource}
                        onChange={(e) => setSelectedSource(e.target.value)}
                        aria-label="Default Coordinate Source"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                      >
                        <option value="deployment,gps">Deployment → GPS fallback</option>
                        <option value="gps">GPS only</option>
                        <option value="manual">Manual coordinates</option>
                      </select>
                      <p className="text-xs text-gray-500 mt-1">
                        Where to get GPS coordinates for tagging photos
                      </p>
                    </div>

                    {/* Service Status */}
                    {exifStatus?.service_status && (
                      <div className="text-xs text-gray-600">
                        <span className="font-medium">Service:</span>{' '}
                        <span className={
                          exifStatus.service_status === 'running' ? 'text-green-600 font-medium' :
                          exifStatus.service_status === 'stopped' ? 'text-yellow-600' :
                          'text-gray-600'
                        }>
                          {exifStatus.service_status}
                        </span>
                      </div>
                    )}

                    {/* Tagged Count */}
                    {exifStatus?.tagged_count != null && (
                      <div className="text-xs text-gray-600">
                        <span className="font-medium">Photos tagged:</span> {exifStatus.tagged_count}
                      </div>
                    )}

                    {/* Save Button */}
                    <button
                      onClick={() => updateExifConfig.mutate({ default_sources: selectedSource.split(',') })}
                      disabled={updateExifConfig.isPending}
                      className="w-full px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                    >
                      {updateExifConfig.isPending ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                )}
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
                        🟢 Hot Start (&lt;4 hours): {timeout_hot}s
                      </label>
                      <input
                        type="range"
                        min="5"
                        max="60"
                        step="5"
                        {...register('timeout_hot', { valueAsNumber: true })}
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
                        🟡 Warm Start (4h-6d): {timeout_warm}s
                      </label>
                      <input
                        type="range"
                        min="30"
                        max="180"
                        step="10"
                        {...register('timeout_warm', { valueAsNumber: true })}
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
                        🟠 Cold Start (6-28d): {timeout_cold}s
                      </label>
                      <input
                        type="range"
                        min="60"
                        max="300"
                        step="10"
                        {...register('timeout_cold', { valueAsNumber: true })}
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
                        🔴 Almanac Expired (&gt;28d): {Math.floor(timeout_almanac / 60)}m
                      </label>
                      <input
                        type="range"
                        min="300"
                        max="1800"
                        step="60"
                        {...register('timeout_almanac', { valueAsNumber: true })}
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
                      type="button"
                      onClick={() => {
                        setValue('timeout_hot', GPS_SETTINGS_DEFAULTS.timeout_hot, { shouldDirty: true })
                        setValue('timeout_warm', GPS_SETTINGS_DEFAULTS.timeout_warm, { shouldDirty: true })
                        setValue('timeout_cold', GPS_SETTINGS_DEFAULTS.timeout_cold, { shouldDirty: true })
                        setValue('timeout_almanac', GPS_SETTINGS_DEFAULTS.timeout_almanac, { shouldDirty: true })
                      }}
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
                onClick={handleSubmit(handleSaveConfig)}
                disabled={updateConfigMutation.isPending || !isValid}
                className="flex-1 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                title={!isValid ? 'Please fix validation errors' : ''}
              >
                {updateConfigMutation.isPending ? 'Saving...' : '💾 Save Configuration'}
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
        onClose={() => { setShowRestartConfirm(false); pendingValues.current = null }}
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
