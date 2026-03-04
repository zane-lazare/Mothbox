import { useCallback, useEffect, useState } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import type { Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { ChevronDownIcon, ChevronRightIcon, PlusIcon, XMarkIcon, SparklesIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import CoordinateInput from './CoordinateInput'
// @ts-expect-error — ConfirmDialog.jsx has no type declarations (pre-migration)
import ConfirmDialog from '../common/ConfirmDialog'
// @ts-expect-error — usePhotoAggregation.js has no type declarations (pre-migration)
import { usePhotoAggregation } from '../../hooks/usePhotoAggregation'
import {
  deploymentSchema,
  DEPLOYMENT_DEFAULTS,
  type DeploymentFormData,
} from '../../schemas/deployment'

/**
 * Backend deployment shape — derives scalar fields from the Zod schema,
 * but keeps environmental/custom as Record<string, string> (backend format)
 * instead of the useFieldArray { key, value }[] form format.
 */
type DeploymentPropData = Partial<
  Omit<DeploymentFormData, 'environmental' | 'custom'>
> & {
  environmental?: Record<string, string>
  custom?: Record<string, string>
}

interface DeploymentEditorProps {
  deployment?: DeploymentPropData | null
  directory: string
  filter?: Record<string, unknown>
  onSave: (data: Record<string, unknown>) => void
  onCancel: () => void
  isLoading?: boolean
  error?: string | null
}

/**
 * DeploymentEditor Component
 *
 * Full deployment metadata form with collapsible sections.
 * Migrated to react-hook-form + Zod for validation.
 *
 * @component
 * @example
 * <DeploymentEditor
 *   deployment={existingDeployment}
 *   directory="/photos/deployment1"
 *   onSave={(data) => console.log('Save', data)}
 *   onCancel={() => console.log('Cancel')}
 * />
 */
export default function DeploymentEditor({
  deployment,
  directory,
  filter,
  onSave,
  onCancel,
  isLoading = false,
  error = null,
}: DeploymentEditorProps) {
  // zodResolver's Zod 4 overload expects $ZodType<Output, FieldValues> but
  // Zod 4's public ZodType uses `unknown` for its input parameter (z.coerce).
  // The cast through `unknown` is safe because the schema validates the same
  // shape at runtime — DeploymentFormData is z.infer<typeof deploymentSchema>.
  // Verified working with @hookform/resolvers ^5.2.2.
  // TODO(#485): Remove cast when @hookform/resolvers aligns with Zod 4.
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    control,
    formState: { errors, isDirty, submitCount, isValid },
  } = useForm<DeploymentFormData>({
    resolver: zodResolver(
      deploymentSchema as unknown as Parameters<typeof zodResolver>[0],
    ) as unknown as Resolver<DeploymentFormData>,
    defaultValues: DEPLOYMENT_DEFAULTS,
    mode: 'onBlur',
  })

  const {
    fields: envFields,
    append: appendEnv,
    remove: removeEnv,
  } = useFieldArray({ control, name: 'environmental' })

  const {
    fields: customFields,
    append: appendCustom,
    remove: removeCustom,
  } = useFieldArray({ control, name: 'custom' })

  // Collapsible section state (not form state)
  const [sectionsExpanded, setSectionsExpanded] = useState({
    environmental: false,
    metadata: false,
    custom: false,
  })

  // Confirm dialog state for unsaved changes
  const [showCancelConfirm, setShowCancelConfirm] = useState(false)

  // Photo aggregation for auto-fill
  const aggregateMutation = usePhotoAggregation()

  // Watch fields for character counters and display
  const deploymentName = watch('deployment_name')
  const locationName = watch('location_name')

  // Watch lat/lng for CoordinateInput sync
  const [latitude, longitude] = watch(['latitude', 'longitude'])

  // Initialize form with existing deployment data
  useEffect(() => {
    if (deployment) {
      const envArray = Object.entries(deployment.environmental || {}).map(
        ([key, value]) => ({ key, value }),
      )
      const customArray = Object.entries(deployment.custom || {}).map(
        ([key, value]) => ({ key, value }),
      )
      reset({
        deployment_name: deployment.deployment_name || '',
        location_name: deployment.location_name || '',
        latitude: deployment.latitude ?? null,
        longitude: deployment.longitude ?? null,
        altitude: deployment.altitude ?? null,
        start_date: deployment.start_date || '',
        end_date: deployment.end_date || '',
        environmental: envArray,
        custom: customArray,
        mothbox_id: deployment.mothbox_id || '',
        firmware_version: deployment.firmware_version || '',
      })
    }
  }, [deployment, reset])

  const handleCancel = useCallback(() => {
    if (isDirty) {
      setShowCancelConfirm(true)
      return
    }
    onCancel()
  }, [isDirty, onCancel])

  // Handle Escape key to close editor
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !showCancelConfirm) {
        handleCancel()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [showCancelConfirm, handleCancel])

  /**
   * Handle successful aggregation response.
   * Extracted for testability.
   */
  const handleAggregationSuccess = (data: Record<string, unknown>) => {
    // Always fill dates
    if (data.date_start) {
      setValue('start_date', data.date_start as string, { shouldDirty: true })
    }
    if (data.date_end) {
      setValue('end_date', data.date_end as string, { shouldDirty: true })
    }

    // Fill GPS if consistent
    if (data.gps_consistent) {
      if (data.latitude !== null && data.longitude !== null) {
        setValue('latitude', data.latitude as number, { shouldDirty: true })
        setValue('longitude', data.longitude as number, { shouldDirty: true })
      }
      if (data.altitude !== null) {
        setValue('altitude', data.altitude as number, { shouldDirty: true })
      }
      toast.success(`Auto-filled from ${data.photo_count} photos`)
    } else {
      // GPS inconsistent - show warning but still fill dates
      toast.error(
        (data.gps_error as string) || 'GPS coordinates are inconsistent',
        { duration: 5000 },
      )
      if (data.date_start || data.date_end) {
        toast.success(
          `Filled dates from ${data.photo_count} photos (GPS skipped)`,
          { duration: 3000 },
        )
      }
    }
  }

  const handleAutoFill = () => {
    // Use filter prop or empty object
    const aggregationFilter = filter || {}

    aggregateMutation.mutate(
      { filter: aggregationFilter, tolerance_m: 50.0 },
      {
        onSuccess: handleAggregationSuccess,
        onError: (error: { response?: { data?: { error?: string } } }) => {
          const message =
            error.response?.data?.error || 'Failed to aggregate photo data'
          toast.error(message)
        },
      },
    )
  }

  // Submit handler — convert arrays to objects, call onSave
  const onValid = (values: DeploymentFormData) => {
    if (!isDirty) {
      toast('No changes to save', { icon: 'ℹ️' })
      return
    }
    const environmentalObj: Record<string, string> = {}
    values.environmental.forEach(({ key, value }) => {
      if (key.trim()) {
        environmentalObj[key.trim()] = value
      }
    })

    const customObj: Record<string, string> = {}
    values.custom.forEach(({ key, value }) => {
      if (key.trim()) {
        customObj[key.trim()] = value
      }
    })

    onSave({
      deployment_name: values.deployment_name.trim(),
      location_name: (values.location_name || '').trim(),
      latitude: values.latitude,
      longitude: values.longitude,
      altitude: values.altitude,
      start_date: values.start_date || null,
      end_date: values.end_date || null,
      environmental: environmentalObj,
      mothbox_id: (values.mothbox_id || '').trim(),
      firmware_version: (values.firmware_version || '').trim(),
      custom: customObj,
    })
  }

  const handleConfirmCancel = () => {
    setShowCancelConfirm(false)
    onCancel()
  }

  const toggleSection = (section: keyof typeof sectionsExpanded) => {
    setSectionsExpanded({
      ...sectionsExpanded,
      [section]: !sectionsExpanded[section],
    })
  }

  const addEnvironmentalField = () => {
    appendEnv({ key: '', value: '' })
    setSectionsExpanded((prev) => ({ ...prev, environmental: true }))
  }

  const addCustomField = () => {
    if (customFields.length >= 50) return
    appendCustom({ key: '', value: '' })
    setSectionsExpanded((prev) => ({ ...prev, custom: true }))
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {deployment ? 'Edit Deployment Metadata' : 'Create Deployment Metadata'}
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Directory: {directory}
        </p>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Required Fields */}
      <div className="space-y-4">
        <div>
          <label htmlFor="deployment-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Deployment Name <span className="text-red-500">*</span>
          </label>
          <input
            id="deployment-name"
            type="text"
            {...register('deployment_name')}
            disabled={isLoading}
            maxLength={200}
            placeholder="e.g., Oak Ridge Forest Survey 2024"
            autoFocus
            className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       dark:bg-gray-700 dark:text-gray-100
                       ${errors.deployment_name ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'}
                       disabled:opacity-50 disabled:cursor-not-allowed`}
          />
          {errors.deployment_name && (
            <p className="text-xs text-red-600 dark:text-red-400 mt-1">{errors.deployment_name.message}</p>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {(deploymentName || '').length}/200 characters
          </p>
        </div>
      </div>

      {/* Location Section */}
      <div className="space-y-4 border-t pt-4 dark:border-gray-700">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Location</h4>

        <div>
          <label htmlFor="location-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Location Name
          </label>
          <input
            id="location-name"
            type="text"
            {...register('location_name')}
            disabled={isLoading}
            maxLength={500}
            placeholder="e.g., Oak Ridge, TN, USA"
            className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       dark:bg-gray-700 dark:text-gray-100
                       ${errors.location_name ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'}
                       disabled:opacity-50 disabled:cursor-not-allowed`}
          />
          {errors.location_name && (
            <p className="text-xs text-red-600 dark:text-red-400 mt-1">{errors.location_name.message}</p>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {(locationName || '').length}/500 characters
          </p>
        </div>

        <CoordinateInput
          latitude={latitude}
          longitude={longitude}
          onChange={({ latitude: lat, longitude: lon }: { latitude: number | null; longitude: number | null }) => {
            setValue('latitude', lat, { shouldDirty: true })
            setValue('longitude', lon, { shouldDirty: true })
          }}
          disabled={isLoading}
        />

        <div>
          <label htmlFor="altitude" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Altitude (meters)
          </label>
          <input
            id="altitude"
            type="number"
            step="0.1"
            {...register('altitude', {
              setValueAs: (v: string | number | null) =>
                (v === '' || v === null || v === undefined) ? null : Number(v),
            })}
            disabled={isLoading}
            placeholder="e.g., 350.5"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     dark:bg-gray-700 dark:text-gray-100
                     disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>
      </div>

      {/* Date Range Section */}
      <div className="space-y-4 border-t pt-4 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Date Range</h4>

          {/* Auto-fill button */}
          {filter && (
            <button
              type="button"
              onClick={handleAutoFill}
              disabled={isLoading || aggregateMutation.isPending}
              className="flex items-center gap-1 px-3 py-1 text-xs font-medium text-blue-600 dark:text-blue-400
                       border border-blue-300 dark:border-blue-700 rounded-md
                       hover:bg-blue-50 dark:hover:bg-blue-900/20
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
              title="Auto-fill dates and GPS from selected photos"
            >
              <SparklesIcon className="h-4 w-4" />
              {aggregateMutation.isPending ? 'Loading...' : 'Auto-fill from Photos'}
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="start-date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Start Date
            </label>
            <input
              id="start-date"
              type="date"
              {...register('start_date')}
              disabled={isLoading}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       dark:bg-gray-700 dark:text-gray-100
                       disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          <div>
            <label htmlFor="end-date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              End Date
            </label>
            <input
              id="end-date"
              type="date"
              {...register('end_date')}
              disabled={isLoading}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                       focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       dark:bg-gray-700 dark:text-gray-100
                       disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
        </div>

        {errors.end_date && (
          <p className="text-xs text-red-600 dark:text-red-400">{errors.end_date.message}</p>
        )}
      </div>

      {/* Environmental Conditions (Collapsible) */}
      <div className="border-t pt-4 dark:border-gray-700">
        <button
          type="button"
          onClick={() => toggleSection('environmental')}
          className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100 hover:text-blue-600"
        >
          {sectionsExpanded.environmental ? (
            <ChevronDownIcon className="h-4 w-4" />
          ) : (
            <ChevronRightIcon className="h-4 w-4" />
          )}
          Environmental Conditions
          {envFields.length > 0 && (
            <span className="text-xs text-gray-500">({envFields.length})</span>
          )}
        </button>

        {sectionsExpanded.environmental && (
          <div className="mt-4 space-y-3">
            {envFields.map((field, index) => (
              <div key={field.id} className="flex gap-2">
                <input
                  type="text"
                  {...register(`environmental.${index}.key`)}
                  disabled={isLoading}
                  placeholder="Key (e.g., temperature)"
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           dark:bg-gray-700 dark:text-gray-100
                           disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <input
                  type="text"
                  {...register(`environmental.${index}.value`)}
                  disabled={isLoading}
                  placeholder="Value (e.g., 18-28°C)"
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           dark:bg-gray-700 dark:text-gray-100
                           disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button
                  type="button"
                  onClick={() => removeEnv(index)}
                  disabled={isLoading}
                  aria-label="Remove"
                  className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md
                           disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
            ))}

            <button
              type="button"
              onClick={addEnvironmentalField}
              disabled={isLoading}
              aria-label="Add environmental field"
              className="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline
                       disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PlusIcon className="h-4 w-4" />
              Add Field
            </button>
          </div>
        )}
      </div>

      {/* Metadata Section (Collapsible) */}
      <div className="border-t pt-4 dark:border-gray-700">
        <button
          type="button"
          onClick={() => toggleSection('metadata')}
          className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100 hover:text-blue-600"
        >
          {sectionsExpanded.metadata ? (
            <ChevronDownIcon className="h-4 w-4" />
          ) : (
            <ChevronRightIcon className="h-4 w-4" />
          )}
          Metadata
        </button>

        {sectionsExpanded.metadata && (
          <div className="mt-4 space-y-3">
            <div>
              <label htmlFor="mothbox-id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Mothbox ID
              </label>
              <input
                id="mothbox-id"
                type="text"
                {...register('mothbox_id')}
                disabled={isLoading}
                placeholder="e.g., mothbox-001"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         dark:bg-gray-700 dark:text-gray-100
                         disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>

            <div>
              <label htmlFor="firmware-version" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Firmware Version
              </label>
              <input
                id="firmware-version"
                type="text"
                {...register('firmware_version')}
                disabled={isLoading}
                placeholder="e.g., 5.2.1"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         dark:bg-gray-700 dark:text-gray-100
                         disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          </div>
        )}
      </div>

      {/* Custom Fields (Collapsible) */}
      <div className="border-t pt-4 dark:border-gray-700">
        <button
          type="button"
          onClick={() => toggleSection('custom')}
          className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100 hover:text-blue-600"
        >
          {sectionsExpanded.custom ? (
            <ChevronDownIcon className="h-4 w-4" />
          ) : (
            <ChevronRightIcon className="h-4 w-4" />
          )}
          Custom Fields
          {customFields.length > 0 && (
            <span className="text-xs text-gray-500">({customFields.length}/50)</span>
          )}
        </button>

        {sectionsExpanded.custom && (
          <div className="mt-4 space-y-3">
            {customFields.map((field, index) => (
              <div key={field.id} className="flex gap-2">
                <input
                  type="text"
                  {...register(`custom.${index}.key`)}
                  disabled={isLoading}
                  placeholder="Key"
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           dark:bg-gray-700 dark:text-gray-100
                           disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <input
                  type="text"
                  {...register(`custom.${index}.value`)}
                  disabled={isLoading}
                  placeholder="Value"
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           dark:bg-gray-700 dark:text-gray-100
                           disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button
                  type="button"
                  onClick={() => removeCustom(index)}
                  disabled={isLoading}
                  aria-label="Remove"
                  className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md
                           disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
            ))}

            {customFields.length >= 50 ? (
              <span title="Maximum of 50 custom fields allowed">
                <button
                  type="button"
                  disabled
                  aria-label="Add custom field (limit reached)"
                  className="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400
                           opacity-50 cursor-not-allowed pointer-events-none"
                >
                  <PlusIcon className="h-4 w-4" />
                  Add Field (Max 50)
                </button>
              </span>
            ) : (
              <button
                type="button"
                onClick={addCustomField}
                disabled={isLoading}
                aria-label="Add custom field"
                className="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline
                         disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <PlusIcon className="h-4 w-4" />
                Add Field
              </button>
            )}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 border-t pt-4 dark:border-gray-700">
        <button
          type="button"
          onClick={handleCancel}
          disabled={isLoading}
          className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                   hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100
                   disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSubmit(onValid)}
          disabled={isLoading || (submitCount > 0 && !isValid)}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md
                   hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Saving...' : 'Save'}
        </button>
      </div>

      {/* Unsaved changes confirmation dialog */}
      <ConfirmDialog
        isOpen={showCancelConfirm}
        onClose={() => setShowCancelConfirm(false)}
        onConfirm={handleConfirmCancel}
        title="Discard unsaved changes?"
        message="You have unsaved changes. Are you sure you want to discard them?"
        confirmLabel="Discard"
        cancelLabel="Keep Editing"
        variant="warning"
      />
    </div>
  )
}
