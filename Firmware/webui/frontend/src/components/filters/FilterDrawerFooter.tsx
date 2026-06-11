import { FilterPresetManager } from './FilterPresetManager'

/**
 * FilterDrawerFooter Component
 *
 * Footer for the filter drawer. Integrates the FilterPresetManager
 * for saving, loading, and deleting filter presets.
 *
 * @component
 * @example
 * <FilterDrawerFooter />
 */
export function FilterDrawerFooter() {
  return (
    <FilterPresetManager />
  )
}

export default FilterDrawerFooter
