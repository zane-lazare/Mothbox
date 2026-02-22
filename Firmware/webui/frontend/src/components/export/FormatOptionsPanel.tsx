import { useEffect, useMemo, useRef } from 'react'
import { useForm, useWatch, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  exportOptionsSchema,
  getExportDefaults,
  FORMAT_VALUES,
  type ExportOptionsFormData,
} from '../../schemas/export-options'
import { GPS_PRECISION_OPTIONS, getGpsPrecision } from '../../utils/gpsPrecision'

type FormatValue = (typeof FORMAT_VALUES)[number]

interface FormatOptionsPanelProps {
  format: string | null
  options?: Record<string, unknown>
  onChange: (options: Record<string, unknown>) => void
  disabled?: boolean
}

/**
 * Inner component that owns the react-hook-form instance.
 * Separated from the outer guard to avoid violating React's Rules of Hooks
 * (the guard returns null before hooks would be called).
 */
function FormatOptionsPanelInner({
  format,
  options = {},
  onChange,
  disabled = false,
}: FormatOptionsPanelProps & { format: FormatValue }) {
  // Stable ref for onChange so it never triggers the sync useEffect
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  // Cache GPS precision from localStorage once at mount — avoids
  // reading localStorage on every render (getExportDefaults calls getGpsPrecision)
  const cachedGpsPrecision = useMemo(() => getGpsPrecision(), [])

  const defaults = {
    ...getExportDefaults(format),
    gps_precision: cachedGpsPrecision,
    ...options,
    format,
  } as ExportOptionsFormData

  const { register, control, reset } = useForm<ExportOptionsFormData>({
    resolver: zodResolver(exportOptionsSchema),
    defaultValues: defaults,
    mode: 'onChange',
  })

  // Watch all form values for syncing to parent
  const watched = useWatch({ control })

  // Sync watched values to parent, stripping the `format` key
  useEffect(() => {
    if (!watched || Object.keys(watched).length === 0) return

    const { format: _format, ...rest } = watched
    onChangeRef.current(rest as Record<string, unknown>)
  }, [watched])

  // Reset form when parent changes format (prevFormatRef prevents re-reset on same format)
  const prevFormatRef = useRef(format)
  useEffect(() => {
    if (format !== prevFormatRef.current) {
      prevFormatRef.current = format
      const newDefaults = {
        ...getExportDefaults(format),
        gps_precision: cachedGpsPrecision,
        format,
      } as ExportOptionsFormData
      reset(newDefaults)
    }
    // `cachedGpsPrecision` is stable (useMemo([], [])), `reset` is stable from useForm
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only reset when format changes
  }, [format])

  const watchedFormat = watched.format as FormatValue | undefined

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
        Format Options
      </h3>

      {/* GPS Precision - Common to all formats (Issue #288) */}
      <div className="mb-4 pb-4 border-b border-gray-200 dark:border-gray-700">
        <label
          htmlFor="gps-precision"
          className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-1"
        >
          GPS Precision
        </label>
        <Controller
          name="gps_precision"
          control={control}
          render={({ field }) => (
            <select
              id="gps-precision"
              name={field.name}
              ref={field.ref}
              value={String(field.value ?? defaults.gps_precision)}
              onChange={(e) => field.onChange(Number(e.target.value))}
              onBlur={field.onBlur}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                        focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                        bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                        disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {GPS_PRECISION_OPTIONS.map(({ value, label }) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          )}
        />
        <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
          Reduce precision for privacy when sharing location data
        </p>
      </div>

      {/* Darwin Core Options */}
      {watchedFormat === 'darwin_core' && (
        <div className="space-y-3">
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('validate')}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Validate output against Darwin Core schema
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Ensure exported data conforms to Darwin Core standards
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('include_warnings')}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include validation warnings
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add warnings as comments in the CSV file
              </p>
            </div>
          </label>
        </div>
      )}

      {/* iNaturalist Options */}
      {watchedFormat === 'inaturalist' && (
        <div className="space-y-3">
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('include_xmp_sidecars')}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include XMP sidecar files
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Generate .xmp files alongside photos with embedded metadata
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('include_manifest')}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include manifest.json
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add manifest file with export metadata and file list
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('include_csv_summary')}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include CSV summary
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add a summary CSV file with photo metadata
              </p>
            </div>
          </label>
        </div>
      )}

      {/* JSON Options */}
      {watchedFormat === 'json' && (
        <div className="space-y-3">
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('pretty_print')}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Pretty print JSON
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Format JSON with indentation for readability
              </p>
            </div>
          </label>

          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('include_raw_exif')}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include raw EXIF data
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add complete EXIF data from photo files
              </p>
            </div>
          </label>
        </div>
      )}

      {/* CSV Options */}
      {watchedFormat === 'csv' && (
        <div className="space-y-3">
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              {...register('include_bom')}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500
                        disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div>
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Include UTF-8 BOM
              </span>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Add byte order mark for Excel compatibility
              </p>
            </div>
          </label>

          <div>
            <label
              htmlFor="csv-delimiter"
              className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-1"
            >
              Delimiter
            </label>
            <select
              id="csv-delimiter"
              {...register('delimiter')}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                        focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                        bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                        disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value=",">Comma (,)</option>
              <option value={'\t'}>Tab</option>
              <option value=";">Semicolon (;)</option>
            </select>
            <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
              Choose delimiter for CSV columns
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * Format-specific options panel for the export workflow.
 *
 * Outer guard component: returns null when no format is selected,
 * otherwise renders FormatOptionsPanelInner which owns the form.
 */
function FormatOptionsPanel({
  format,
  options = {},
  onChange,
  disabled = false,
}: FormatOptionsPanelProps) {
  // Guard: don't render anything if no format selected
  if (!format || !FORMAT_VALUES.includes(format as FormatValue)) {
    return null
  }

  return (
    <FormatOptionsPanelInner
      format={format as FormatValue}
      options={options}
      onChange={onChange}
      disabled={disabled}
    />
  )
}

export default FormatOptionsPanel
