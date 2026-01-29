import { useInfiniteQuery } from '@tanstack/react-query'
import { getPhotosPaginated } from '../utils/api'
import { QUERY_KEYS } from '../utils/queryKeys'
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ArrowTopRightOnSquareIcon, AdjustmentsHorizontalIcon } from '@heroicons/react/24/outline'
import { useInfiniteScroll } from '../hooks/useInfiniteScroll'
import { useViewMode } from '../hooks/useViewMode'
import { useSeries } from '../hooks/useSeries'
import { useClusteredLocations } from '../hooks/useClusteredLocations'
import { usePhotoSearch } from '../hooks/usePhotoSearch'
import useScrollRestoration from '../hooks/useScrollRestoration'
import useBulkOperations from '../hooks/useBulkOperations'
import useUndoToast from '../hooks/useUndoToast'
import useBulkExport from '../hooks/useBulkExport'
import PhotoSkeleton from '../components/PhotoSkeleton'
import PhotoGridItem from '../components/PhotoGridItem'
import PhotoListItem from '../components/PhotoListItem'
import SearchResultItem from '../components/gallery/SearchResultItem'
import StackedPhotoCard from '../components/StackedPhotoCard'
import VirtualPhotoGrid from '../components/VirtualPhotoGrid'
import PhotoLightbox from '../components/PhotoLightbox'
import MapView from '../components/MapView'
import ErrorBoundary from '../components/ErrorBoundary'
import LightboxErrorFallback from '../components/LightboxErrorFallback'
import ViewModeToggle from '../components/ViewModeToggle'
import SelectModeToggle from '../components/gallery/SelectModeToggle'
import BulkActionsToolbar from '../components/gallery/BulkActionsToolbar'
import BulkTagModal from '../components/gallery/BulkTagModal'
import BulkSpeciesModal from '../components/gallery/BulkSpeciesModal'
import BulkDeleteConfirmModal from '../components/gallery/BulkDeleteConfirmModal'
import BulkProgressModal from '../components/gallery/BulkProgressModal'
import BulkExportModal from '../components/gallery/BulkExportModal'
import EmptyStateMessage from '../components/EmptyStateMessage'
import { SearchBar } from '../components/gallery/SearchBar'
import { AdvancedSearchBuilder } from '../components/gallery/AdvancedSearchBuilder'
import { SelectionProvider, useSelectionContext } from '../contexts/SelectionContext'
import { FilterDrawer, FilterDrawerToggle, ActiveFilterChips, FilterErrorFallback } from '../components/filters'
import { useFilters } from '../hooks/useFilters'
import { combineWithUserSearch } from '../utils/filterQueryBuilder'
import { GALLERY_CONFIG, GALLERY_MESSAGES } from '../constants/config'
import { formatErrorMessage } from '../utils/helpers'
import toast from 'react-hot-toast'

/**
 * Inner Gallery component that uses selection context
 * Separated to allow SelectionProvider wrapping
 */
