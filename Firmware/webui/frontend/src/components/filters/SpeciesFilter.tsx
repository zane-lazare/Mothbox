import { useState, useMemo, useCallback } from 'react'
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { useFilterContext } from '../../contexts/FilterContext'
import useSpecies from '../../hooks/useSpecies'
import TagChip from '../gallery/TagChip'

/**
 * SpeciesFilter Component
 *
 * Species selection filter with multi-select, search, and unidentified toggle.
 * Integrates with FilterContext for state management.
 *
 * Features:
 * - Multi-select species checkboxes
 * - Search/filter input to find species
 * - Selected species displayed as removable chips
 * - Toggle to include unidentified photos
 * - Loading, empty, and error states
 *
 * @component
 * @example
 * <FilterSection id="species" title="Species">
 *   <SpeciesFilter />
 * </FilterSection>
 */
export function SpeciesFilter() {
  const { species, setSpecies } = useFilterContext()
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch species from API
  const {
    species: availableSpecies,
    isLoading,
    isError,
    error,
  } = useSpecies()

  // Filter species based on search query
  const filteredSpecies = useMemo(() => {
    if (!searchQuery.trim()) return availableSpecies

    const query = searchQuery.toLowerCase().trim()
    return availableSpecies.filter(speciesItem =>
      speciesItem.name.toLowerCase().includes(query)
    )
  }, [availableSpecies, searchQuery])

  // Handle species selection toggle
  const handleSpeciesToggle = useCallback((speciesName: string) => {
    const isSelected = species.selected.includes(speciesName)
    const newSelected = isSelected
      ? species.selected.filter(s => s !== speciesName)
      : [...species.selected, speciesName]

    setSpecies(newSelected, species.includeUnidentified)
  }, [species, setSpecies])

  // Handle removing species from selected chips
  const handleRemoveSpecies = useCallback((speciesName: string) => {
    const newSelected = species.selected.filter(s => s !== speciesName)
    setSpecies(newSelected, species.includeUnidentified)
  }, [species, setSpecies])

  // Handle include unidentified toggle
  const handleUnidentifiedToggle = useCallback(() => {
    setSpecies(species.selected, !species.includeUnidentified)
  }, [species, setSpecies])

  // Handle search input change
  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value)
  }, [])

  // Clear search
  const handleClearSearch = useCallback(() => {
    setSearchQuery('')
  }, [])

  // Loading state
  if (isLoading) {
    return (
      <div className="p-4">
        <div className="flex items-center justify-center py-8">
          <div className="animate-pulse text-gray-500 dark:text-gray-400">
            Loading species...
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (isError) {
    return (
      <div className="p-4">
        <div className="text-sm text-red-600 dark:text-red-400">
          Failed to load species: {error?.message || 'Unknown error'}
        </div>
      </div>
    )
  }

  // Empty state - no species available
  if (availableSpecies.length === 0) {
    return (
      <div className="p-4">
        <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
          No species available
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      {/* Selected Species Chips */}
      {species.selected.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-gray-700 dark:text-gray-300">
            Selected ({species.selected.length})
          </div>
          <div className="flex flex-wrap gap-2">
            {species.selected.map(speciesName => (
              <TagChip
                key={speciesName}
                tag={speciesName}
                removable
                onRemove={() => handleRemoveSpecies(speciesName)}
                size="sm"
              />
            ))}
          </div>
        </div>
      )}

      {/* Include Unidentified Toggle */}
      <div className="pb-2 border-b border-gray-200 dark:border-gray-700">
        <label className="flex items-center gap-2 p-2 rounded cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-150">
          <input
            type="checkbox"
            checked={species.includeUnidentified}
            onChange={handleUnidentifiedToggle}
            className="h-4 w-4 rounded
                     border-gray-300 dark:border-gray-600
                     text-blue-600 dark:text-blue-500
                     focus:ring-blue-500 focus:ring-offset-0
                     cursor-pointer"
            aria-label="Include photos without species identification"
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">
            Include unidentified photos
          </span>
        </label>
      </div>

      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
          <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" aria-hidden="true" />
        </div>
        <input
          type="text"
          placeholder="Search species..."
          value={searchQuery}
          onChange={handleSearchChange}
          className="w-full pl-10 pr-10 py-2 text-sm
                   border border-gray-300 dark:border-gray-600
                   rounded-md
                   bg-white dark:bg-gray-800
                   text-gray-900 dark:text-gray-100
                   placeholder-gray-400 dark:placeholder-gray-500
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   transition-colors duration-150"
          aria-label="Search species"
        />
        {searchQuery && (
          <button
            type="button"
            onClick={handleClearSearch}
            className="absolute inset-y-0 right-0 flex items-center pr-3
                     text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="Clear search"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Species List */}
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {filteredSpecies.length === 0 ? (
          <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
            No species match &quot;{searchQuery}&quot;
          </div>
        ) : (
          filteredSpecies.map(speciesItem => {
            const isSelected = species.selected.includes(speciesItem.name)

            return (
              <label
                key={speciesItem.name}
                className="flex items-center gap-2 p-2 rounded
                         hover:bg-gray-50 dark:hover:bg-gray-700/50
                         cursor-pointer group
                         transition-colors duration-150"
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => handleSpeciesToggle(speciesItem.name)}
                  className="h-4 w-4 rounded
                           border-gray-300 dark:border-gray-600
                           text-blue-600 dark:text-blue-500
                           focus:ring-blue-500 focus:ring-offset-0
                           cursor-pointer"
                  aria-label={`Select species ${speciesItem.name}`}
                />
                <span className="flex-1 text-sm text-gray-700 dark:text-gray-300">
                  {speciesItem.name}
                </span>
                {speciesItem.count !== undefined && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {speciesItem.count}
                  </span>
                )}
              </label>
            )
          })
        )}
      </div>
    </div>
  )
}

export default SpeciesFilter
