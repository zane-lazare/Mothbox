import { useInfiniteQuery } from '@tanstack/react-query'
import { getPhotosPaginated } from '../utils/api'
import { QUERY_KEYS } from '../utils/queryKeys'
import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useInfiniteScroll } from '../hooks/useInfiniteScroll'
import { useViewMode } from '../hooks/useViewMode'
import PhotoSkeleton from '../components/PhotoSkeleton'
import PhotoGridItem from '../components/PhotoGridItem'
import PhotoListItem from '../components/PhotoListItem'
import PhotoLightbox from '../components/PhotoLightbox'
import ErrorBoundary from '../components/ErrorBoundary'
import ViewModeToggle from '../components/ViewModeToggle'
import EmptyStateMessage from '../components/EmptyStateMessage'
import { GALLERY_CONFIG, GALLERY_MESSAGES } from '../constants/config'
import { formatErrorMessage } from '../utils/helpers'
import toast from 'react-hot-toast'

export default function Gallery() {
  const [selectedPhoto, setSelectedPhoto] = useState(null)
  const { viewMode, setViewMode, isLoading: isLoadingPreference } = useViewMode()
  const navigate = useNavigate()

  // State tracking for toast notifications (prevent duplicates)
  const [hasShownInitialErrorToast, setHasShownInitialErrorToast] = useState(false)
  const [hasShownEndToast, setHasShownEndToast] = useState(false)
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

  // Set up infinite scroll sentinel
  const sentinelRef = useInfiniteScroll({
    onLoadMore: fetchNextPage,
    hasMore: hasNextPage,
    isLoading: isFetchingNextPage,
    threshold: GALLERY_CONFIG.INFINITE_SCROLL.THRESHOLD,
    rootMargin: GALLERY_CONFIG.INFINITE_SCROLL.ROOT_MARGIN,
  })

  // Note: Keyboard handling (Escape, Arrow keys) is now managed by PhotoLightbox component

  // Flatten all pages into single photo array
  const photos = data?.pages.flatMap((page) => page.photos) ?? []

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

      {/* Conditional rendering: Grid view or List view */}
      {viewMode === 'grid' ? (
        /* Photo Grid */
        <div className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-4 ${GALLERY_CONFIG.LAYOUT.GRID_GAP}`}>
          {photos.map((photo) => (
            <PhotoGridItem key={photo.path} photo={photo} onClick={setSelectedPhoto} />
          ))}

          {/* Skeleton loading cards while fetching next page */}
          {isFetchingNextPage &&
            Array.from({ length: GALLERY_CONFIG.SKELETON_COUNT }).map((_, i) => (
              <PhotoSkeleton key={`skeleton-${i}`} aria-hidden="true" />
            ))}
        </div>
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

      {/* Photo Lightbox with Navigation (wrapped in ErrorBoundary) */}
      <ErrorBoundary
        errorTitle="Lightbox Error"
        errorMessage="An error occurred while displaying the photo. Please try closing and reopening the lightbox."
        onReset={() => setSelectedPhoto(null)}
      >
        <PhotoLightbox
          photo={selectedPhoto}
          photos={photos}
          onClose={() => setSelectedPhoto(null)}
          onNavigate={(photo) => setSelectedPhoto(photo)}
        />
      </ErrorBoundary>
    </div>
  )
}
