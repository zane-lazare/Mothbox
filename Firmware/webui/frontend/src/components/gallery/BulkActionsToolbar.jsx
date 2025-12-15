import { createPortal } from 'react-dom'
import { TagIcon, BeakerIcon, ArrowDownTrayIcon, TrashIcon, XMarkIcon } from '@heroicons/react/24/outline'
import useSelection from '../../hooks/useSelection'
import { Z_INDEX } from '../../constants/config'

export default function BulkActionsToolbar({
  onTagClick,
  onSpeciesClick,
  onExportClick,
  onDeleteClick
}) {
  const { selectedCount, deselectAll } = useSelection()

  // Don't render if nothing selected
  if (selectedCount === 0) return null

  const toolbar = (
    <div
      role="toolbar"
      aria-label="Bulk actions for selected photos"
      className={`fixed bottom-4 left-1/2 -translate-x-1/2 ${Z_INDEX.TOOLBAR}
                 flex items-center gap-3 px-4 py-3
                 bg-white dark:bg-gray-800
                 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700`}
    >
      {/* Selection count */}
      <span
        aria-live="polite"
        className="text-sm font-medium text-gray-700 dark:text-gray-300"
      >
        {selectedCount} {selectedCount === 1 ? 'photo' : 'photos'} selected
      </span>

      {/* Divider */}
      <div className="h-6 w-px bg-gray-300 dark:bg-gray-600" />

      {/* Action buttons */}
      <button
        onClick={onTagClick}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm
                   text-gray-700 dark:text-gray-300
                   hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
        aria-label="Add tags to selected photos"
      >
        <TagIcon className="h-4 w-4" />
        Tag
      </button>

      <button
        onClick={onSpeciesClick}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm
                   text-gray-700 dark:text-gray-300
                   hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
        aria-label="Set species for selected photos"
      >
        <BeakerIcon className="h-4 w-4" />
        Species
      </button>

      <button
        onClick={onExportClick}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm
                   text-gray-700 dark:text-gray-300
                   hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
        aria-label="Export selected photos"
      >
        <ArrowDownTrayIcon className="h-4 w-4" />
        Export
      </button>

      <button
        onClick={onDeleteClick}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm
                   text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md"
        aria-label="Delete selected photos"
        aria-describedby="delete-warning"
      >
        <TrashIcon className="h-4 w-4" />
        Delete
      </button>

      {/* Divider */}
      <div className="h-6 w-px bg-gray-300 dark:bg-gray-600" />

      <button
        onClick={deselectAll}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm
                   text-gray-500 hover:text-gray-700 dark:text-gray-400
                   dark:hover:text-gray-200 rounded-md"
        aria-label="Deselect all photos"
      >
        <XMarkIcon className="h-4 w-4" />
        Deselect All
      </button>

      {/* Hidden warning for screen readers */}
      <span id="delete-warning" className="sr-only">
        Warning: This action cannot be undone
      </span>
    </div>
  )

  // Render as portal to body to escape parent overflow/positioning
  return createPortal(toolbar, document.body)
}
