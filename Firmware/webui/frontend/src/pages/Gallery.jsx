import { useInfiniteQuery } from '@tanstack/react-query'
import { getPhotosPaginated, getThumbnailUrl, getPhotoUrl } from '../utils/api'
import { QUERY_KEYS } from '../utils/queryKeys'
import { useState, useEffect } from 'react'
import { useInfiniteScroll } from '../hooks/useInfiniteScroll'
import { useViewMode } from '../hooks/useViewMode'
import PhotoSkeleton from '../components/PhotoSkeleton'
import PhotoListItem from '../components/PhotoListItem'
import ViewModeToggle from '../components/ViewModeToggle'
import { GALLERY_CONFIG, GALLERY_MESSAGES } from '../constants/config'
import { formatErrorMessage } from '../utils/helpers'

export default function Gallery() {
  const [selectedPhoto, setSelectedPhoto] = useState(null)
  const { viewMode, setViewMode, isLoading: isLoadingPreference } = useViewMode()

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

  // Escape key handler for lightbox
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        setSelectedPhoto(null)
      }
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, []) // Empty deps - setSelectedPhoto is stable, no re-registration needed

  // Flatten all pages into single photo array
  const photos = data?.pages.flatMap((page) => page.photos) ?? []

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
        <div className="text-center py-12 text-gray-500">{GALLERY_MESSAGES.EMPTY}</div>
      )}

      {/* Conditional rendering: Grid view or List view */}
      {viewMode === 'grid' ? (
        /* Photo Grid */
        <div className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-4 ${GALLERY_CONFIG.LAYOUT.GRID_GAP}`}>
        {photos.map((photo) => (
          <button
            key={photo.path}
            className="cursor-pointer group relative focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg"
            onClick={() => setSelectedPhoto(photo)}
            aria-label={`View photo: ${photo.filename}, taken on ${new Date(photo.date).toLocaleString()}`}
          >
            <img
              src={getThumbnailUrl(photo.path)}
              alt={photo.filename}
              width={Math.round(GALLERY_CONFIG.THUMBNAIL.SIZE * GALLERY_CONFIG.THUMBNAIL.ASPECT_RATIO)}
              height={GALLERY_CONFIG.THUMBNAIL.SIZE}
              loading="lazy"
              onError={(e) => {
                // Fallback to gray placeholder on error (rate limit, missing file, etc.)
                e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23e5e7eb" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" fill="%239ca3af" font-size="14"%3EImage Error%3C/text%3E%3C/svg%3E';
                e.target.onerror = null; // Prevent infinite loop
              }}
              className={`w-full ${GALLERY_CONFIG.LAYOUT.PHOTO_HEIGHT} object-cover rounded-lg shadow hover:shadow-lg transition-shadow`}
            />
            <div className="absolute inset-0 bg-transparent group-hover:bg-black/30 group-focus:bg-black/30 transition-all rounded-lg flex items-center justify-center pointer-events-none">
              <span className="text-white opacity-0 group-hover:opacity-100 group-focus:opacity-100 text-sm">
                View
              </span>
            </div>
          </button>
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

      {/* Lightbox Modal */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="lightbox-title"
          onClick={() => setSelectedPhoto(null)}
        >
          <div className="relative max-w-6xl max-h-full">
            {/* Close button */}
            <button
              onClick={() => setSelectedPhoto(null)}
              className="absolute top-2 right-2 z-10 bg-white rounded-full p-2 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-lg"
              aria-label="Close lightbox"
            >
              <svg
                className="w-6 h-6 text-gray-800"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>

            <img
              src={getPhotoUrl(selectedPhoto.path)}
              alt={selectedPhoto.filename}
              loading="eager"
              className="max-w-full max-h-screen object-contain"
              onClick={(e) => e.stopPropagation()}
            />
            <div className="text-white text-center mt-4">
              <h2 id="lightbox-title" className="font-semibold text-lg">
                {selectedPhoto.filename}
              </h2>
              <p className="text-sm text-gray-300" aria-label="Photo date">
                Taken: {new Date(selectedPhoto.date).toLocaleString()}
              </p>
              <p className="text-xs text-gray-400" aria-label="File size">
                Size: {(selectedPhoto.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
