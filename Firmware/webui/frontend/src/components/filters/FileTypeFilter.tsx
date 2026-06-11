import { useMemo, useCallback } from 'react'
import type { ForwardRefExoticComponent, SVGProps, RefAttributes } from 'react'
import {
  PhotoIcon,
  FilmIcon,
  DocumentIcon,
} from '@heroicons/react/24/outline'
import { useFilterContext } from '../../contexts/FilterContext'

type HeroIcon = ForwardRefExoticComponent<
  Omit<SVGProps<SVGSVGElement>, "ref"> & {
    title?: string
    titleId?: string
  } & RefAttributes<SVGSVGElement>
>

interface FileType {
  id: string
  label: string
  extensions: string[]
  Icon: HeroIcon
  color: string
}

// File type definitions with icons and extensions
const FILE_TYPES: FileType[] = [
  {
    id: 'jpg',
    label: 'JPG/JPEG',
    extensions: ['.jpg', '.jpeg'],
    Icon: PhotoIcon,
    color: 'text-blue-500',
  },
  {
    id: 'png',
    label: 'PNG',
    extensions: ['.png'],
    Icon: PhotoIcon,
    color: 'text-green-500',
  },
  {
    id: 'raw',
    label: 'RAW',
    extensions: ['.dng', '.cr2', '.nef', '.arw'],
    Icon: DocumentIcon,
    color: 'text-purple-500',
  },
  {
    id: 'video',
    label: 'Video',
    extensions: ['.mp4', '.mov', '.avi'],
    Icon: FilmIcon,
    color: 'text-red-500',
  },
]

/**
 * FileTypeFilter Component
 *
 * File type selection filter with multi-select checkboxes.
 * Integrates with FilterContext for state management.
 *
 * Features:
 * - Multi-select file type checkboxes (JPG, PNG, RAW, Video)
 * - Visual file type icons
 * - Selected types displayed with visual feedback
 * - No selection = all types shown (no filter applied)
 * - Client-side filtering (not in search index)
 *
 * @component
 * @example
 * <FilterSection id="fileTypes" title="File Types">
 *   <FileTypeFilter />
 * </FilterSection>
 */
export function FileTypeFilter() {
  const { fileTypes, setFileTypes } = useFilterContext()

  // Handle file type selection toggle
  const handleFileTypeToggle = useCallback((typeId: string) => {
    const isSelected = fileTypes.selected.includes(typeId)
    const newSelected = isSelected
      ? fileTypes.selected.filter(t => t !== typeId)
      : [...fileTypes.selected, typeId]

    setFileTypes(newSelected)
  }, [fileTypes, setFileTypes])

  // Check if any file types are selected
  const hasSelection = useMemo(() => {
    return fileTypes.selected.length > 0
  }, [fileTypes.selected])

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="text-xs text-gray-600 dark:text-gray-400">
        {hasSelection ? (
          <span>
            {fileTypes.selected.length} type{fileTypes.selected.length !== 1 ? 's' : ''} selected
          </span>
        ) : (
          <span>
            All file types shown
          </span>
        )}
      </div>

      {/* File Type Grid */}
      <div className="grid grid-cols-2 gap-3">
        {FILE_TYPES.map((fileType) => {
          const isSelected = fileTypes.selected.includes(fileType.id)
          const { Icon } = fileType

          return (
            <label
              key={fileType.id}
              className={`flex items-center gap-3 p-3 rounded-lg border-2
                       cursor-pointer group
                       transition-all duration-200
                       ${
                         isSelected
                           ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                           : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50'
                       }`}
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => handleFileTypeToggle(fileType.id)}
                className="h-4 w-4 rounded
                         border-gray-300 dark:border-gray-600
                         text-blue-600 dark:text-blue-500
                         focus:ring-blue-500 focus:ring-offset-0
                         cursor-pointer"
                aria-label={`Select file type ${fileType.label}`}
              />
              <div className="flex-1 flex items-center gap-2">
                <Icon
                  className={`h-5 w-5 ${
                    isSelected
                      ? fileType.color
                      : 'text-gray-400 dark:text-gray-500'
                  }`}
                  aria-hidden="true"
                />
                <span className={`text-sm font-medium ${
                  isSelected
                    ? 'text-gray-900 dark:text-gray-100'
                    : 'text-gray-700 dark:text-gray-300'
                }`}>
                  {fileType.label}
                </span>
              </div>
            </label>
          )
        })}
      </div>

      {/* Extensions Info */}
      {hasSelection && (
        <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
          <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
            <div className="font-medium text-gray-600 dark:text-gray-400 mb-2">
              Included extensions:
            </div>
            {FILE_TYPES.filter(ft => fileTypes.selected.includes(ft.id)).map(ft => (
              <div key={ft.id} className="flex items-center gap-2">
                <span className="font-medium text-gray-700 dark:text-gray-300">
                  {ft.label}:
                </span>
                <span>
                  {ft.extensions.join(', ')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default FileTypeFilter
