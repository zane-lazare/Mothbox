import { LockClosedIcon } from '@heroicons/react/24/outline'
import type { ExportPreset } from '../../types/api'

export interface PresetDropdownProps {
  value?: string
  onChange: (preset: string | null) => void
  presets?: ExportPreset[]
  onSavePreset: () => void
  disabled?: boolean
}

export default function PresetDropdown({
  value,
  onChange,
  presets = [],
  onSavePreset,
  disabled = false
}: PresetDropdownProps) {
  // Group presets by category
  const builtInPresets = presets.filter((p) => p.is_builtin)
  const userPresets = presets.filter((p) => !p.is_builtin)

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedValue = e.target.value

    if (selectedValue === '__save_new__') {
      onSavePreset()
      // Reset to current value to avoid showing "__save_new__" in dropdown
      e.target.value = value || ''
    } else if (selectedValue === '') {
      onChange(null)
    } else {
      onChange(selectedValue)
    }
  }

  return (
    <div className="space-y-2">
      <label
        htmlFor="preset-select"
        className="block text-sm font-medium text-gray-700 dark:text-gray-300"
      >
        Preset
      </label>
      <select
        id="preset-select"
        name="preset"
        value={value || ''}
        onChange={handleChange}
        disabled={disabled}
        aria-label="Export preset"
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                   focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                   bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                   disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <option value="">No preset</option>

        {builtInPresets.length > 0 && (
          <optgroup label="Built-in Presets" aria-label="Built-in presets">
            {builtInPresets.map((preset) => (
              <option key={preset.name} value={preset.name}>
                🔒 {preset.description || preset.name}
              </option>
            ))}
          </optgroup>
        )}

        {userPresets.length > 0 && (
          <optgroup label="User Presets" aria-label="User presets">
            {userPresets.map((preset) => (
              <option key={preset.name} value={preset.name}>
                {preset.description || preset.name}
              </option>
            ))}
          </optgroup>
        )}

        <option value="__save_new__">💾 Save current settings as preset...</option>
      </select>

      {value && (
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          {builtInPresets.some((p) => p.name === value) && (
            <>
              <LockClosedIcon className="h-4 w-4" data-icon="lock" />
              <span>Built-in preset (read-only)</span>
            </>
          )}
        </div>
      )}
    </div>
  )
}
