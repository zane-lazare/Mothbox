import { useState, useMemo } from 'react'
import { useFilterContext } from '../../contexts/FilterContext'
import RangeSlider, { type RangeValue } from './RangeSlider'

// Camera setting value ranges
const ISO_VALUES = [100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600]
const APERTURE_VALUES = [1.4, 2, 2.8, 4, 5.6, 8, 11, 16, 22]
const SHUTTER_SPEEDS = [
  '1/8000', '1/4000', '1/2000', '1/1000', '1/500', '1/250', '1/125', '1/60',
  '1/30', '1/15', '1/8', '1/4', '1/2', '1', '2', '4', '8', '15', '30'
]

/**
 * CameraSettingsFilter Component
 *
 * Provides EXIF-based camera settings filters with range sliders for:
 * - ISO (100 - 25600)
 * - Aperture (f/1.4 - f/22)
 * - Shutter Speed (1/8000s - 30s)
 *
 * Features:
 * - Collapsible sub-sections for each setting type
 * - Individual clear buttons for each setting
 * - Formatted value display (ISO: numbers, Aperture: f/N, Shutter: fraction/seconds)
 * - Integration with FilterContext
 * - Dark mode compatible
 * - Full keyboard accessibility
 *
 * NOTE: This is CLIENT-SIDE filtering (EXIF data is not in search index)
 *
 * @component
 * @example
 * <CameraSettingsFilter />
 */