function GalleryContent() {
  const [selectedPhoto, setSelectedPhoto] = useState(null)
  const [selectedSeries, setSelectedSeries] = useState(null)
  const { viewMode, setViewMode, isLoading: isLoadingPreference } = useViewMode()
  const navigate = useNavigate()

  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false)

  // Filter state from useFilters hook
  const { searchQuery: filterQuery, hasFilters } = useFilters()

  // Combine user search query with filter query
  const combinedQuery = useMemo(() => {
    return combineWithUserSearch(searchQuery, filterQuery)
  }, [searchQuery, filterQuery])

  // Selection context for bulk operations
  const {
    isSelectMode,
    selectedPhotos,
    selectedCount,
    toggleSelectMode,
    selectAll,
    deselectAll,
  } = useSelectionContext()

  // Bulk operations
  const {
    bulkAddTags,
    bulkReplaceTags,
    bulkRemoveTags,
    bulkUpdateSpecies,
    bulkDelete,
  } = useBulkOperations()

  const { showUndoToast } = useUndoToast()

  // Bulk export hook
  const {
    exportPhotos,
    isExporting,
    progress: exportProgress,
    error: exportError,
    downloadUrl,
  } = useBulkExport({
    onComplete: () => {
      // Will show download button in success state
    }
  })

  // Modal state
  const [tagModalOpen, setTagModalOpen] = useState(false)
  const [speciesModalOpen, setSpeciesModalOpen] = useState(false)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [exportModalOpen, setExportModalOpen] = useState(false)
  const [progressModalOpen, setProgressModalOpen] = useState(false)
  const [progressOperation, setProgressOperation] = useState(null) // 'export' | 'tag' | 'species' | 'delete'
  const [progressState, setProgressState] = useState({
    status: 'processing',
    current: 0,
    total: 0,
    message: '',
  })

  // Scroll restoration for virtualized grid
  const { scrollRef, saveScrollPosition } = useScrollRestoration('gallery-main')

  // State tracking for toast notifications (prevent duplicates)
  const [hasShownInitialErrorToast, setHasShownInitialErrorToast] = useState(false)
  const [hasShownEndToast, setHasShownEndToast] = useState(false)
  const [hasShownSeriesErrorToast, setHasShownSeriesErrorToast] = useState(false)
  const prevPaginationError = useRef(null)

  // Search functionality
  const { results: searchResults, total: searchTotal, isLoading: isSearching, tookMs } = usePhotoSearch(combinedQuery)
  const isSearchActive = combinedQuery.trim().length > 0

  // Infinite query for paginated photos
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
    refetch,
  } = useInfiniteQuery({
    queryKey: QUERY_KEYS.PHOTOS_INFINITE,
    queryFn: ({ pageParam = 0 }) =>
      getPhotosPaginated({
        limit: GALLERY_CONFIG.PAGE_SIZE,
        offset: pageParam,
        sort: 'date_desc',
      }).then((res) => res.data),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      if (lastPage.pagination.has_next) {
        return lastPage.pagination.offset + lastPage.pagination.limit
      }
      return undefined
    },
  })

  // Fetch series data for grouping photos
  const { data: seriesData, isError: isSeriesError, refetch: refetchSeries } = useSeries()

  // Fetch clustered photo locations for map view
  const {
    clusters,
    unclustered,
    isLoading: isLoadingLocations,
    settings: clusterSettings,
    setEnabled: setClusterEnabled,
    setRadius: setClusterRadius,
  } = useClusteredLocations({ enabled: viewMode === 'map' })

  // Calculate total counts from clustered data
  const totalInClusters = clusters.reduce((sum, cluster) => sum + cluster.count, 0)
  const totalWithGps = totalInClusters + unclustered.length

  // Set up infinite scroll sentinel
  const sentinelRef = useInfiniteScroll({
    onLoadMore: fetchNextPage,
    hasMore: hasNextPage,
    isLoading: isFetchingNextPage,
    threshold: GALLERY_CONFIG.INFINITE_SCROLL.THRESHOLD,
    rootMargin: GALLERY_CONFIG.INFINITE_SCROLL.ROOT_MARGIN,
  })

  // Note: Keyboard handling (Escape, Arrow keys) is now managed by PhotoLightbox component

  // Flatten all pages into single photo array (memoized to prevent re-creation on every render)
  const photos = useMemo(() => data?.pages.flatMap((page) => page.photos) ?? [], [data?.pages])

  // Build series lookup map: photoPath -> seriesData
  // This allows quick lookup to determine if a photo is part of a series
  const seriesLookup = useMemo(() => {
    const lookup = new Map()
    if (seriesData?.series) {
      seriesData.series.forEach((series) => {
        series.photos.forEach((photo) => {
          // Handle both string paths and photo objects
          const photoPath = typeof photo === 'string' ? photo : photo.path
          lookup.set(photoPath, series)
        })
      })
    }
    return lookup
  }, [seriesData])

  // Filter photos for display: hide non-cover series photos (they're shown in stacked cards)
  const displayPhotos = useMemo(() => {
    return photos.filter((photo) => {
      const series = seriesLookup.get(photo.path)
      if (!series) return true // Not in a series, show it
      return series.cover_photo === photo.path // Only show if it's the cover photo
    })
  }, [photos, seriesLookup])

  // Compute photos for lightbox navigation - restricted to series when viewing a series
  const lightboxPhotos = useMemo(() => {
    if (selectedSeries) {
      // When viewing a series, normalize series photos to objects
      return selectedSeries.photos.map(photo => {
        if (typeof photo === 'string') {
          // Find full photo object from photos array, or create minimal object
          const fullPhoto = photos.find(p => p.path === photo)
          return fullPhoto || { path: photo, filename: photo.split('/').pop() }
        }
        return photo
      })
    }
    return photos
  }, [selectedSeries, photos])

  // Determine if virtualization should be enabled
  const shouldUseVirtualization = useMemo(() => {
    return (
      GALLERY_CONFIG.VIRTUALIZATION.ENABLED &&
      viewMode === 'grid' &&
      photos.length >= GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION
    )
  }, [viewMode, photos.length])

  // Memoized callbacks to prevent unnecessary re-renders
  const handleCloseLightbox = useCallback(() => {
    setSelectedPhoto(null)
    setSelectedSeries(null)
  }, [])
  const handlePhotoClick = useCallback((photo) => {
    // Save scroll position before opening lightbox
    saveScrollPosition()
    setSelectedPhoto(photo)
  }, [saveScrollPosition])
  const handleNavigate = useCallback((photo) => {
    // Validate photo exists in current photos array before navigating
    if (photos.some(p => p.path === photo.path)) {
      setSelectedPhoto(photo)
    }
  }, [photos])
  // Handle series card click - open lightbox with cover photo and track series
  const handleSeriesPhotoClick = useCallback((photo, series) => {
    saveScrollPosition()
    setSelectedSeries(series)
    setSelectedPhoto(photo)
  }, [saveScrollPosition])

  // Handle map marker click - open lightbox with the clicked photo
  const handleMapPhotoClick = useCallback((location) => {
    // Find the photo object in the photos array by matching the path
    const photo = photos.find(p => p.path === location.path)
    if (photo) {
      saveScrollPosition()
      setSelectedPhoto(photo)
    }
  }, [photos, saveScrollPosition])

  // Toast notifications for error states
  useEffect(() => {
    // Initial load error toast
    if (isError && photos.length === 0 && !hasShownInitialErrorToast) {
      toast.error(
        formatErrorMessage(error, GALLERY_MESSAGES.ERROR.INITIAL, GALLERY_MESSAGES.ERROR.FALLBACK),
        { duration: 6000 }
      )
      setHasShownInitialErrorToast(true)
    }

    // Reset flag when error clears
    if (!isError) {
      setHasShownInitialErrorToast(false)
    }
  }, [isError, photos.length, error, hasShownInitialErrorToast])

  // Toast notification for pagination errors
  useEffect(() => {
    if (isError && photos.length > 0) {
      // Only show toast if this is a new error (prevent duplicates)
      const errorMessage = error?.message || 'Unknown error'
      if (prevPaginationError.current !== errorMessage) {
        toast.error(
          formatErrorMessage(error, GALLERY_MESSAGES.ERROR.PAGINATION, GALLERY_MESSAGES.ERROR.FALLBACK),
          { duration: 6000 }
        )
        prevPaginationError.current = errorMessage
      }
    } else {
      // Clear on success
      prevPaginationError.current = null
    }
  }, [isError, photos.length, error])

  // Toast notification when all photos loaded
  useEffect(() => {
    if (!hasNextPage && photos.length > 0 && !isError && !hasShownEndToast) {
      toast.success('All photos loaded', { duration: 3000 })
      setHasShownEndToast(true)
    }

    // Reset if user navigates away and back (has more pages again)
    if (hasNextPage) {
      setHasShownEndToast(false)
    }
  }, [hasNextPage, photos.length, isError, hasShownEndToast])

  // Toast notification for series API errors
  useEffect(() => {
    if (isSeriesError && !hasShownSeriesErrorToast) {
      toast.error('Could not load photo series. Displaying all photos individually.', {
        duration: 5000,
      })
      setHasShownSeriesErrorToast(true)
    }

    // Reset if series loads successfully later
    if (!isSeriesError) {
      setHasShownSeriesErrorToast(false)
    }
  }, [isSeriesError, hasShownSeriesErrorToast])

  // Derive export progress state from hook (avoids race condition with manual updates)
  const exportProgressState = useMemo(() => {
    if (progressOperation !== 'export') return null

    if (exportError) {
      return {
        status: 'error',
        current: 0,
        total: selectedCount,
        message: exportError,
      }
    }

    if (!isExporting && downloadUrl) {
      return {
        status: 'success',
        current: selectedCount,
        total: selectedCount,
        message: 'Export complete!',
        downloadUrl: downloadUrl,
      }
    }

    if (exportProgress) {
      return {
        status: 'processing',
        current: exportProgress.current,
        total: exportProgress.total,
        message: `${exportProgress.phase}... ${exportProgress.percent}%`,
      }
    }

    // Initial state while waiting for first progress update
    return {
      status: 'processing',
      current: 0,
      total: selectedCount,
      message: `Exporting ${selectedCount} photos...`,
    }
  }, [progressOperation, isExporting, exportProgress, exportError, downloadUrl, selectedCount])

  // Current progress state (export uses derived state, others use manual state)
  const currentProgressState = progressOperation === 'export' ? exportProgressState : progressState

  // Keyboard shortcuts for bulk selection
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Only handle shortcuts when in select mode
      if (!isSelectMode) return

      // Escape - exit select mode
      if (e.key === 'Escape') {
        e.preventDefault()
        toggleSelectMode()
        return
      }

      // Ctrl+A - select all photos
      if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
        e.preventDefault()
        selectAll(photos.map(p => p.path))
        return
      }

      // Ctrl+E - open export modal (only if photos selected)
      if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
        if (selectedCount > 0) {
          e.preventDefault()
          setExportModalOpen(true)
        }
        return
      }

      // Delete - open delete confirmation modal (only if photos selected)
      if (e.key === 'Delete' && selectedCount > 0) {
        e.preventDefault()
        setDeleteModalOpen(true)
        return
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isSelectMode, toggleSelectMode, selectAll, photos, selectedCount])

  // Bulk operation handlers
  const handleBulkTagApply = useCallback(async ({ tags, mode }) => {
    setTagModalOpen(false)
    setProgressModalOpen(true)
    setProgressState({
      status: 'processing',
      current: 0,
      total: selectedCount,
      message: `Applying tags to ${selectedCount} photos...`,
    })

    const filenames = Array.from(selectedPhotos)
    let result

    const onProgress = (progress) => {
      setProgressState({
        status: 'processing',
        current: progress.processedCount,
        total: filenames.length,
        message: `Processing batch ${progress.currentBatch} of ${progress.totalBatches}...`,
      })
    }

    try {
      if (mode === 'add') {
        result = await bulkAddTags(filenames, tags, onProgress)
      } else if (mode === 'replace') {
        result = await bulkReplaceTags(filenames, tags, onProgress)
      } else if (mode === 'remove') {
        result = await bulkRemoveTags(filenames, tags, onProgress)
      }

      if (result.success.length > 0) {
        setProgressState({
          status: 'success',
          current: result.success.length,
          total: filenames.length,
          message: `Successfully updated ${result.success.length} photos`,
        })

        // Show undo toast with undo callback
        if (result.previousState) {
          showUndoToast(`Updated tags on ${result.success.length} photos`, async () => {
            // Restore previous tags
            for (const [filename, state] of Object.entries(result.previousState)) {
              await bulkReplaceTags([filename], state.tags || [])
            }
            toast.success('Tags restored')
          })
        }

        deselectAll()
      } else {
        setProgressState({
          status: 'error',
          current: 0,
          total: filenames.length,
          message: 'Failed to update any photos',
        })
      }
    } catch (error) {
      setProgressState({
        status: 'error',
        current: 0,
        total: filenames.length,
        message: error.message || 'An error occurred',
      })
    }
  }, [selectedPhotos, selectedCount, bulkAddTags, bulkReplaceTags, bulkRemoveTags, showUndoToast, deselectAll])

  const handleBulkSpeciesApply = useCallback(async (speciesData) => {
    setSpeciesModalOpen(false)
    setProgressModalOpen(true)
    setProgressState({
      status: 'processing',
      current: 0,
      total: selectedCount,
      message: `Updating species on ${selectedCount} photos...`,
    })

    const filenames = Array.from(selectedPhotos)

    const onProgress = (progress) => {
      setProgressState({
        status: 'processing',
        current: progress.processedCount,
        total: filenames.length,
        message: `Processing batch ${progress.currentBatch} of ${progress.totalBatches}...`,
      })
    }

    try {
      const result = await bulkUpdateSpecies(filenames, speciesData, onProgress)

      if (result.success.length > 0) {
        setProgressState({
          status: 'success',
          current: result.success.length,
          total: filenames.length,
          message: `Successfully updated ${result.success.length} photos`,
        })

        // Show undo toast
        if (result.previousState) {
          showUndoToast(`Updated species on ${result.success.length} photos`, async () => {
            for (const [filename, state] of Object.entries(result.previousState)) {
              await bulkUpdateSpecies([filename], state.species || null)
            }
            toast.success('Species restored')
          })
        }

        deselectAll()
      } else {
        setProgressState({
          status: 'error',
          current: 0,
          total: filenames.length,
          message: 'Failed to update any photos',
        })
      }
    } catch (error) {
      setProgressState({
        status: 'error',
        current: 0,
        total: filenames.length,
        message: error.message || 'An error occurred',
      })
    }
  }, [selectedPhotos, selectedCount, bulkUpdateSpecies, showUndoToast, deselectAll])

  const handleBulkDeleteConfirm = useCallback(async () => {
    setDeleteModalOpen(false)
    setProgressModalOpen(true)
    setProgressState({
      status: 'processing',
      current: 0,
      total: selectedCount,
      message: `Deleting ${selectedCount} photos...`,
    })

    const filenames = Array.from(selectedPhotos)

    const onProgress = (progress) => {
      setProgressState({
        status: 'processing',
        current: progress.processedCount,
        total: filenames.length,
        message: `Processing batch ${progress.currentBatch} of ${progress.totalBatches}...`,
      })
    }

    try {
      const result = await bulkDelete(filenames, onProgress)

      if (result.success.length > 0) {
        setProgressState({
          status: 'success',
          current: result.success.length,
          total: filenames.length,
          message: `Successfully deleted ${result.success.length} photos`,
        })

        // No undo for delete - it's permanent
        toast.success(`Deleted ${result.success.length} photos`)
        deselectAll()
        refetch() // Refresh photo list
      } else {
        setProgressState({
          status: 'error',
          current: 0,
          total: filenames.length,
          message: 'Failed to delete any photos',
        })
      }
    } catch (error) {
      setProgressState({
        status: 'error',
        current: 0,
        total: filenames.length,
        message: error.message || 'An error occurred',
      })
    }
  }, [selectedPhotos, selectedCount, bulkDelete, deselectAll, refetch])

  const handleBulkExport = useCallback(async (format) => {
    setExportModalOpen(false)
    setProgressModalOpen(true)
    setProgressOperation('export')

    const photoPaths = Array.from(selectedPhotos)
    await exportPhotos(photoPaths, format)
  }, [selectedPhotos, exportPhotos])

  // Toolbar action handlers
  const handleTagClick = useCallback(() => setTagModalOpen(true), [])
  const handleSpeciesClick = useCallback(() => setSpeciesModalOpen(true), [])
  const handleExportClick = useCallback(() => setExportModalOpen(true), [])
  const handleDeleteClick = useCallback(() => setDeleteModalOpen(true), [])

  if (isLoading) {
    return <div className="text-center py-12">{GALLERY_MESSAGES.LOADING.INITIAL}</div>
  }

  // Only show full error screen if initial load failed (no photos loaded)
  if (isError && photos.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">
          {formatErrorMessage(error, GALLERY_MESSAGES.ERROR.INITIAL, GALLERY_MESSAGES.ERROR.FALLBACK)}
        </div>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Retry loading photos"
        >
          {isLoading ? 'Retrying...' : 'Retry'}
        </button>
      </div>
    )
  }

  return (
    <div className="flex gap-6">
      {/* Filter Drawer (desktop: always visible, mobile/tablet: toggleable) */}
      <ErrorBoundary
        fallback={({ onClose }) => (
          <FilterErrorFallback onRetry={onClose} />
        )}
      >
        <FilterDrawer />
      </ErrorBoundary>

      {/* Main Gallery Content */}
      <div className="flex-1 space-y-6">
        {/* Header with title and view mode toggle */}
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">Photo Gallery</h2>
          <div className="flex items-center gap-3">
            <FilterDrawerToggle />
            <SelectModeToggle />
            <ViewModeToggle
              currentView={viewMode}
              onViewChange={setViewMode}
              isLoading={isLoadingPreference}
            />
            {/* Link to full-screen map page */}
            {totalWithGps > 0 && (
              <Link
                to="/gallery/map"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                aria-label="Open full-screen map view"
              >
                <ArrowTopRightOnSquareIcon className="w-5 h-5" aria-hidden="true" />
                <span className="text-sm font-medium">Full Map</span>
              </Link>
            )}
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex gap-2">
          <div className="flex-1">
            <SearchBar
              value={searchQuery}
              onChange={setSearchQuery}
              onClear={() => setSearchQuery('')}
              isLoading={isSearching}
            />
          </div>
          <button
            type="button"
            onClick={() => setShowAdvancedSearch(true)}
            aria-label="Advanced search"
            className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <AdjustmentsHorizontalIcon className="w-5 h-5 text-gray-600" />
            <span className="text-sm font-medium text-gray-700">Advanced</span>
          </button>
        </div>

        {/* Active Filter Chips */}
        <ActiveFilterChips />

        {/* Series API error warning with retry */}
        {isSeriesError && (
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-yellow-700">
                Photo series not available. Displaying all photos individually.
              </p>
              <button
                onClick={() => refetchSeries()}
                className="text-sm text-yellow-700 underline hover:text-yellow-800"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Screen reader announcements for loading states */}
        <div aria-live="polite" aria-atomic="true" className="sr-only">
          {isLoading && GALLERY_MESSAGES.LOADING.INITIAL}
          {isError && photos.length === 0 && formatErrorMessage(error, GALLERY_MESSAGES.ERROR.INITIAL, GALLERY_MESSAGES.ERROR.FALLBACK)}
          {isError && photos.length > 0 && formatErrorMessage(error, GALLERY_MESSAGES.ERROR.PAGINATION, GALLERY_MESSAGES.ERROR.FALLBACK)}
          {!hasNextPage && photos.length > 0 && !isError && GALLERY_MESSAGES.END}
          {isFetchingNextPage && GALLERY_MESSAGES.LOADING.MORE}
        </div>

        {photos.length === 0 && !isSearchActive && (
          <EmptyStateMessage variant="first-time" onCtaClick={() => navigate('/camera')} />
        )}

        {/* Search Results or Normal Gallery */}
        {isSearchActive ? (
          /* Search Results View */
          <div className="space-y-4">
            {/* Search Results Header */}
            <div className="flex justify-between items-center">
              <p className="text-sm text-gray-600">
                {searchTotal === 0 ? (
                  hasFilters ? 'No photos match the selected filters' : 'No results found'
                ) : searchTotal === 1 ? (
                  hasFilters && !searchQuery ? (
                    `1 photo matches the selected filters`
                  ) : (
                    `1 result${hasFilters ? ' with filters' : ''}`
                  )
                ) : (
                  hasFilters && !searchQuery ? (
                    `${searchTotal} photos match the selected filters`
                  ) : (
                    `${searchTotal} results${hasFilters ? ' with filters' : ''}`
                  )
                )}
                {tookMs > 0 && <span className="ml-2 text-gray-400">({tookMs}ms)</span>}
              </p>
            </div>

            {/* Search Results Grid */}
            {searchResults.length > 0 ? (
              <div data-testid="photo-grid" className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-4 ${GALLERY_CONFIG.LAYOUT.GRID_GAP}`}>
                {searchResults.map((result, index) => (
                  <SearchResultItem
                    key={result.path}
                    result={result}
                    onClick={isSelectMode ? undefined : setSelectedPhoto}
                    index={index}
                    results={searchResults}
                  />
                ))}
              </div>
            ) : combinedQuery.trim().length > 0 && !isSearching ? (
              <div className="text-center py-12 text-gray-500">
                <p>
                  {hasFilters && !searchQuery
                    ? 'No photos match the selected filters'
                    : searchQuery
                    ? `No results found for "${searchQuery}"`
                    : 'No results found'}
                </p>
                <p className="text-sm mt-2">
                  {hasFilters
                    ? 'Try adjusting or clearing filters'
                    : 'Try different keywords or use advanced search'}
                </p>
              </div>
            ) : null}
          </div>
        ) : (
          /* Normal Gallery View */
          <>
            {/* Conditional rendering: Grid view, Virtualized Grid, List view, or Map view */}
            {viewMode === 'map' ? (
              /* Map View */
              <div className="h-[600px] rounded-lg overflow-hidden">
                <MapView
                  locations={unclustered}
                  clusters={clusters}
                  clusterSettings={clusterSettings}
                  onClusterEnabledChange={setClusterEnabled}
                  onClusterRadiusChange={setClusterRadius}
                  onPhotoClick={handleMapPhotoClick}
                  isLoading={isLoadingLocations}
                />
              </div>
            ) : viewMode === 'grid' ? (
              shouldUseVirtualization ? (
                /* Virtualized Photo Grid (for large galleries) - wrapped in ErrorBoundary */
                <ErrorBoundary
                  fallback={({ error, resetErrorBoundary }) => (
                    <div className="py-12">
                      <EmptyStateMessage
                        variant="error"
                        onCtaClick={resetErrorBoundary}
                      />
                      {/* Show technical error details in development */}
                      {import.meta.env.DEV && error && (
                        <details className="mt-4 text-sm text-gray-600 max-w-2xl mx-auto">
                          <summary className="cursor-pointer font-semibold">Error Details</summary>
                          <pre className="mt-2 p-4 bg-gray-100 rounded overflow-auto">
                            {error.message}
                            {error.stack && `\n\n${error.stack}`}
                          </pre>
                        </details>
                      )}
                    </div>
                  )}
                  onReset={() => {
                    // Reset selected photo and re-fetch photos
                    setSelectedPhoto(null)
                    refetch()
                  }}
                >
                  <VirtualPhotoGrid
                    photos={photos}
                    onPhotoClick={handlePhotoClick}
                    isLoading={isLoading}
                    isFetchingNextPage={isFetchingNextPage}
                    hasNextPage={hasNextPage}
                    viewMode={viewMode}
                    scrollRef={scrollRef}
                  />
                </ErrorBoundary>
              ) : (
                /* Traditional Photo Grid (for smaller galleries) */
                <div data-testid="photo-grid" className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-4 ${GALLERY_CONFIG.LAYOUT.GRID_GAP}`}>
                  {displayPhotos.map((photo, index) => {
                    const series = seriesLookup.get(photo.path)

                    // If this photo is a series cover, render as StackedPhotoCard
                    if (series && series.cover_photo === photo.path) {
                      return (
                        <StackedPhotoCard
                          key={photo.path}
                          series={series}
                          onPhotoClick={isSelectMode ? undefined : (photo) => handleSeriesPhotoClick(photo, series)}
                        />
                      )
                    }

                    // Regular single photo
                    return (
                      <PhotoGridItem
                        key={photo.path}
                        photo={photo}
                        onClick={isSelectMode ? undefined : setSelectedPhoto}
                        index={index}
                        photos={displayPhotos}
                      />
                    )
                  })}

                  {/* Skeleton loading cards while fetching next page */}
                  {isFetchingNextPage &&
                    Array.from({ length: GALLERY_CONFIG.SKELETON_COUNT }).map((_, i) => (
                      <PhotoSkeleton key={`skeleton-${i}`} aria-hidden="true" />
                    ))}
                </div>
              )
            ) : (
              /* Photo List - show ALL photos, not filtered displayPhotos */
              <div className="flex flex-col gap-4">
                {photos.map((photo, index) => (
                  <PhotoListItem
                    key={photo.path}
                    photo={photo}
                    onClick={isSelectMode ? undefined : setSelectedPhoto}
                    index={index}
                    photos={photos}
                  />
                ))}
              </div>
            )}

            {/* Pagination error message (shows error but keeps photos visible) - not shown in map view */}
            {viewMode !== 'map' && isError && photos.length > 0 && (
              <div className="text-center py-4">
                <div className="text-red-600 mb-2">
                  {formatErrorMessage(error, GALLERY_MESSAGES.ERROR.PAGINATION, GALLERY_MESSAGES.ERROR.FALLBACK)}
                </div>
                <button
                  onClick={() => fetchNextPage()}
                  disabled={isFetchingNextPage}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  aria-label="Retry loading more photos"
                >
                  {isFetchingNextPage ? 'Retrying...' : 'Try Again'}
                </button>
              </div>
            )}

            {/* Infinite scroll sentinel - not shown in map view */}
            {viewMode !== 'map' && <div ref={sentinelRef} className={GALLERY_CONFIG.INFINITE_SCROLL.SENTINEL_HEIGHT} />}

            {/* End of photos indicator - not shown in map view */}
            {viewMode !== 'map' && !hasNextPage && photos.length > 0 && !isError && (
              <div className="text-center py-8 text-gray-500">
                {GALLERY_MESSAGES.END}
              </div>
            )}
          </>
        )}

        {/* Photo Lightbox with Navigation (wrapped in ErrorBoundary with custom fallback) */}
        <ErrorBoundary
          fallback={({ error, onClose }) => (
            <LightboxErrorFallback error={error} onClose={onClose} />
          )}
          onReset={handleCloseLightbox}
        >
          <PhotoLightbox
            photo={selectedPhoto}
            photos={lightboxPhotos}
            onClose={handleCloseLightbox}
            onNavigate={handleNavigate}
          />
        </ErrorBoundary>

        {/* Bulk Actions Toolbar (fixed at bottom when photos selected) */}
        <BulkActionsToolbar
          selectedCount={selectedCount}
          onTagClick={handleTagClick}
          onSpeciesClick={handleSpeciesClick}
          onExportClick={handleExportClick}
          onDeleteClick={handleDeleteClick}
          onDeselectAll={deselectAll}
        />

        {/* Bulk Tag Modal */}
        <BulkTagModal
          isOpen={tagModalOpen}
          onClose={() => setTagModalOpen(false)}
          onApply={handleBulkTagApply}
          selectedCount={selectedCount}
        />

        {/* Bulk Species Modal */}
        <BulkSpeciesModal
          isOpen={speciesModalOpen}
          onClose={() => setSpeciesModalOpen(false)}
          onApply={handleBulkSpeciesApply}
          selectedCount={selectedCount}
        />

        {/* Bulk Delete Confirmation Modal */}
        <BulkDeleteConfirmModal
          isOpen={deleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
          onConfirm={handleBulkDeleteConfirm}
          selectedPhotos={Array.from(selectedPhotos)}
        />

        {/* Bulk Export Modal */}
        <BulkExportModal
          isOpen={exportModalOpen}
          onClose={() => setExportModalOpen(false)}
          onExport={handleBulkExport}
          selectedCount={selectedCount}
          isLoading={isExporting}
          error={exportError}
        />

        {/* Bulk Progress Modal */}
        <BulkProgressModal
          isOpen={progressModalOpen}
          status={currentProgressState?.status}
          current={currentProgressState?.current}
          total={currentProgressState?.total}
          message={currentProgressState?.message}
          downloadUrl={currentProgressState?.downloadUrl}
          operation={progressOperation || 'tag'}
          onClose={() => {
            setProgressModalOpen(false)
            setProgressOperation(null)
          }}
        />

        {/* Advanced Search Modal */}
        {showAdvancedSearch && (
          <AdvancedSearchBuilder
            onQueryChange={(query) => {
              setSearchQuery(query)
              setShowAdvancedSearch(false)
            }}
            onClose={() => setShowAdvancedSearch(false)}
            initialQuery={searchQuery}
          />
        )}
      </div>
    </div>
  )
}

/**
 * Gallery page wrapper with SelectionProvider
 */
export default function Gallery() {
  return (
    <SelectionProvider>
      <GalleryContent />
    </SelectionProvider>
  )
}
