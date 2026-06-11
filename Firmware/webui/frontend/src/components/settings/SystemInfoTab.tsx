import type { SystemInfo, CollapsedCardsState } from '../../types/settings'
import SettingCard from './SettingCard'
import GPSSettings from '../GPSSettings'

interface SystemInfoTabProps {
  systemInfo: SystemInfo | undefined
  collapsedCards: CollapsedCardsState
  toggleCard: (id: string) => void
}

export default function SystemInfoTab({
  systemInfo,
  collapsedCards,
  toggleCard,
}: SystemInfoTabProps) {
  return (
    <div className="settings-grid-2col">
      {/* Installation Information Card */}
      <SettingCard
        id="systemInstallation"
        title="📋 Installation Information"
        isCollapsed={collapsedCards.systemInstallation}
        onToggle={toggleCard}
        className="settings-card-lg"
      >
        <div className="space-y-2">
          <div>
            <p className="text-sm text-gray-500">Installation Type</p>
            <p className="font-medium capitalize">{systemInfo?.installation_type || 'Loading...'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Firmware Version</p>
            <p className="font-medium">{systemInfo?.firmware_version || 'Loading...'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Mothbox Home</p>
            <p className="font-mono text-xs break-all">{systemInfo?.mothbox_home || 'Loading...'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Config Directory</p>
            <p className="font-mono text-xs break-all">{systemInfo?.config_dir || 'Loading...'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Firmware Directory</p>
            <p className="font-mono text-xs break-all">{systemInfo?.firmware_dir || 'Loading...'}</p>
          </div>
        </div>
      </SettingCard>

      {/* GPIO Pin Configuration Card */}
      <SettingCard
        id="systemGPIO"
        title="🔌 GPIO Pin Configuration"
        isCollapsed={collapsedCards.systemGPIO}
        onToggle={toggleCard}
        className="settings-card-lg"
      >
        <p className="text-xs text-gray-600 mb-2">
          Source: <span className="font-medium">{systemInfo?.gpio_source || 'Loading...'}</span>
        </p>
        <div className="space-y-2">
          <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
            <span className="text-sm text-gray-600">Relay Ch1 (Attract Light)</span>
            <span className="font-mono text-lg font-semibold">{systemInfo?.gpio_pins?.Relay_Ch1 || '?'}</span>
          </div>
          <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
            <span className="text-sm text-gray-600">Relay Ch2 (Flash)</span>
            <span className="font-mono text-lg font-semibold">{systemInfo?.gpio_pins?.Relay_Ch2 || '?'}</span>
          </div>
          <div className="flex justify-between items-center p-2 bg-gray-50 rounded">
            <span className="text-sm text-gray-600">Relay Ch3 (UV Light)</span>
            <span className="font-mono text-lg font-semibold">{systemInfo?.gpio_pins?.Relay_Ch3 || '?'}</span>
          </div>
        </div>
        {systemInfo?.gpio_source === 'defaults' && (
          <div className="mt-2 settings-info-box bg-yellow-50 border-yellow-200">
            <p className="text-xs text-yellow-800">
              ⚠️ Using default GPIO pins. To customize, add Relay_Ch1, Relay_Ch2, and Relay_Ch3 to controls.txt
            </p>
          </div>
        )}
      </SettingCard>

      {/* GPS Configuration Card */}
      <GPSSettings />
    </div>
  )
}
