import type { DiagnosticInfo, CollapsedCardsState } from '../../types/settings'
import SettingCard from './SettingCard'

interface DiagnosticTabProps {
  diagnosticInfo: DiagnosticInfo | undefined
  collapsedCards: CollapsedCardsState
  toggleCard: (id: string) => void
}

export default function DiagnosticTab({
  diagnosticInfo,
  collapsedCards,
  toggleCard,
}: DiagnosticTabProps) {
  return (
    <div className="space-y-2">
      <SettingCard
        id="diagnosticPaths"
        title="📁 File Paths"
        isCollapsed={collapsedCards.diagnosticPaths}
        onToggle={toggleCard}
        className="settings-card-lg"
      >
        <div className="space-y-1 text-xs font-mono">
          {diagnosticInfo?.paths && Object.entries(diagnosticInfo.paths).map(([key, value]) => (
            <div key={key} className="flex items-start">
              <span className="text-gray-500 w-48">{key}:</span>
              <span className={typeof value === 'boolean' ? (value ? 'text-green-600' : 'text-red-600') : ''}>
                {String(value)}
              </span>
            </div>
          ))}
        </div>
      </SettingCard>

      <SettingCard
        id="diagnosticControls"
        title="📄 Controls File Content"
        isCollapsed={collapsedCards.diagnosticControls}
        onToggle={toggleCard}
        className="settings-card-lg"
      >
        <div className="space-y-1 text-xs">
          <p>Raw lines: {diagnosticInfo?.controls_content?.raw_lines || 0}</p>
          <p>Parsed keys: {diagnosticInfo?.controls_content?.parsed_keys?.length || 0}</p>
          <p>Has GPIO pins: {diagnosticInfo?.controls_content?.has_gpio_pins ? '✓ Yes' : '✗ No'}</p>
          <div className="mt-1">
            <p className="settings-label">Sample values:</p>
            <div className="settings-info-box bg-gray-50">
              {diagnosticInfo?.controls_content?.sample_values &&
                Object.entries(diagnosticInfo.controls_content.sample_values).map(([key, value]) => (
                  <div key={key} className="font-mono settings-help-text">{key}: {value}</div>
                ))
              }
            </div>
          </div>
        </div>
      </SettingCard>

      <SettingCard
        id="diagnosticHardware"
        title="🔧 Hardware Modules"
        isCollapsed={collapsedCards.diagnosticHardware}
        onToggle={toggleCard}
        className="settings-card-lg"
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {diagnosticInfo?.hardware_config && Object.entries(diagnosticInfo.hardware_config).map(([key, value]) => (
            key.endsWith('_enabled') && (
              <div key={key} className="settings-info-box border">
                <p className="settings-help-text text-gray-500">{key.replace('_enabled', '')}</p>
                <p className={`font-semibold text-xs ${value ? 'text-green-600' : 'text-gray-400'}`}>
                  {value ? 'Enabled' : 'Disabled'}
                </p>
              </div>
            )
          ))}
        </div>
      </SettingCard>
    </div>
  )
}
