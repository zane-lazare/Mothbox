import { useRef, useEffect, useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import { useFloating, offset, flip, shift } from '@floating-ui/react'
import { ArrowRightIcon, ArrowDownTrayIcon } from '@heroicons/react/20/solid'
import ExportOptionsMenu from '../export/ExportOptionsMenu'
import { Z_INDEX } from '../../constants/config'

function PhotoContextMenu({ photo, isOpen, onClose, position }) {
  const menuRef = useRef(null)
  const exportItemRef = useRef(null)
  const [showExportMenu, setShowExportMenu] = useState(false)
  const [adjustedPosition, setAdjustedPosition] = useState(position)

  // Use refs to stabilize event listener dependencies
  const onCloseRef = useRef(onClose)

  // Floating UI for positioning ExportOptionsMenu relative to Export item
  const { refs, floatingStyles } = useFloating({
    placement: 'right-start',
    middleware: [
      offset(4),
      flip({ fallbackPlacements: ['left-start', 'right-end', 'left-end'] }),
      shift({ padding: 8 }),
    ],
  })

  // Keep refs updated with latest prop values
  useEffect(() => {
    onCloseRef.current = onClose
  })

  // Update floating UI reference when exportItemRef changes
  useEffect(() => {
    if (exportItemRef.current) {
      refs.setReference(exportItemRef.current)
    }
  }, [refs, showExportMenu])

  // Adjust position to prevent viewport overflow
  useEffect(() => {
    if (!isOpen || !menuRef.current) return

    const menuWidth = 200 // Approximate menu width
    const menuHeight = 100 // Approximate menu height
    const padding = 8 // Safety padding

    let newX = position.x
    let newY = position.y

    // Check right edge
    if (position.x + menuWidth > window.innerWidth) {
      newX = window.innerWidth - menuWidth - padding
    }

    // Check bottom edge
    if (position.y + menuHeight > window.innerHeight) {
      newY = window.innerHeight - menuHeight - padding
    }

    setAdjustedPosition({ x: newX, y: newY })
  }, [isOpen, position])

  // Reset submenu state when menu opens/closes
  useEffect(() => {
    if (!isOpen) {
      setShowExportMenu(false)
    }
  }, [isOpen])

  // Close on Escape or click outside
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onCloseRef.current()
      }
    }

    const handleClickOutside = (e) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(e.target) &&
        (!showExportMenu || !e.target.closest('[role="menu"]'))
      ) {
        onCloseRef.current()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen, showExportMenu])

  // Handle Export menu item interactions
  const handleExportClick = useCallback(() => {
    setShowExportMenu(true)
  }, [])

  const handleExportHover = useCallback(() => {
    setShowExportMenu(true)
  }, [])

  const handleExportLeave = useCallback(() => {
    setShowExportMenu(false)
  }, [])

  const handleExportKeyDown = useCallback((e) => {
    if (e.key === 'Enter') {
      setShowExportMenu(true)
    }
  }, [])

  const handleExportMenuClose = useCallback(() => {
    setShowExportMenu(false)
  }, [])

  if (!isOpen) return null

  const menuStyle = {
    position: 'absolute',
    left: `${adjustedPosition.x}px`,
    top: `${adjustedPosition.y}px`,
  }

  return (
    <>
      <div
        ref={menuRef}
        style={menuStyle}
        className={`
          ${Z_INDEX.MODAL} w-48 bg-white dark:bg-gray-800 rounded-lg shadow-xl
          border border-gray-200 dark:border-gray-700
          transition-all duration-150 origin-top-left
          ${isOpen ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}
        `}
        role="menu"
        aria-label="Photo context menu"
        tabIndex={-1}
      >
        <div className="py-1">
          <button
            ref={exportItemRef}
            role="menuitem"
            onClick={handleExportClick}
            onMouseEnter={handleExportHover}
            onMouseLeave={handleExportLeave}
            onKeyDown={handleExportKeyDown}
            className="w-full flex items-center justify-between px-3 py-2 text-left
                       hover:bg-gray-100 dark:hover:bg-gray-700
                       text-gray-900 dark:text-gray-100"
            aria-label="Export photo"
          >
            <span className="flex items-center gap-2">
              <ArrowDownTrayIcon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
              <span className="text-sm">Export</span>
            </span>
            <ArrowRightIcon className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>

      {/* ExportOptionsMenu positioned relative to Export item */}
      <ExportOptionsMenu
        photoPath={photo.path}
        isOpen={showExportMenu}
        onClose={handleExportMenuClose}
        anchorEl={exportItemRef.current}
      />
    </>
  )
}

PhotoContextMenu.propTypes = {
  photo: PropTypes.shape({
    path: PropTypes.string.isRequired,
    filename: PropTypes.string.isRequired,
  }).isRequired,
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  position: PropTypes.shape({
    x: PropTypes.number.isRequired,
    y: PropTypes.number.isRequired,
  }).isRequired,
}

export default PhotoContextMenu
