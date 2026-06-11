/**
 * Core domain types for Mothbox application
 */

// Photo and Gallery Types
export interface Photo {
  path: string
  filename: string
  timestamp: string
  thumbnail_url: string
  full_url: string
  metadata?: PhotoMetadata
  gps?: GPSData
  series_id?: string | null
  series_type?: 'hdr' | 'focus_bracket' | null
}

export interface PhotoMetadata {
  camera?: CameraInfo
  iso?: number
  aperture?: number
  shutter_speed?: number
  focal_length?: number
  exposure_mode?: string
  metering_mode?: string
  white_balance?: string
  tags?: string[]
  species?: string[]
  notes?: string
  custom_fields?: Record<string, string | number | boolean>
}

export interface CameraInfo {
  make?: string
  model?: string
  lens_make?: string
  lens_model?: string
}

export interface GPSData {
  latitude: number
  longitude: number
  altitude?: number
  precision?: number
}

// Series Detection
export interface PhotoSeries {
  id: string
  type: 'hdr' | 'focus_bracket'
  photos: Photo[]
  base_name: string
  count: number
}

// Location Clustering
export interface LocationCluster {
  centroid: { lat: number; lng: number }
  photo_count: number
  photos: Photo[]
  bounds: {
    min_lat: number
    max_lat: number
    min_lng: number
    max_lng: number
  }
}

// Deployment Types
export interface DeploymentMetadata {
  location: {
    latitude: number
    longitude: number
    altitude?: number
    description?: string
  }
  dates: {
    start_date: string
    end_date?: string
  }
  custom_fields?: Record<string, unknown>
}