export function CameraSettingsFilter() {
  const { cameraSettings, setCameraSettings } = useFilterContext()

  // Local state for sub-section expansion
  const [expandedSubSections, setExpandedSubSections] = useState<Record<string, boolean>>({
    iso: false,
    aperture: false,
    shutterSpeed: false,
  })

  // Toggle sub-section expansion
  const toggleSubSection = (section: string) => {
    setExpandedSubSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }))
  }

  // Format functions
  const formatISO = (index: number) => ISO_VALUES[index].toString()
  const formatAperture = (index: number) => `f/${APERTURE_VALUES[index]}`
  const formatShutterSpeed = (index: number) => `${SHUTTER_SPEEDS[index]}s`

  // Check if each section has values
  const hasISOValues = useMemo(() => {
    return cameraSettings.iso.min !== null || cameraSettings.iso.max !== null
  }, [cameraSettings.iso])

  const hasApertureValues = useMemo(() => {
    return cameraSettings.aperture.min !== null || cameraSettings.aperture.max !== null
  }, [cameraSettings.aperture])

  const hasShutterSpeedValues = useMemo(() => {
    return cameraSettings.shutterSpeed.min !== null || cameraSettings.shutterSpeed.max !== null
  }, [cameraSettings.shutterSpeed])

  // Handlers
  const handleISOChange = (value: RangeValue) => {
    setCameraSettings({
      iso: {
        min: value.min,
        max: value.max,
      },
    })
  }

  const handleApertureChange = (value: RangeValue) => {
    setCameraSettings({
      aperture: {
        min: value.min,
        max: value.max,
      },
    })
  }

  const handleShutterSpeedChange = (value: RangeValue) => {
    setCameraSettings({
      shutterSpeed: {
        min: value.min,
        max: value.max,
      },
    })
  }

  const clearISO = () => {
    setCameraSettings({
      iso: { min: null, max: null },
    })
  }

  const clearAperture = () => {
    setCameraSettings({
      aperture: { min: null, max: null },
    })
  }

  const clearShutterSpeed = () => {
    setCameraSettings({
      shutterSpeed: { min: null, max: null },
    })
  }

  return (
    <div className="p-4 space-y-4">
      {/* ISO Section */}
      <div className="space-y-2">
        <button
          onClick={() => toggleSubSection('iso')}
          className="w-full flex items-center justify-between text-sm font-medium
                     text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                     dark:focus:ring-offset-gray-800 rounded px-2 py-1"
          aria-expanded={expandedSubSections.iso}
          aria-controls="iso-settings"
        >
          <span className="flex items-center gap-2">
            ISO
            {hasISOValues && (
              <span
                className="w-2 h-2 bg-blue-600 rounded-full"
                aria-label="Active ISO filter"
              />
            )}
          </span>
          <span className={`transform transition-transform ${expandedSubSections.iso ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </button>

        {expandedSubSections.iso && (
          <div id="iso-settings" className="pl-2 space-y-3">
            <RangeSlider
              min={0}
              max={ISO_VALUES.length - 1}
              value={{
                min: cameraSettings.iso.min ?? 0,
                max: cameraSettings.iso.max ?? ISO_VALUES.length - 1,
              }}
              onChange={handleISOChange}
              formatValue={formatISO}
              showInputs={false}
              label="ISO"
            />
            {hasISOValues && (
              <button
                onClick={clearISO}
                className="w-full px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300
                           bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600
                           border border-gray-300 dark:border-gray-600 rounded
                           focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                           dark:focus:ring-offset-gray-800
                           transition-colors duration-150"
                type="button"
                aria-label="Clear ISO filter"
              >
                Clear
              </button>
            )}
          </div>
        )}
      </div>

      {/* Aperture Section */}
      <div className="space-y-2">
        <button
          onClick={() => toggleSubSection('aperture')}
          className="w-full flex items-center justify-between text-sm font-medium
                     text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                     dark:focus:ring-offset-gray-800 rounded px-2 py-1"
          aria-expanded={expandedSubSections.aperture}
          aria-controls="aperture-settings"
        >
          <span className="flex items-center gap-2">
            Aperture
            {hasApertureValues && (
              <span
                className="w-2 h-2 bg-blue-600 rounded-full"
                aria-label="Active aperture filter"
              />
            )}
          </span>
          <span className={`transform transition-transform ${expandedSubSections.aperture ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </button>

        {expandedSubSections.aperture && (
          <div id="aperture-settings" className="pl-2 space-y-3">
            <RangeSlider
              min={0}
              max={APERTURE_VALUES.length - 1}
              value={{
                min: cameraSettings.aperture.min ?? 0,
                max: cameraSettings.aperture.max ?? APERTURE_VALUES.length - 1,
              }}
              onChange={handleApertureChange}
              formatValue={formatAperture}
              showInputs={false}
              label="Aperture"
            />
            {hasApertureValues && (
              <button
                onClick={clearAperture}
                className="w-full px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300
                           bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600
                           border border-gray-300 dark:border-gray-600 rounded
                           focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                           dark:focus:ring-offset-gray-800
                           transition-colors duration-150"
                type="button"
                aria-label="Clear aperture filter"
              >
                Clear
              </button>
            )}
          </div>
        )}
      </div>

      {/* Shutter Speed Section */}
      <div className="space-y-2">
        <button
          onClick={() => toggleSubSection('shutterSpeed')}
          className="w-full flex items-center justify-between text-sm font-medium
                     text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                     dark:focus:ring-offset-gray-800 rounded px-2 py-1"
          aria-expanded={expandedSubSections.shutterSpeed}
          aria-controls="shutter-speed-settings"
        >
          <span className="flex items-center gap-2">
            Shutter Speed
            {hasShutterSpeedValues && (
              <span
                className="w-2 h-2 bg-blue-600 rounded-full"
                aria-label="Active shutter speed filter"
              />
            )}
          </span>
          <span className={`transform transition-transform ${expandedSubSections.shutterSpeed ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </button>

        {expandedSubSections.shutterSpeed && (
          <div id="shutter-speed-settings" className="pl-2 space-y-3">
            <RangeSlider
              min={0}
              max={SHUTTER_SPEEDS.length - 1}
              value={{
                min: cameraSettings.shutterSpeed.min ?? 0,
                max: cameraSettings.shutterSpeed.max ?? SHUTTER_SPEEDS.length - 1,
              }}
              onChange={handleShutterSpeedChange}
              formatValue={formatShutterSpeed}
              showInputs={false}
              label="Shutter Speed"
            />
            {hasShutterSpeedValues && (
              <button
                onClick={clearShutterSpeed}
                className="w-full px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300
                           bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600
                           border border-gray-300 dark:border-gray-600 rounded
                           focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                           dark:focus:ring-offset-gray-800
                           transition-colors duration-150"
                type="button"
                aria-label="Clear shutter speed filter"
              >
                Clear
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default CameraSettingsFilter
