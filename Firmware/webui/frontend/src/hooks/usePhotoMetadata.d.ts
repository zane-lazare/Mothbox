/**
 * Type declarations for usePhotoMetadata.js
 *
 * Provides TypeScript types during the gradual migration.
 * IMPORTANT: Keep in sync with usePhotoMetadata.js.
 */

import { UseQueryResult } from '@tanstack/react-query'

interface PhotoMetadata {
  camera?: {
    make?: string
    model?: string
    lens_make?: string
    lens_model?: string
  }
  iso?: number
  aperture?: number
  shutter_speed?: number
  focal_length?: number
  exposure_mode?: string
  metering_mode?: string
  capture?: Record<string, unknown>
  file?: Record<string, unknown>
  gps?: Record<string, unknown>
  [key: string]: unknown
}

declare function usePhotoMetadata(photoPath: string | null | undefined): UseQueryResult<PhotoMetadata>
export default usePhotoMetadata
