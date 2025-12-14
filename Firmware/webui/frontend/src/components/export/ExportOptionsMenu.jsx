import { useRef, useEffect, useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import { useFloating, offset, flip, shift, autoUpdate } from '@floating-ui/react'
import {
  CircleStackIcon,
  DocumentTextIcon,
  TableCellsIcon,
  BeakerIcon
} from '@heroicons/react/20/solid'
import { useSinglePhotoExport } from '../../hooks/useSinglePhotoExport'
import { Z_INDEX } from '../../constants/config'

const EXPORT_FORMATS = [
  {
    id: 'darwin_core',
    name: 'Darwin Core',
    description: 'For GBIF biodiversity portals',
    icon: BeakerIcon
  },
  {
    id: 'inaturalist',
    name: 'iNaturalist',
    description: 'With XMP sidecars',
    icon: CircleStackIcon
  },
  {
    id: 'json',
    name: 'JSON',
    description: 'All metadata fields',
    icon: DocumentTextIcon
  },
  {
    id: 'csv',
    name: 'CSV',
    description: 'Excel compatible',
    icon: TableCellsIcon
  },
]

function ExportOptionsMenu({ photoPath, isOpen, onClose, anchorEl, position }) {
  const menuRef = useRef(null)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)

  // Use refs to stabilize event listener dependencies
  const onCloseRef = useRef(onClose)
  const anchorElRef = useRef(anchorEl)

  // Export hook
  const { exportPhoto, isExporting } = useSinglePhotoExport()

  // Floating UI for positioning (only used when anchorEl is provided)
  const { refs, floatingStyles } = useFloating({
    placement: 'bottom-start',
    middleware: [
      offset(4),
      flip({ fallbackPlacements: ['top-start', 'bottom-end', 'top-end'] }),
      shift({ padding: 8 })
    ],
    whileElementsMounted: autoUpdate,
  })

  // Keep refs updated with latest prop values
  useEffect(() => {
    onCloseRef.current = onClose
    anchorElRef.current = anchorEl
  })

  // Update reference element for floating UI
  useEffect(() => {
    if (anchorEl) {
      refs.setReference(anchorEl)
    }
  }, [anchorEl, refs])

  // Reset highlight when menu opens
  useEffect(() => {
    if (isOpen) {
      setHighlightedIndex(-1)
    }
  }, [isOpen])

  // Handle format selection
  const handleFormatSelect = useCallback((formatId) => {
    if (isExporting) return

    exportPhoto(photoPath, formatId)
    onCloseRef.current()
  }, [photoPath, exportPhoto, isExporting])

  // Close on Escape or click outside
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e) => {
      switch (e.key) {
        case 'Escape':
          onCloseRef.current()
          break
        case 'ArrowDown':
          e.preventDefault()
          setHighlightedIndex((prev) => {
            if (prev === -1) return 0
            return (prev + 1) % EXPORT_FORMATS.length
          })
          break
        case 'ArrowUp':
          e.preventDefault()
          setHighlightedIndex((prev) => {
            if (prev === -1) return EXPORT_FORMATS.length - 1
            return (prev - 1 + EXPORT_FORMATS.length) % EXPORT_FORMATS.length
          })
          break
        case 'Enter':
          e.preventDefault()
          if (highlightedIndex >= 0 && highlightedIndex < EXPORT_FORMATS.length) {
            handleFormatSelect(EXPORT_FORMATS[highlightedIndex].id)
          }
          break
      }
    }

    const handleClickOutside = (e) => {
      if (menuRef.current &&
          !menuRef.current.contains(e.target) &&
          !anchorElRef.current?.contains(e.target)) {
        onCloseRef.current()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen, highlightedIndex, handleFormatSelect])

  if (!isOpen) return null

  // Determine positioning style
  const menuStyle = position
    ? {
        position: 'absolute',
        left: `${position.x}px`,
        top: `${position.y}px`,
      }
    : floatingStyles

  return (
    <div
      ref={(node) => {
        menuRef.current = node
        if (!position) {
          refs.setFloating(node)
        }
      }}
      style={menuStyle}
      className={`
        ${Z_INDEX.MODAL} w-64 bg-white dark:bg-gray-800 rounded-lg shadow-xl
        border border-gray-200 dark:border-gray-700
        transition-all duration-150 origin-top-left
        ${isOpen ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}
      `}
      role="menu"
      aria-label="Export photo"
      tabIndex={-1}
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
          Export Photo
        </h3>
      </div>

      {/* Format Options */}
      <div className="py-1">
        {EXPORT_FORMATS.map((format, index) => {
          const Icon = format.icon
          const isHighlighted = highlightedIndex === index
          return (
            <button
              key={format.id}
              role="menuitem"
              disabled={isExporting}
              onClick={() => handleFormatSelect(format.id)}
              onMouseEnter={() => setHighlightedIndex(index)}
              className={`
                w-full flex items-start gap-3 px-3 py-2.5 text-left
                hover:bg-gray-100 dark:hover:bg-gray-700
                disabled:opacity-50 disabled:cursor-not-allowed
                ${isHighlighted ? 'ring-2 ring-blue-500 bg-gray-50 dark:bg-gray-700' : ''}
              `}
            >
              <Icon className="w-5 h-5 text-gray-400 dark:text-gray-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {format.name}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {format.description}
                </div>
              </div>
            </button>
          )
        })}
      </div>

      {/* Loading indicator */}
      {isExporting && (
        <div className="px-3 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Exporting...
          </div>
        </div>
      )}
    </div>
  )
}

ExportOptionsMenu.propTypes = {
  photoPath: PropTypes.string.isRequired,
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  anchorEl: PropTypes.instanceOf(Element),
  position: PropTypes.shape({
    x: PropTypes.number.isRequired,
    y: PropTypes.number.isRequired,
  }),
}

export default ExportOptionsMenu
