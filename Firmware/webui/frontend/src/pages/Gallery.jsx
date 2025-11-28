import { useInfiniteQuery } from '@tanstack/react-query'
import { getPhotosPaginated } from '../utils/api'
import { QUERY_KEYS } from '../utils/queryKeys'
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useInfiniteScroll } from '../hooks/useInfiniteScroll'
import { useViewMode } from '../hooks/useViewMode'
import { useSeries } from '../hooks/useSeries'
import useScrollRestoration from '../hooks/useScrollRestoration'
import PhotoSkeleton from '../components/PhotoSkeleton'
import PhotoGridItem from '../components/PhotoGridItem'
import PhotoListItem from '../components/PhotoListItem'
import StackedPhotoCard from '../components/StackedPhotoCard'
import VirtualPhotoGrid from '../components/VirtualPhotoGrid'
import PhotoLightbox from '../components/PhotoLightbox'
import ErrorBoundary from '../components/ErrorBoundary'
import LightboxErrorFallback from '../components/LightboxErrorFallback'
import ViewModeToggle from '../components/ViewModeToggle'
import EmptyStateMessage from '../components/EmptyStateMessage'
import { GALLERY_CONFIG, GALLERY_MESSAGES } from '../constants/config'
import { formatErrorMessage } from '../utils/helpers'
import toast from 'react-hot-toast'

export default function Gallery() {
  const [selectedPhoto, setSelectedPhoto] = useState(null)
  const { viewMode, setViewMode, isLoading: isLoadingPreference } = useViewMode()
  const navigate = useNavigate()

  // Scroll restoration for virtualized grid
  const { scrollRef, saveScrollPosition } = useScrollRestoration('gallery-main')

  // State tracking for toast notifications (prevent duplicates)
  const [hasShownInitialErrorToast, setHasShownInitialErrorToast] = useState(false)
  const [hasShownEndToast, setHasShownEndToast] = useState(false)
  const [hasShownSeriesErrorToast, setHasShownSeriesErrorToast] = useState(false)
  const prevPaginationError = useRef(null)

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
  const { data: seriesData, isError: isSeriesError } = useSeries()

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

  // Determine if virtualization should be enabled
  const shouldUseVirtualization = useMemo(() => {
    return (
      GALLERY_CONFIG.VIRTUALIZATION.ENABLED &&
      viewMode === 'grid' &&
      photos.length >= GALLERY_CONFIG.VIRTUALIZATION.MIN_PHOTOS_FOR_VIRTUALIZATION
    )
  }, [viewMode, photos.length])

  // Memoized callbacks to prevent unnecessary re-renders
  const handleCloseLightbox = useCallback(() => setSelectedPhoto(null), [])
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
  // Handle series card click - open lightbox with cover photo
  const handleSeriesPhotoClick = useCallback((photo) => {
    saveScrollPosition()
    setSelectedPhoto(photo)
  }, [saveScrollPosition])

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
    <div className="space-y-6">
      {/* Header with title and view mode toggle */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Photo Gallery</h2>
        <ViewModeToggle
          currentView={viewMode}
          onViewChange={setViewMode}
          isLoading={isLoadingPreference}
        />
      </div>

      {/* Screen reader announcements for loading states */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {isLoading && GALLERY_MESSAGES.LOADING.INITIAL}
        {isError && photos.length === 0 && formatErrorMessage(error, GALLERY_MESSAGES.ERROR.INITIAL, GALLERY_MESSAGES.ERROR.FALLBACK)}
        {isError && photos.length > 0 && formatErrorMessage(error, GALLERY_MESSAGES.ERROR.PAGINATION, GALLERY_MESSAGES.ERROR.FALLBACK)}
        {!hasNextPage && photos.length > 0 && !isError && GALLERY_MESSAGES.END}
        {isFetchingNextPage && GALLERY_MESSAGES.LOADING.MORE}
      </div>

      {photos.length === 0 && (
        <EmptyStateMessage variant="first-time" onCtaClick={() => navigate('/camera')} />
      )}

      {/* Conditional rendering: Grid view, Virtualized Grid, or List view */}
      {viewMode === 'grid' ? (
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
          <div className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-4 ${GALLERY_CONFIG.LAYOUT.GRID_GAP}`}>
            {displayPhotos.map((photo) => {
              const series = seriesLookup.get(photo.path)

              // If this photo is a series cover, render as StackedPhotoCard
              if (series && series.cover_photo === photo.path) {
                return (
                  <StackedPhotoCard
                    key={photo.path}
                    series={series}
                    onPhotoClick={handleSeriesPhotoClick}
                  />
                )
              }

              // Regular single photo
              return (
                <PhotoGridItem key={photo.path} photo={photo} onClick={setSelectedPhoto} />
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
        /* Photo List */
        <div className="flex flex-col gap-4">
          {photos.map((photo) => (
            <PhotoListItem key={photo.path} photo={photo} onClick={setSelectedPhoto} />
          ))}
        </div>
      )}

      {/* Pagination error message (shows error but keeps photos visible) */}
      {isError && photos.length > 0 && (
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

      {/* Infinite scroll sentinel */}
      <div ref={sentinelRef} className={GALLERY_CONFIG.INFINITE_SCROLL.SENTINEL_HEIGHT} />

      {/* End of photos indicator */}
      {!hasNextPage && photos.length > 0 && !isError && (
        <div className="text-center py-8 text-gray-500">
          {GALLERY_MESSAGES.END}
        </div>
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
          photos={photos}
          onClose={handleCloseLightbox}
          onNavigate={handleNavigate}
        />
      </ErrorBoundary>
    </div>
  )
}
