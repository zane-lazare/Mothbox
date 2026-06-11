import { useState, useRef, useCallback, useEffect } from 'react'

export interface RangeValue {
  min: number
  max: number
}

export interface RangeSliderProps {
  min?: number
  max?: number
  value?: RangeValue
  onChange: (value: RangeValue) => void
  step?: number
  label?: string
  formatValue?: (val: number) => string
  showInputs?: boolean
  disabled?: boolean
}

/**
 * RangeSlider - Dual-handle range slider component
 *
 * Features:
 * - Dual handles for min/max selection
 * - Optional numeric input fields
 * - Keyboard navigation support
 * - Touch-friendly interaction
 * - Dark mode support
 * - Custom value formatting
 */
const RangeSlider = ({
  min = 0,
  max = 100,
  value = { min: 0, max: 100 },
  onChange,
  step = 1,
  label = 'Range',
  formatValue = (val) => val.toString(),
  showInputs = true,
  disabled = false,
}: RangeSliderProps) => {
  const [isDragging, setIsDragging] = useState<'min' | 'max' | null>(null)
  const [hoveredHandle, setHoveredHandle] = useState<'min' | 'max' | null>(null)
  const trackRef = useRef<HTMLDivElement>(null)

  // Local state for controlled inputs
  const [minInputValue, setMinInputValue] = useState(value.min.toString())
  const [maxInputValue, setMaxInputValue] = useState(value.max.toString())

  // Sync local input state when prop values change
  useEffect(() => {
    setMinInputValue(value.min.toString())
  }, [value.min])

  useEffect(() => {
    setMaxInputValue(value.max.toString())
  }, [value.max])

  // Clamp value to valid range
  const clamp = useCallback((val: number) => {
    return Math.max(min, Math.min(max, val))
  }, [min, max])

  // Round to nearest step
  const roundToStep = useCallback((val: number) => {
    return Math.round(val / step) * step
  }, [step])

  // Get percentage position on track
  const getPercentage = useCallback((val: number) => {
    return ((val - min) / (max - min)) * 100
  }, [min, max])

  // Convert mouse/touch position to value
  const getValueFromPosition = useCallback((clientX: number) => {
    if (!trackRef.current) return min

    const rect = trackRef.current.getBoundingClientRect()
    const percentage = (clientX - rect.left) / rect.width
    const rawValue = min + percentage * (max - min)
    return roundToStep(clamp(rawValue))
  }, [min, max, clamp, roundToStep])

  // Handle track click
  const handleTrackClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (disabled) return

    const clickValue = getValueFromPosition(e.clientX)
    const minDist = Math.abs(clickValue - value.min)
    const maxDist = Math.abs(clickValue - value.max)

    // Move the closest handle
    if (minDist < maxDist) {
      onChange({ min: clickValue, max: value.max })
    } else {
      onChange({ min: value.min, max: clickValue })
    }
  }, [disabled, getValueFromPosition, value, onChange])

  // Handle drag move
  const handleDragMove = useCallback((clientX: number) => {
    if (!isDragging || disabled) return

    const newValue = getValueFromPosition(clientX)

    if (isDragging === 'min') {
      // Min handle cannot exceed max handle (maintain step gap)
      onChange({ min: Math.min(newValue, value.max - step), max: value.max })
    } else if (isDragging === 'max') {
      // Max handle cannot go below min handle (maintain step gap)
      onChange({ min: value.min, max: Math.max(newValue, value.min + step) })
    }
  }, [isDragging, disabled, getValueFromPosition, value, onChange, step])

  // Mouse/touch event handlers
  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      e.preventDefault()
      handleDragMove(e.clientX)
    }

    const handleTouchMove = (e: TouchEvent) => {
      e.preventDefault()
      handleDragMove(e.touches[0].clientX)
    }

    const handleEnd = () => {
      setIsDragging(null)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleEnd)
    document.addEventListener('touchmove', handleTouchMove, { passive: false })
    document.addEventListener('touchend', handleEnd)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleEnd)
      document.removeEventListener('touchmove', handleTouchMove)
      document.removeEventListener('touchend', handleEnd)
    }
  }, [isDragging, handleDragMove])

  // Handle controlled input changes
  const handleMinInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setMinInputValue(e.target.value)
  }, [])

  const handleMaxInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setMaxInputValue(e.target.value)
  }, [])

  // Handle input field blur - validate and apply changes
  const handleMinInputBlur = useCallback(() => {
    if (disabled) return

    const newMin = parseFloat(minInputValue)
    if (isNaN(newMin)) {
      // Reset to current value if invalid
      setMinInputValue(value.min.toString())
      return
    }

    const clampedMin = clamp(roundToStep(newMin))
    onChange({ min: Math.min(clampedMin, value.max), max: value.max })
  }, [disabled, minInputValue, clamp, roundToStep, value.min, value.max, onChange])

  const handleMaxInputBlur = useCallback(() => {
    if (disabled) return

    const newMax = parseFloat(maxInputValue)
    if (isNaN(newMax)) {
      // Reset to current value if invalid
      setMaxInputValue(value.max.toString())
      return
    }

    const clampedMax = clamp(roundToStep(newMax))
    onChange({ min: value.min, max: Math.max(clampedMax, value.min) })
  }, [disabled, maxInputValue, clamp, roundToStep, value.min, value.max, onChange])

  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent, handle: 'min' | 'max') => {
    if (disabled) return

    let delta = 0
    if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
      delta = -step
    } else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
      delta = step
    } else if (e.key === 'Home') {
      delta = min - (handle === 'min' ? value.min : value.max)
    } else if (e.key === 'End') {
      delta = max - (handle === 'min' ? value.min : value.max)
    } else {
      return
    }

    e.preventDefault()

    if (handle === 'min') {
      const newMin = clamp(value.min + delta)
      onChange({ min: Math.min(newMin, value.max), max: value.max })
    } else {
      const newMax = clamp(value.max + delta)
      onChange({ min: value.min, max: Math.max(newMax, value.min) })
    }
  }, [disabled, step, min, max, value, clamp, onChange])

  const minPercentage = getPercentage(value.min)
  const maxPercentage = getPercentage(value.max)

  return (
    <div className="w-full" data-testid="range-slider">
      {/* Track */}
      <div className="relative mb-2">
        <div
          ref={trackRef}
          className={`
            relative h-2 bg-gray-200 dark:bg-gray-700 rounded-full
            ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}
          `}
          onClick={handleTrackClick}
          role="presentation"
        >
          {/* Selected range highlight */}
          <div
            className="absolute h-full bg-blue-500 dark:bg-blue-600 rounded-full transition-all"
            style={{
              left: `${minPercentage}%`,
              width: `${maxPercentage - minPercentage}%`,
            }}
          />

          {/* Min handle */}
          <div
            className={`
              absolute top-1/2 -translate-y-1/2 -translate-x-1/2
              w-5 h-5 bg-white dark:bg-gray-800 border-2 border-blue-500 dark:border-blue-600
              rounded-full shadow-md transition-transform
              ${disabled ? 'cursor-not-allowed' : 'cursor-grab active:cursor-grabbing'}
              ${isDragging === 'min' ? 'scale-110' : 'hover:scale-110'}
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
              dark:focus:ring-offset-gray-900
            `}
            style={{ left: `${minPercentage}%` }}
            onMouseDown={() => !disabled && setIsDragging('min')}
            onTouchStart={() => !disabled && setIsDragging('min')}
            onMouseEnter={() => setHoveredHandle('min')}
            onMouseLeave={() => setHoveredHandle(null)}
            onKeyDown={(e) => handleKeyDown(e, 'min')}
            tabIndex={disabled ? -1 : 0}
            role="slider"
            aria-label={`${label} minimum`}
            aria-valuemin={min}
            aria-valuemax={max}
            aria-valuenow={value.min}
            aria-disabled={disabled}
            data-testid="range-slider-min-handle"
          >
            {/* Tooltip on hover/drag */}
            {(hoveredHandle === 'min' || isDragging === 'min') && (
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded whitespace-nowrap">
                {formatValue(value.min)}
              </div>
            )}
          </div>

          {/* Max handle */}
          <div
            className={`
              absolute top-1/2 -translate-y-1/2 -translate-x-1/2
              w-5 h-5 bg-white dark:bg-gray-800 border-2 border-blue-500 dark:border-blue-600
              rounded-full shadow-md transition-transform
              ${disabled ? 'cursor-not-allowed' : 'cursor-grab active:cursor-grabbing'}
              ${isDragging === 'max' ? 'scale-110' : 'hover:scale-110'}
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
              dark:focus:ring-offset-gray-900
            `}
            style={{ left: `${maxPercentage}%` }}
            onMouseDown={() => !disabled && setIsDragging('max')}
            onTouchStart={() => !disabled && setIsDragging('max')}
            onMouseEnter={() => setHoveredHandle('max')}
            onMouseLeave={() => setHoveredHandle(null)}
            onKeyDown={(e) => handleKeyDown(e, 'max')}
            tabIndex={disabled ? -1 : 0}
            role="slider"
            aria-label={`${label} maximum`}
            aria-valuemin={min}
            aria-valuemax={max}
            aria-valuenow={value.max}
            aria-disabled={disabled}
            data-testid="range-slider-max-handle"
          >
            {/* Tooltip on hover/drag */}
            {(hoveredHandle === 'max' || isDragging === 'max') && (
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded whitespace-nowrap">
                {formatValue(value.max)}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Input fields */}
      {showInputs && (
        <div className="flex items-center gap-2 text-sm">
          <input
            type="number"
            value={minInputValue}
            onChange={handleMinInputChange}
            onBlur={handleMinInputBlur}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
            className={`
              w-20 px-2 py-1 border rounded
              bg-white dark:bg-gray-800
              border-gray-300 dark:border-gray-600
              text-gray-900 dark:text-gray-100
              focus:outline-none focus:ring-2 focus:ring-blue-500
              ${disabled ? 'cursor-not-allowed opacity-50' : ''}
            `}
            aria-label={`${label} minimum value`}
            data-testid="range-slider-min-input"
          />
          <span className="text-gray-500 dark:text-gray-400">to</span>
          <input
            type="number"
            value={maxInputValue}
            onChange={handleMaxInputChange}
            onBlur={handleMaxInputBlur}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
            className={`
              w-20 px-2 py-1 border rounded
              bg-white dark:bg-gray-800
              border-gray-300 dark:border-gray-600
              text-gray-900 dark:text-gray-100
              focus:outline-none focus:ring-2 focus:ring-blue-500
              ${disabled ? 'cursor-not-allowed opacity-50' : ''}
            `}
            aria-label={`${label} maximum value`}
            data-testid="range-slider-max-input"
          />
        </div>
      )}
    </div>
  )
}

export default RangeSlider
