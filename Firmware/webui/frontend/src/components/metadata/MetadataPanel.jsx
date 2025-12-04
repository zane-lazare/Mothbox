import { useState, useEffect, useCallback, useRef } from 'react'
import PropTypes from 'prop-types'
import { TagIcon, BugAntIcon, DocumentTextIcon, CameraIcon, AdjustmentsHorizontalIcon, XMarkIcon } from '@heroicons/react/24/outline'
import usePhotoMetadata from '../../hooks/usePhotoMetadata'
import useSidecarMetadata from '../../hooks/useSidecarMetadata'
import useAutoSave from '../../hooks/useAutoSave'
import AccordionSection from './AccordionSection'
import SaveStatusIndicator from './SaveStatusIndicator'
import MetadataTags from './MetadataTags'
import MetadataSpecies from './MetadataSpecies'
import MetadataNotes from './MetadataNotes'
import MetadataCustomFields from './MetadataCustomFields'
import MetadataEXIF from './MetadataEXIF'
import MetadataSkeleton from './MetadataSkeleton'

/**
 * MetadataPanel - Container component for photo metadata display and editing
 *
 * Orchestrates all metadata sections using accordion UI with auto-save functionality.
 * Fetches both EXIF metadata (read-only) and sidecar metadata (editable) and provides
 * seamless editing experience with debounced auto-save.
 *
 * Features:
 * - Accordion-based UI with collapsible sections
 * - Auto-save with 2-second debounce
 * - Optimistic updates for instant feedback
 * - Real-time save status indicator
 * - Loading skeleton during data fetch
 * - Error handling with retry capability
 * - Full keyboard navigation support
 *
 * @param {string} photoPath - Full path to the photo file
 * @param {string} [className] - Optional additional CSS classes
 * @param {Function} [onClose] - Optional callback when panel is closed (for Escape or Ctrl+Enter shortcuts)
 *
 * @example
 * <MetadataPanel photoPath="/var/lib/mothbox/photos/photo.jpg" />
 */
