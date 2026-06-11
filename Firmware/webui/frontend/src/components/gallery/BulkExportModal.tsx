import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { XMarkIcon } from '@heroicons/react/24/outline'
import {
  CircleStackIcon,
  DocumentTextIcon,
  TableCellsIcon,
  BeakerIcon
} from '@heroicons/react/20/solid'
import { Z_INDEX, EXPORT_FORMATS } from '@/constants/config'

type FormatId = 'darwin_core' | 'inaturalist' | 'json' | 'csv'

/**
 * Icon mapping for export formats (UI-specific, not in config)
 */
const FORMAT_ICONS: Record<FormatId, React.ComponentType<{ className?: string }>> = {
  darwin_core: BeakerIcon,
  inaturalist: CircleStackIcon,
  json: DocumentTextIcon,
  csv: TableCellsIcon,
}

export interface BulkExportModalProps {
  /** Whether the modal is open */
  isOpen: boolean
  /** Close handler */
  onClose: () => void
  /** Export handler - receives format id (darwin_core, inaturalist, json, csv) */
  onExport: (format: FormatId) => void
  /** Number of selected photos */
  selectedCount: number
  /** Loading state */
  isLoading?: boolean
  /** Error message */
  error?: string | null
}

/**
 * BulkExportModal Component
 *
 * Modal for selecting export format for bulk photo export.
 * Displays format options as radio button cards with icons and descriptions.
 */
export default function BulkExportModal({
  isOpen,
  onClose,
  onExport,
  selectedCount,
  isLoading = false,
  error = null
}: BulkExportModalProps) {
  const [selectedFormat, setSelectedFormat] = useState<FormatId | null>(null)

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setSelectedFormat(null)
    }
  }, [isOpen])

  // Handle Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (!isOpen) return
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const handleExport = () => {
    if (selectedFormat && !isLoading) {
      onExport(selectedFormat)
    }
  }

  const isExportDisabled = !selectedFormat || isLoading

  const modal = (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center`}>
      {/* Backdrop with click-to-close */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal content */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="bulk-export-title"
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl
                   w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 id="bulk-export-title" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Export {selectedCount} photo{selectedCount !== 1 ? 's' : ''}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Format Selection */}
        <div
          role="radiogroup"
          aria-label="Export format"
          className="space-y-2"
        >
          {EXPORT_FORMATS.map((format) => {
            const Icon = FORMAT_ICONS[format.id as FormatId]
            const isSelected = selectedFormat === format.id
            return (
              <label
                key={format.id}
                className={`
                  flex items-start gap-3 p-3 rounded-lg cursor-pointer
                  border-2 transition-colors
                  ${isSelected
                    ? 'border-blue-500 ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'}
                `}
              >
                <input
                  type="radio"
                  name="export-format"
                  value={format.id}
                  checked={isSelected}
                  onChange={() => setSelectedFormat(format.id as FormatId)}
                  aria-label={format.name}
                  className="sr-only"
                />
                <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                  isSelected
                    ? 'text-blue-600 dark:text-blue-400'
                    : 'text-gray-400 dark:text-gray-500'
                }`} />
                <div className="flex-1 min-w-0">
                  <div className={`text-sm font-medium ${
                    isSelected
                      ? 'text-blue-900 dark:text-blue-100'
                      : 'text-gray-900 dark:text-gray-100'
                  }`}>
                    {format.name}
                  </div>
                  <div className={`text-xs ${
                    isSelected
                      ? 'text-blue-700 dark:text-blue-300'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}>
                    {format.description}
                  </div>
                </div>
                {/* Visual check indicator */}
                <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-0.5 ${
                  isSelected
                    ? 'border-blue-500 bg-blue-500'
                    : 'border-gray-300 dark:border-gray-500'
                }`}>
                  {isSelected && (
                    <div className="w-2 h-2 rounded-full bg-white" />
                  )}
                </div>
              </label>
            )
          })}
        </div>

        {/* Error message */}
        {error && (
          <p role="alert" className="text-red-600 dark:text-red-400 text-sm mt-4">
            {error}
          </p>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md
                       hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100
                       disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={isExportDisabled}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md
                       hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Exporting...' : 'Export'}
          </button>
        </div>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}
