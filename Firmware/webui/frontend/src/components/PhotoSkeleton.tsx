import React from 'react'
import { GALLERY_CONFIG } from '../constants/config'

export interface PhotoSkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

/**
 * PhotoSkeleton - Skeleton loading component for photo cards
 *
 * Displays an animated placeholder while photos are loading in the gallery.
 * Matches the dimensions and layout of actual photo cards for smooth transitions.
 */
export default function PhotoSkeleton({ ...props }: PhotoSkeletonProps) {
  return (
    <div
      data-testid="photo-skeleton"
      className={`relative rounded-lg overflow-hidden bg-gray-200 animate-pulse ${GALLERY_CONFIG.LAYOUT.PHOTO_HEIGHT}`}
      role="status"
      aria-busy="true"
      aria-label="Loading photo..."
      {...props}
    >
      {/* Skeleton image placeholder */}
      <div className="w-full h-full bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 bg-[length:200%_100%] animate-shimmer" />

      {/* Optional: Add a faint icon to indicate loading */}
      <div className="absolute inset-0 flex items-center justify-center">
        <svg
          className="w-8 h-8 text-gray-400 opacity-30"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
      </div>
    </div>
  )
}
