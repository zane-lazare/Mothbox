import { useQuery } from '@tanstack/react-query'
import { getPhotos, getThumbnailUrl, getPhotoUrl } from '../utils/api'
import { useState } from 'react'

export default function Gallery() {
  const [selectedPhoto, setSelectedPhoto] = useState(null)

  const { data: photos, isLoading } = useQuery({
    queryKey: ['photos'],
    queryFn: () => getPhotos().then(res => res.data.photos),
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading gallery...</div>
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Photo Gallery</h2>

      {photos && photos.length === 0 && (
        <div className="text-center py-12 text-gray-500">No photos yet</div>
      )}

      {/* Photo Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {photos?.map((photo) => (
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
      </div>

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
