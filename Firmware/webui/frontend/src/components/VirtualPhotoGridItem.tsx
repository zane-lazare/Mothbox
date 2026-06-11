import { memo } from 'react'
import type { Photo } from '@/types/domain'
import LazyImage from './LazyImage'

/**
 * VirtualPhotoGridItem - Individual photo item in virtual grid
 * Wrapper around LazyImage for grid-specific styling and behavior
 */

type ThumbnailSize = 64 | 128 | 256

interface VirtualPhotoGridItemProps {
  photo: Photo
  size?: ThumbnailSize
  onClick?: (photo: Photo) => void
}

const VirtualPhotoGridItem = memo(function VirtualPhotoGridItem({
  photo,
  size = 256,
  onClick
}: VirtualPhotoGridItemProps) {
  return (
    <div className="virtual-photo-grid-item group cursor-pointer">
      <LazyImage
        photo={photo}
        size={size}
        alt={photo.filename}
        onClick={onClick}
        className="rounded-lg overflow-hidden"
      />

      {/* Hover overlay */}
      <div className="
        absolute inset-0
        bg-black bg-opacity-0
        group-hover:bg-opacity-20
        transition-opacity duration-200
        pointer-events-none
      " />
    </div>
  )
})

export default VirtualPhotoGridItem
