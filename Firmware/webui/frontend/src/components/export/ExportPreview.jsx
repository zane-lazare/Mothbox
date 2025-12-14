import { useState } from 'react'
import PropTypes from 'prop-types'
import { DocumentDuplicateIcon, ArrowsPointingOutIcon } from '@heroicons/react/24/outline'
import useExportPreview from '../../hooks/useExportPreview'

/**
 * Format tabs configuration
 */
const PREVIEW_TABS = [
  { id: 'json', label: 'JSON' },
  { id: 'csv', label: 'CSV' },
  { id: 'darwin_core', label: 'Darwin Core' }
]

/**
 * Syntax highlight JSON string
 * Simple highlighting using regex and CSS classes
 */
function highlightJSON(jsonString) {
  return jsonString
    .replace(/("([^"\\]|\\.)*")\s*:/g, '<span class="json-key text-blue-600 dark:text-blue-400">$1</span>:')
    .replace(/:\s*("([^"\\]|\\.)*")/g, ': <span class="json-string text-green-600 dark:text-green-400">$1</span>')
    .replace(/:\s*(\d+\.?\d*)/g, ': <span class="json-number text-orange-600 dark:text-orange-400">$1</span>')
    .replace(/:\s*(true|false|null)/g, ': <span class="json-boolean text-purple-600 dark:text-purple-400">$1</span>')
}

/**
 * Render JSON preview with syntax highlighting
 */
function JSONPreview({ data }) {
  const jsonString = JSON.stringify(data, null, 2)
  const highlighted = highlightJSON(jsonString)

  return (
    <pre
      data-testid="json-preview"
      className="text-sm font-mono bg-gray-50 dark:bg-gray-900 p-4 rounded overflow-x-auto"
      dangerouslySetInnerHTML={{ __html: highlighted }}
    />
  )
}

JSONPreview.propTypes = {
  data: PropTypes.array.isRequired
}

/**
 * Render CSV preview as table
 */
function CSVPreview({ headers, data }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            {headers.map(header => (
              <th
                key={header}
                className="px-4 py-2 text-left font-medium text-gray-700 dark:text-gray-300"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
          {data.map((row, idx) => (
            <tr key={idx}>
              {headers.map(header => (
                <td
                  key={header}
                  className="px-4 py-2 text-gray-900 dark:text-gray-100"
                >
                  {Array.isArray(row[header])
                    ? row[header].join(', ')
                    : String(row[header] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

CSVPreview.propTypes = {
  headers: PropTypes.arrayOf(PropTypes.string).isRequired,
  data: PropTypes.array.isRequired
}

/**
 * ExportPreview Component
 *
 * Live preview panel showing sample export data.
 * Updates dynamically with format, filter, and field selection changes.
 *
 * Features:
 * - Tab-based view switching (JSON, CSV, Darwin Core)
 * - Syntax-highlighted JSON
 * - Table-formatted CSV
 * - Copy to clipboard
 * - Full preview modal
 * - Debounced updates (500ms)
 *
 * @component
 * @example
 * <ExportPreview
 *   format="json"
 *   filter={{ tags: ['moth'], date_start: '2024-01-01' }}
 *   selectedFields={['filename', 'tags', 'latitude']}
 *   onOpenModal={() => setModalOpen(true)}
 * />
 */
export default function ExportPreview({ format, filter, selectedFields, onOpenModal }) {
  const [activeTab, setActiveTab] = useState('json')
  const [copyStatus, setCopyStatus] = useState(null)

  // Fetch preview data with debouncing
  const { previewData, isLoading, isError, error } = useExportPreview({
    format,
    filter,
    selectedFields
  })

  // Handle copy to clipboard
  const handleCopy = async () => {
    try {
      let textToCopy = ''

      if (activeTab === 'csv' && previewData?.headers) {
        // CSV format
        const headerRow = previewData.headers.join(',')
        const dataRows = previewData.data.map(row =>
          previewData.headers.map(h => {
            const value = row[h]
            if (Array.isArray(value)) return `"${value.join('; ')}"`
            if (typeof value === 'string' && value.includes(',')) return `"${value}"`
            return value ?? ''
          }).join(',')
        ).join('\n')
        textToCopy = `${headerRow}\n${dataRows}`
      } else {
        // JSON format
        textToCopy = JSON.stringify(previewData?.data || [], null, 2)
      }

      await navigator.clipboard.writeText(textToCopy)
      setCopyStatus('success')
      setTimeout(() => setCopyStatus(null), 2000)
    } catch {
      setCopyStatus('error')
      setTimeout(() => setCopyStatus(null), 2000)
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-8">
        <div className="flex items-center justify-center text-gray-500 dark:text-gray-400">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3" />
          Loading preview...
        </div>
      </div>
    )
  }

  // Error state
  if (isError) {
    return (
      <div className="border border-red-200 dark:border-red-800 rounded-lg p-8">
        <div className="text-center text-red-600 dark:text-red-400">
          <p className="font-medium mb-2">Failed to load preview</p>
          <p className="text-sm">{error?.message || 'Unknown error'}</p>
        </div>
      </div>
    )
  }

  // Empty state
  if (!previewData?.data || previewData.data.length === 0) {
    return (
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-8">
        <div className="text-center text-gray-500 dark:text-gray-400">
          <p className="font-medium mb-2">No photos found</p>
          <p className="text-sm">Adjust your filters to see a preview</p>
        </div>
      </div>
    )
  }

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      {/* Header with tabs and controls */}
      <div className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-gray-900 dark:text-gray-100">Preview</h3>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Showing {previewData.data.length} sample{previewData.data.length !== 1 ? 's' : ''}
            </span>
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-1 px-3 py-1 text-sm text-gray-700 dark:text-gray-300
                       hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
              title="Copy to clipboard"
            >
              <DocumentDuplicateIcon className="h-4 w-4" />
              {copyStatus === 'success' ? 'Copied!' : copyStatus === 'error' ? 'Failed to copy' : 'Copy'}
            </button>
            {onOpenModal && (
              <button
                type="button"
                onClick={onOpenModal}
                className="flex items-center gap-1 px-3 py-1 text-sm text-blue-600 dark:text-blue-400
                         hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
                title="Full preview"
              >
                <ArrowsPointingOutIcon className="h-4 w-4" />
                Full Preview
              </button>
            )}
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex gap-2" role="tablist">
          {PREVIEW_TABS.map(tab => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium rounded-t
                       ${activeTab === tab.id
                  ? 'bg-white dark:bg-gray-900 text-blue-600 dark:text-blue-400 border-t border-x border-gray-200 dark:border-gray-700'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Preview content */}
      <div className="p-4 bg-white dark:bg-gray-900 max-h-96 overflow-auto">
        {activeTab === 'csv' ? (
          <CSVPreview
            headers={previewData.headers || selectedFields}
            data={previewData.data}
          />
        ) : (
          <JSONPreview data={previewData.data} />
        )}
      </div>
    </div>
  )
}

ExportPreview.propTypes = {
  /** Current export format */
  format: PropTypes.oneOf(['json', 'csv', 'darwin_core', 'inaturalist']).isRequired,
  /** Filter criteria for photos */
  filter: PropTypes.object.isRequired,
  /** Selected fields to include in preview */
  selectedFields: PropTypes.arrayOf(PropTypes.string).isRequired,
  /** Callback to open full preview modal */
  onOpenModal: PropTypes.func
}
