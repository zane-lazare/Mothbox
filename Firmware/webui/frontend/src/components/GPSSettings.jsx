import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getGPSConfig, updateGPSConfig, getGPSStatus, syncGPS } from '../utils/api'
import { formatTimestamp } from '../utils/helpers'
import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'

// Collapsible Card Component (from Settings.jsx)
const CollapsibleCard = ({ id, title, isCollapsed, onToggle, children, className = "settings-card" }) => (
  <div className={className}>
    <div
      className="flex justify-between items-center cursor-pointer select-none"
      onClick={() => onToggle(id)}
    >
      <h4 className="settings-card-title mb-0">{title}</h4>
      <span className="text-gray-500 text-sm">
        {isCollapsed ? '▶' : '▼'}
      </span>
    </div>
    {!isCollapsed && <div className="mt-2">{children}</div>}
  </div>
)

export default function GPSSettings() {
  const queryClient = useQueryClient()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [localConfig, setLocalConfig] = useState(null)

  const { data: gpsConfig, isLoading: configLoading } = useQuery({
    queryKey: ['gps-config'],
    queryFn: () => getGPSConfig().then(res => res.data),
  })

  // Sync local config with query data (replaces deprecated onSuccess)
  useEffect(() => {
    if (gpsConfig) {
      setLocalConfig(gpsConfig)
    }
  }, [gpsConfig])

  const { data: gpsStatus } = useQuery({
    queryKey: ['gps-status'],
    queryFn: () => getGPSStatus().then(res => res.data),
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  const updateConfigMutation = useMutation({
    mutationFn: updateGPSConfig,
    onSuccess: () => {
      queryClient.invalidateQueries(['gps-config'])
      queryClient.invalidateQueries(['gps-status'])
      toast.success('GPS configuration updated successfully!')
    },
    onError: (error) => {
      const message = error.response?.data?.message || 'Failed to update GPS config'
      toast.error(`Error: ${message}`)
    },
  })

  const handleSyncGPS = async () => {
    if (!gpsConfig?.enabled) {
      toast.error('GPS is disabled. Enable it first.')
      return
    }

    setSyncing(true)
    try {
      const result = await syncGPS()
      if (result.data.success) {
        toast.success(`GPS synced! Location: ${result.data.latitude}, ${result.data.longitude}`)
      } else {
        toast.error('GPS sync failed: No fix acquired')
      }
      queryClient.invalidateQueries(['gps-status'])
      queryClient.invalidateQueries(['system-status'])
    } catch (error) {
      const message = error.response?.data?.message || error.message
      toast.error(`GPS sync failed: ${message}`)
    } finally {
      setSyncing(false)
    }
  }

  const handleSaveConfig = () => {
    updateConfigMutation.mutate({
      gps_enabled: localConfig.enabled,
      gps_device: localConfig.device,
      gps_baudrate: localConfig.baudrate,
      gps_timeout: localConfig.timeout
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
                <div className="space-y-1 text-sm">
                  <div className="flex items-center">
                    <div className={`w-2 h-2 rounded-full mr-2 ${
                      gpsStatus.has_fix ? 'bg-green-500' : 'bg-red-500'
                    }`}></div>
                    <span className="text-blue-800">
                      {gpsStatus.has_fix ? 'GPS Fix Acquired' : 'No GPS Fix'}
                    </span>
                  </div>
                  {gpsStatus.has_fix && (
                    <>
                      <p className="text-blue-700">
                        <span className="font-medium">Latitude:</span> {gpsStatus.latitude}
                      </p>
                      <p className="text-blue-700">
                        <span className="font-medium">Longitude:</span> {gpsStatus.longitude}
                      </p>
                      <p className="text-blue-700">
                        <span className="font-medium">UTC Offset:</span> {gpsStatus.utc_offset}h
                      </p>
                    </>
                  )}
                  <p className="text-blue-700">
                    <span className="font-medium">Last Sync:</span> {formatTimestamp(gpsStatus.gpstime)}
                  </p>
                </div>
              </div>
            )}

            {/* GPS Configuration */}
            <div className="space-y-3">
              {/* Device Path */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  GPS Device Path
                </label>
                <input
                  type="text"
                  value={localConfig?.device || ''}
                  onChange={(e) => setLocalConfig({...localConfig, device: e.target.value})}
                  placeholder="/dev/ttyAMA0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  UART device path (typically /dev/ttyAMA0 for Pi GPIO UART)
                </p>
              </div>

              {/* Baud Rate */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Baud Rate
                </label>
                <select
                  value={localConfig?.baudrate || 9600}
                  onChange={(e) => setLocalConfig({...localConfig, baudrate: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="4800">4800</option>
                  <option value="9600">9600 (Default)</option>
                  <option value="19200">19200</option>
                  <option value="38400">38400</option>
                  <option value="57600">57600</option>
                  <option value="115200">115200</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Serial communication speed (9600 is default for NEO-M8N)
                </p>
              </div>

              {/* Timeout */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Sync Timeout: {localConfig?.timeout || 10} seconds
                </label>
                <input
                  type="range"
                  min="5"
                  max="60"
                  step="5"
                  value={localConfig?.timeout || 10}
                  onChange={(e) => setLocalConfig({...localConfig, timeout: parseInt(e.target.value)})}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>5s (Fast)</span>
                  <span>60s (Long)</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  How long to wait for GPS fix before timing out (actual timeout may be up to 20 seconds longer for processing overhead)
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={handleSyncGPS}
                disabled={syncing}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400"
              >
                {syncing ? 'Syncing...' : '🛰️ Sync GPS Now'}
              </button>
              <button
                onClick={handleSaveConfig}
                disabled={updateConfigMutation.isLoading}
                className="flex-1 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:bg-gray-400"
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
          </>
        )}
      </div>
    </CollapsibleCard>
  )
}