export default function MetadataPanel({ photoPath, className = '', onClose }) {
  // Ref for panel container to check focus
  const panelRef = useRef(null)
  // Get filename from path for sidecar operations
  const filename = photoPath ? photoPath.split('/').pop() : null

  // Mobile drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

  // Fetch EXIF metadata (read-only)
  const { data: exifData, isLoading: exifLoading, isError: exifError, refetch: refetchExif } = usePhotoMetadata(photoPath)

  // Fetch and mutate sidecar metadata (editable)
  const {
    data: sidecarData,
    isLoading: sidecarLoading,
    updateMetadata
  } = useSidecarMetadata(filename)

  // Local state for editable fields
  const [editableData, setEditableData] = useState({
    tags: [],
    species: '',
    species_confidence: 'unknown',
    species_common_name: '',
    species_reference_url: '',
    notes: '',
    custom: {}
  })

  // Sync local state with fetched sidecar data
  useEffect(() => {
    if (sidecarData) {
      setEditableData({
        tags: sidecarData.user_tags || [],
        species: sidecarData.species || '',
        species_confidence: sidecarData.species_confidence || 'unknown',
        species_common_name: sidecarData.species_common_name || '',
        species_reference_url: sidecarData.species_reference_url || '',
        notes: sidecarData.notes || '',
        custom: sidecarData.custom || {}
      })
    }
  }, [sidecarData])

  // Auto-save hook with 2-second debounce
  const { status: saveStatus, error: saveError, saveNow } = useAutoSave({
    data: editableData,
    onSave: async (data) => {
      await updateMetadata({
        user_tags: data.tags,
        species: data.species,
        species_confidence: data.species_confidence,
        species_common_name: data.species_common_name,
        species_reference_url: data.species_reference_url,
        notes: data.notes,
        custom: data.custom
      })
    },
    delay: 2000,
    enabled: !!filename
  })

  // Keyboard shortcut handler
  const handleKeyDown = useCallback((e) => {
    // Focus check required: This handler is attached to document (not panel element)
    // because we need to intercept Ctrl+S before browser's save dialog. Without this
    // check, shortcuts would trigger even when focus is outside the panel (e.g., gallery).
    if (!panelRef.current?.contains(document.activeElement)) {
      return
    }

    // Ctrl+S or Cmd+S - Immediate save
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault()
      saveNow()
    }

    // Ctrl+Enter or Cmd+Enter - Save and close
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      saveNow()
      onClose?.()
    }

    // Escape - Close panel
    if (e.key === 'Escape') {
      onClose?.()
    }
  }, [saveNow, onClose])

  // Add event listener for keyboard shortcuts
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  // Update handlers for each section
  const handleTagAdd = (tag) => {
    setEditableData(prev => ({
      ...prev,
      tags: [...prev.tags, tag]
    }))
  }

  const handleTagRemove = (tag) => {
    setEditableData(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tag)
    }))
  }

  const handleSpeciesChange = (field, value) => {
    setEditableData(prev => {
      // Map field names to state keys
      const fieldMap = {
        'species': 'species',
        'confidence': 'species_confidence',
        'commonName': 'species_common_name',
        'referenceUrl': 'species_reference_url'
      }
      const stateKey = fieldMap[field] || field
      return { ...prev, [stateKey]: value }
    })
  }

  const handleNotesChange = (value) => {
    setEditableData(prev => ({ ...prev, notes: value }))
  }

  const handleCustomFieldsChange = (fields) => {
    setEditableData(prev => ({ ...prev, custom: fields }))
  }

  const isLoading = exifLoading || sidecarLoading

  // Loading state - show skeleton
  if (isLoading) {
    return <MetadataSkeleton rows={6} className={className} />
  }

  // Error state - show error message with retry button
  if (exifError) {
    return (
      <div className={`p-4 text-center ${className}`}>
        <p className="text-red-600 dark:text-red-400 font-semibold mb-2">
          Failed to load metadata
        </p>
        <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
          Please try again or check if the photo exists.
        </p>
        <button
          onClick={() => refetchExif()}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  // Success state - render accordion sections
  return (
    <>
      {/* Mobile Toggle Button */}
      <button
        onClick={() => setIsDrawerOpen(true)}
        className="md:hidden fixed bottom-4 right-4 z-40 p-4 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-colors"
        aria-label="Open metadata panel"
        data-testid="mobile-toggle-button"
      >
        <DocumentTextIcon className="w-6 h-6" />
      </button>

      {/* Mobile Overlay */}
      {isDrawerOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setIsDrawerOpen(false)}
          data-testid="mobile-overlay"
          aria-hidden="true"
        />
      )}

      {/* Panel - Desktop: sidebar, Mobile: drawer */}
      <div
        ref={panelRef}
        data-testid="metadata-panel"
        role="dialog"
        aria-label="Photo metadata"
        className={`
          ${className}
          ${isDrawerOpen ? 'fixed inset-x-0 bottom-0 z-50 max-h-[80vh] bg-white dark:bg-gray-900 rounded-t-2xl shadow-lg transform translate-y-0 transition-transform' : 'hidden'}
          md:block md:relative md:bg-white md:dark:bg-gray-900 flex flex-col
        `}
        tabIndex={-1}
      >
        {/* Mobile Header with Close */}
        {isDrawerOpen && (
          <div
            className="md:hidden flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-700"
            data-testid="drawer-mobile-header"
          >
            <span className="font-medium">Photo Metadata</span>
            <button
              onClick={() => setIsDrawerOpen(false)}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
              aria-label="Close metadata panel"
              data-testid="drawer-close-button"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* Save Status */}
        <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
          <SaveStatusIndicator
            status={saveStatus}
            onRetry={saveNow}
            errorMessage={saveError?.message}
          />
          {/* Keyboard Shortcuts Hint */}
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
            <kbd className="px-1 py-0.5 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded dark:bg-gray-700 dark:text-gray-100 dark:border-gray-600">Ctrl+S</kbd> to save,
            <kbd className="px-1 py-0.5 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded dark:bg-gray-700 dark:text-gray-100 dark:border-gray-600 ml-1">Ctrl+Enter</kbd> to save & close{onClose ? ', ' : ''}
            {onClose && <><kbd className="px-1 py-0.5 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded dark:bg-gray-700 dark:text-gray-100 dark:border-gray-600 ml-1">Esc</kbd> to close</>}
          </p>
        </div>

        {/* Accordion Sections */}
        <div className="flex-1 overflow-y-auto">
          <AccordionSection title="Tags" icon={<TagIcon className="w-5 h-5" />} defaultExpanded>
            <MetadataTags
              tags={editableData.tags}
              onAddTag={handleTagAdd}
              onRemoveTag={handleTagRemove}
            />
          </AccordionSection>

          <AccordionSection title="Species" icon={<BugAntIcon className="w-5 h-5" />}>
            <MetadataSpecies
              species={editableData.species}
              confidence={editableData.species_confidence}
              commonName={editableData.species_common_name}
              referenceUrl={editableData.species_reference_url}
              onChange={handleSpeciesChange}
            />
          </AccordionSection>

          <AccordionSection title="Notes" icon={<DocumentTextIcon className="w-5 h-5" />}>
            <MetadataNotes
              value={editableData.notes}
              onChange={handleNotesChange}
            />
          </AccordionSection>

          <AccordionSection title="EXIF Data" icon={<CameraIcon className="w-5 h-5" />}>
            <MetadataEXIF data={exifData} />
          </AccordionSection>

          <AccordionSection title="Custom Fields" icon={<AdjustmentsHorizontalIcon className="w-5 h-5" />}>
            <MetadataCustomFields
              fields={editableData.custom}
              onChange={handleCustomFieldsChange}
            />
          </AccordionSection>
        </div>
      </div>
    </>
  )
}

MetadataPanel.propTypes = {
  photoPath: PropTypes.string.isRequired,
  className: PropTypes.string,
  onClose: PropTypes.func,
}
