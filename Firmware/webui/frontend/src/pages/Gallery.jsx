import { useInfiniteQuery } from '@tanstack/react-query'
import { getPhotosPaginated, getThumbnailUrl, getPhotoUrl } from '../utils/api'
import { QUERY_KEYS } from '../utils/queryKeys'
import { useState } from 'react'
import { useInfiniteScroll } from '../hooks/useInfiniteScroll'
import PhotoSkeleton from '../components/PhotoSkeleton'

export default function Gallery() {
  const [selectedPhoto, setSelectedPhoto] = useState(null)

  // Infinite query for paginated photos
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
  } = useInfiniteQuery({
    queryKey: QUERY_KEYS.PHOTOS_INFINITE,
    queryFn: ({ pageParam = 0 }) =>
      getPhotosPaginated({
        limit: 9,
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
  })

  // Flatten all pages into single photo array
  const photos = data?.pages.flatMap((page) => page.photos) ?? []

  if (isLoading) {
    return <div className="text-center py-12">Loading gallery...</div>
  }

  // Only show full error screen if initial load failed (no photos loaded)
  if (isError && photos.length === 0) {
    return (
      <div className="text-center py-12 text-red-600">
        Error loading photos: {error?.message || 'Unknown error'}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Photo Gallery</h2>

      {photos.length === 0 && (
        <div className="text-center py-12 text-gray-500">No photos yet</div>
      )}

      {/* Photo Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {photos.map((photo) => (
          <div
            key={photo.path}
            className="cursor-pointer group relative"
            onClick={() => setSelectedPhoto(photo)}
          >
            <img
              src={getThumbnailUrl(photo.path)}
              alt={photo.filename}
              className="w-full h-32 object-cover rounded-lg shadow hover:shadow-lg transition-shadow"
            />
            <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all rounded-lg flex items-center justify-center">
              <span className="text-white opacity-0 group-hover:opacity-100 text-sm">
                View
              </span>
            </div>
          </div>
        ))}

        {/* Skeleton loading cards while fetching next page */}
        {isFetchingNextPage &&
          Array.from({ length: 9 }).map((_, i) => (
            <PhotoSkeleton key={`skeleton-${i}`} />
          ))}
      </div>

      {/* Pagination error message (shows error but keeps photos visible) */}
      {isError && photos.length > 0 && (
        <div className="text-center py-4 text-red-600">
          Error loading more photos: {error?.message || 'Unknown error'}
        </div>
      )}

      {/* Infinite scroll sentinel */}
      <div ref={sentinelRef} className="h-20" />

      {/* End of photos indicator */}
      {!hasNextPage && photos.length > 0 && !isError && (
        <div className="text-center py-8 text-gray-500">
          No more photos to load
        </div>
      )}

      {/* Lightbox Modal */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedPhoto(null)}
        >
          <div className="max-w-6xl max-h-full">
            <img
              src={getPhotoUrl(selectedPhoto.path)}
              alt={selectedPhoto.filename}
              className="max-w-full max-h-screen object-contain"
              onClick={(e) => e.stopPropagation()}
            />
            <div className="text-white text-center mt-4">
              <p className="font-semibold">{selectedPhoto.filename}</p>
              <p className="text-sm text-gray-300">
                {new Date(selectedPhoto.date).toLocaleString()}
              </p>
              <p className="text-xs text-gray-400">
                {(selectedPhoto.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
