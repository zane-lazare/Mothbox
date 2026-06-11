import {
  DocumentTextIcon,
  PhotoIcon,
  CodeBracketIcon,
  TableCellsIcon,
} from '@heroicons/react/24/outline'

type ExportFormat = 'darwin_core' | 'inaturalist' | 'json' | 'csv'

interface FormatOption {
  value: ExportFormat
  name: string
  description: string
  icon: typeof DocumentTextIcon
  features: string[]
}

const EXPORT_FORMATS: FormatOption[] = [
  {
    value: 'darwin_core',
    name: 'Darwin Core CSV',
    description: 'GBIF biodiversity standard format for occurrence records',
    icon: TableCellsIcon,
    features: [
      'GBIF/iDigBio compatible',
      'Standardized biodiversity fields',
      'Optional schema validation',
    ],
  },
  {
    value: 'inaturalist',
    name: 'iNaturalist Export',
    description: 'ZIP with photos and XMP sidecar metadata',
    icon: PhotoIcon,
    features: [
      'Photo bundle with metadata',
      'XMP sidecar files',
      'iNaturalist upload ready',
    ],
  },
  {
    value: 'json',
    name: 'JSON Export',
    description: 'Full metadata export with nested structure',
    icon: CodeBracketIcon,
    features: [
      'Complete metadata',
      'Nested data structure',
      'Optional raw EXIF',
    ],
  },
  {
    value: 'csv',
    name: 'CSV Export',
    description: 'Flat CSV with customizable columns',
    icon: DocumentTextIcon,
    features: [
      'Excel compatible',
      'Customizable delimiter',
      'UTF-8 with BOM support',
    ],
  },
]

export interface FormatSelectorProps {
  value?: string
  onChange: (format: ExportFormat) => void
  disabled?: boolean
}

export default function FormatSelector({ value, onChange, disabled = false }: FormatSelectorProps) {
  const handleKeyDown = (e: React.KeyboardEvent, format: ExportFormat) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault()
      if (!disabled) {
        onChange(format)
      }
    }
  }

  return (
    <div role="radiogroup" aria-label="Export format">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {EXPORT_FORMATS.map((format) => {
          const Icon = format.icon
          const isSelected = value === format.value

          return (
            <label
              key={format.value}
              htmlFor={`format-${format.value}`}
              className={`
                relative flex flex-col p-4 border-2 rounded-lg cursor-pointer
                transition-all duration-200
                ${isSelected
                  ? 'border-blue-500 ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
              `}
              data-selected={isSelected}
            >
              <div className="flex items-start gap-3">
                <input
                  type="radio"
                  id={`format-${format.value}`}
                  name="export-format"
                  value={format.value}
                  checked={isSelected}
                  onChange={() => !disabled && onChange(format.value)}
                  onKeyDown={(e) => handleKeyDown(e, format.value)}
                  disabled={disabled}
                  aria-describedby={`format-${format.value}-desc`}
                  className="mt-1 h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500
                            disabled:opacity-50 disabled:cursor-not-allowed"
                />

                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className="h-5 w-5 text-gray-600 dark:text-gray-400" aria-hidden="true" />
                    <span className="font-semibold text-gray-900 dark:text-gray-100">
                      {format.name}
                    </span>
                  </div>

                  <p
                    id={`format-${format.value}-desc`}
                    className="text-sm text-gray-600 dark:text-gray-400 mb-2"
                  >
                    {format.description}
                  </p>

                  <ul className="text-xs text-gray-500 dark:text-gray-500 space-y-1">
                    {format.features.map((feature, idx) => (
                      <li key={idx} className="flex items-center gap-1">
                        <span className="text-blue-500">•</span>
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </label>
          )
        })}
      </div>
    </div>
  )
}
