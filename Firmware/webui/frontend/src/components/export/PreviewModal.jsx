import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import PropTypes from 'prop-types'
import { XMarkIcon, DocumentDuplicateIcon } from '@heroicons/react/24/outline'
import { Z_INDEX } from '../../constants/config'

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
 * PreviewModal Component
 *
 * Full-screen modal for viewing export preview data.
 * Larger code view with scroll, tabs for different formats,
 * and copy to clipboard functionality.
 *
 * @component
 * @example
 * <PreviewModal
 *   isOpen={isModalOpen}
 *   onClose={() => setIsModalOpen(false)}
 *   previewData={{ format: 'json', data: [...] }}
 *   format="json"
 * />
 */
export default function PreviewModal({ isOpen, onClose, previewData, format }) {
  const [activeTab, setActiveTab] = useState('json')
  const [copyStatus, setCopyStatus] = useState(null)

  // Sync activeTab with format prop
  useEffect(() => {
    if (format) {
      setActiveTab(format)
    }
  }, [format])

  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose()
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }

    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  if (!isOpen) return null

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

  const modal = (
    <div className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center p-4`}>
      {/* Backdrop */}
      <div
        data-testid="modal-backdrop"
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal content */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="preview-modal-title"
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl
                   w-full max-w-6xl max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 id="preview-modal-title" className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Export Preview
          </h2>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300
                       hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              <DocumentDuplicateIcon className="h-4 w-4" />
              {copyStatus === 'success' ? 'Copied!' : copyStatus === 'error' ? 'Failed to copy' : 'Copy'}
            </button>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              <XMarkIcon className="h-6 w-6 text-gray-500 dark:text-gray-400" />
            </button>
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex gap-2 px-6 pt-4 border-b border-gray-200 dark:border-gray-700" role="tablist">
          {PREVIEW_TABS.map(tab => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium rounded-t
                       ${activeTab === tab.id
                  ? 'bg-gray-50 dark:bg-gray-900 text-blue-600 dark:text-blue-400 border-t border-x border-gray-200 dark:border-gray-700'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div
          data-testid="modal-content"
          className="flex-1 overflow-auto p-6"
        >
          {!previewData?.data || previewData.data.length === 0 ? (
            <div className="text-center text-gray-500 dark:text-gray-400 py-12">
              <p className="text-lg font-medium">No data to preview</p>
            </div>
          ) : activeTab === 'csv' ? (
            <CSVPreview
              headers={previewData.headers || Object.keys(previewData.data[0] || {})}
              data={previewData.data}
            />
          ) : (
            <JSONPreview data={previewData.data} />
          )}
        </div>
      </div>
    </div>
  )

  return createPortal(modal, document.body)
}

PreviewModal.propTypes = {
  /** Whether the modal is open */
  isOpen: PropTypes.bool.isRequired,
  /** Close handler */
  onClose: PropTypes.func.isRequired,
  /** Preview data to display */
  previewData: PropTypes.shape({
    format: PropTypes.string,
    data: PropTypes.array,
    headers: PropTypes.arrayOf(PropTypes.string)
  }),
  /** Current format (json, csv, darwin_core, inaturalist) */
  format: PropTypes.oneOf(['json', 'csv', 'darwin_core', 'inaturalist'])
}
