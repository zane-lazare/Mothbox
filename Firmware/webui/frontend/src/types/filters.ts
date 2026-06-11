/**
 * Filter types for gallery and search
 */

export interface DateRangeFilter {
  preset: 'today' | '7days' | '30days' | '90days' | 'thisMonth' | 'lastMonth' | 'thisYear' | 'custom' | null
  startDate: string | null
  endDate: string | null
}

export interface TagFilter {
  selected: string[]
  matchMode: 'any' | 'all'
}

export interface SpeciesFilter {
  selected: string[]
  includeUnidentified: boolean
}

export interface CameraSettingsFilter {
  iso: { min: number | null; max: number | null }
  aperture: { min: number | null; max: number | null }
  shutterSpeed: { min: number | null; max: number | null }
}

export interface NotesFilter {
  hasNotes: boolean | null
  keywords: string
}

export interface FileTypeFilter {
  selected: string[]
}

export interface CustomFieldsFilter {
  [key: string]: string
}

export interface FilterState {
  dateRange: DateRangeFilter
  tags: TagFilter
  species: SpeciesFilter
  fileTypes: FileTypeFilter
  cameraSettings: CameraSettingsFilter
  notes: NotesFilter
  customFields: CustomFieldsFilter
}

export interface FilterPreset {
  name: string
  description?: string
  filters: Partial<FilterState>
  is_builtin: boolean
}
