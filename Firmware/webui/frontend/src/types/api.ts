/**
 * API types for request/response handling
 */

export interface ApiResponse<T> {
  data: T
  status: number
  message?: string
}

export interface ApiError {
  code: string
  error: string
  details?: Record<string, unknown>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

// Export Job Types
export interface ExportJob {
  id: string
  format: 'darwin_core' | 'inaturalist' | 'json' | 'csv'
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  created_at: string
  completed_at?: string
  error?: string
  result_path?: string
}

export interface ExportPreset {
  name: string
  description?: string
  format: ExportJob['format']
  filters?: Record<string, unknown>
  options?: Record<string, unknown>
  is_builtin: boolean
}
