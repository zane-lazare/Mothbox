import { render, act } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import React from 'react'
import { FilterProvider, useFilterContext } from '../FilterContext'

// Test component to access context
function TestConsumer({ onContextReady }) {
  const ctx = useFilterContext()
  React.useEffect(() => {
    onContextReady(ctx)
  }, [ctx, onContextReady])
  return null
}

// Helper to render with provider
function renderWithProvider(ui) {
  return render(<FilterProvider>{ui}</FilterProvider>)
}

describe('FilterContext', () => {
  let ctx

  beforeEach(() => {
    ctx = null
  })

  const setupContext = () => {
    return new Promise((resolve) => {
      renderWithProvider(<TestConsumer onContextReady={(c) => { ctx = c; resolve() }} />)
    })
  }

  describe('Initial State', () => {
    it('should provide correct initial dateRange', async () => {
      await setupContext()
      expect(ctx.dateRange).toEqual({
        preset: null,
        startDate: null,
        endDate: null,
      })
    })

    it('should provide correct initial tags', async () => {
      await setupContext()
      expect(ctx.tags).toEqual({
        selected: [],
        matchMode: 'any',
      })
    })

    it('should provide correct initial species', async () => {
      await setupContext()
      expect(ctx.species).toEqual({
        selected: [],
        includeUnidentified: false,
      })
    })

    it('should provide correct initial fileTypes', async () => {
      await setupContext()
      expect(ctx.fileTypes).toEqual({
        selected: [],
      })
    })

    it('should provide correct initial cameraSettings', async () => {
      await setupContext()
      expect(ctx.cameraSettings).toEqual({
        iso: { min: null, max: null },
        aperture: { min: null, max: null },
        shutterSpeed: { min: null, max: null },
      })
    })

    it('should provide correct initial notes', async () => {
      await setupContext()
      expect(ctx.notes).toEqual({
        hasNotes: null,
        keywords: '',
      })
    })

    it('should provide correct initial customFields', async () => {
      await setupContext()
      expect(ctx.customFields).toEqual({})
    })

    it('should have isDrawerOpen true initially', async () => {
      await setupContext()
      expect(ctx.isDrawerOpen).toBe(true)
    })

    it('should have expandedSections with dateRange initially', async () => {
      await setupContext()
      expect(ctx.expandedSections).toEqual(['dateRange'])
    })

    it('should have activeFilterCount of 0 initially', async () => {
      await setupContext()
      expect(ctx.activeFilterCount).toBe(0)
    })

    it('should have hasActiveFilters false initially', async () => {
      await setupContext()
      expect(ctx.hasActiveFilters).toBe(false)
    })
  })

  describe('setDateRange action', () => {
    it('should set date preset', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange('7days', null, null)
      })

      expect(ctx.dateRange.preset).toBe('7days')
      expect(ctx.dateRange.startDate).toBe(null)
      expect(ctx.dateRange.endDate).toBe(null)
    })

    it('should set custom date range', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange('custom', '2024-01-01', '2024-01-31')
      })

      expect(ctx.dateRange.preset).toBe('custom')
      expect(ctx.dateRange.startDate).toBe('2024-01-01')
      expect(ctx.dateRange.endDate).toBe('2024-01-31')
    })

    it('should preserve date range when all undefined (use clearFilter to reset)', async () => {
      await setupContext()

      // Set a date range first
      act(() => {
        ctx.setDateRange('7days', undefined, undefined)
      })
      expect(ctx.dateRange.preset).toBe('7days')

      // Passing undefined preserves existing values
      act(() => {
        ctx.setDateRange(undefined, undefined, undefined)
      })

      expect(ctx.dateRange.preset).toBe('7days') // Preserved
      expect(ctx.dateRange.startDate).toBe(null) // Was already null
      expect(ctx.dateRange.endDate).toBe(null) // Was already null
    })

    it('should allow setting values to null explicitly', async () => {
      await setupContext()

      // Set a date range first
      act(() => {
        ctx.setDateRange('custom', '2024-01-01', '2024-01-31')
      })
      expect(ctx.dateRange.preset).toBe('custom')
      expect(ctx.dateRange.startDate).toBe('2024-01-01')
      expect(ctx.dateRange.endDate).toBe('2024-01-31')

      // Passing null explicitly clears the values
      act(() => {
        ctx.setDateRange(null, null, null)
      })

      expect(ctx.dateRange.preset).toBe(null)
      expect(ctx.dateRange.startDate).toBe(null)
      expect(ctx.dateRange.endDate).toBe(null)
    })

    it('should partially update date range (only preset)', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange('custom', '2024-01-01', '2024-01-31')
      })

      // Update only preset (use undefined to preserve other fields)
      act(() => {
        ctx.setDateRange('7days', undefined, undefined)
      })

      expect(ctx.dateRange.preset).toBe('7days')
      expect(ctx.dateRange.startDate).toBe('2024-01-01') // Preserved
      expect(ctx.dateRange.endDate).toBe('2024-01-31') // Preserved
    })
  })

  describe('setTags action', () => {
    it('should set selected tags', async () => {
      await setupContext()

      act(() => {
        ctx.setTags(['moth', 'butterfly'], undefined)
      })

      expect(ctx.tags.selected).toEqual(['moth', 'butterfly'])
      expect(ctx.tags.matchMode).toBe('any') // Preserved
    })

    it('should set match mode', async () => {
      await setupContext()

      act(() => {
        ctx.setTags(undefined, 'all')
      })

      expect(ctx.tags.selected).toEqual([]) // Preserved
      expect(ctx.tags.matchMode).toBe('all')
    })

    it('should set both selected tags and match mode', async () => {
      await setupContext()

      act(() => {
        ctx.setTags(['luna moth'], 'all')
      })

      expect(ctx.tags.selected).toEqual(['luna moth'])
      expect(ctx.tags.matchMode).toBe('all')
    })

    it('should preserve existing values when passed undefined', async () => {
      await setupContext()

      act(() => {
        ctx.setTags(['initial'], 'any')
      })

      act(() => {
        ctx.setTags(undefined, undefined)
      })

      expect(ctx.tags.selected).toEqual(['initial'])
      expect(ctx.tags.matchMode).toBe('any')
    })

    it('should allow setting values to null explicitly', async () => {
      await setupContext()

      act(() => {
        ctx.setTags(['initial'], 'all')
      })

      act(() => {
        ctx.setTags(null, null)
      })

      expect(ctx.tags.selected).toBe(null)
      expect(ctx.tags.matchMode).toBe(null)
    })
  })

  describe('setSpecies action', () => {
    it('should set selected species', async () => {
      await setupContext()

      act(() => {
        ctx.setSpecies(['Actias luna', 'Papilio glaucus'], undefined)
      })

      expect(ctx.species.selected).toEqual(['Actias luna', 'Papilio glaucus'])
      expect(ctx.species.includeUnidentified).toBe(false) // Preserved
    })

    it('should set includeUnidentified flag', async () => {
      await setupContext()

      act(() => {
        ctx.setSpecies(undefined, true)
      })

      expect(ctx.species.selected).toEqual([]) // Preserved
      expect(ctx.species.includeUnidentified).toBe(true)
    })

    it('should set both selected species and includeUnidentified', async () => {
      await setupContext()

      act(() => {
        ctx.setSpecies(['Danaus plexippus'], true)
      })

      expect(ctx.species.selected).toEqual(['Danaus plexippus'])
      expect(ctx.species.includeUnidentified).toBe(true)
    })

    it('should preserve existing values when passed undefined', async () => {
      await setupContext()

      act(() => {
        ctx.setSpecies(['initial species'], false)
      })

      act(() => {
        ctx.setSpecies(undefined, undefined)
      })

      expect(ctx.species.selected).toEqual(['initial species'])
      expect(ctx.species.includeUnidentified).toBe(false)
    })

    it('should allow setting values to null explicitly', async () => {
      await setupContext()

      act(() => {
        ctx.setSpecies(['initial species'], true)
      })

      act(() => {
        ctx.setSpecies(null, null)
      })

      expect(ctx.species.selected).toBe(null)
      expect(ctx.species.includeUnidentified).toBe(null)
    })
  })

  describe('setFileTypes action', () => {
    it('should set selected file types', async () => {
      await setupContext()

      act(() => {
        ctx.setFileTypes(['jpg', 'png'])
      })

      expect(ctx.fileTypes.selected).toEqual(['jpg', 'png'])
    })

    it('should update file types with new array', async () => {
      await setupContext()

      act(() => {
        ctx.setFileTypes(['jpg'])
      })

      act(() => {
        ctx.setFileTypes(['raw', 'video'])
      })

      expect(ctx.fileTypes.selected).toEqual(['raw', 'video'])
    })

    it('should handle empty array', async () => {
      await setupContext()

      act(() => {
        ctx.setFileTypes([])
      })

      expect(ctx.fileTypes.selected).toEqual([])
    })
  })

  describe('setCameraSettings action', () => {
    it('should set ISO range', async () => {
      await setupContext()

      act(() => {
        ctx.setCameraSettings({
          iso: { min: 100, max: 800 }
        })
      })

      expect(ctx.cameraSettings.iso).toEqual({ min: 100, max: 800 })
      expect(ctx.cameraSettings.aperture).toEqual({ min: null, max: null }) // Preserved
      expect(ctx.cameraSettings.shutterSpeed).toEqual({ min: null, max: null }) // Preserved
    })

    it('should set aperture range', async () => {
      await setupContext()

      act(() => {
        ctx.setCameraSettings({
          aperture: { min: 2.8, max: 5.6 }
        })
      })

      expect(ctx.cameraSettings.aperture).toEqual({ min: 2.8, max: 5.6 })
      expect(ctx.cameraSettings.iso).toEqual({ min: null, max: null }) // Preserved
    })

    it('should set shutter speed range', async () => {
      await setupContext()

      act(() => {
        ctx.setCameraSettings({
          shutterSpeed: { min: 1/1000, max: 1/60 }
        })
      })

      expect(ctx.cameraSettings.shutterSpeed).toEqual({ min: 1/1000, max: 1/60 })
    })

    it('should allow partial updates', async () => {
      await setupContext()

      // Set initial values
      act(() => {
        ctx.setCameraSettings({
          iso: { min: 100, max: 800 },
          aperture: { min: 2.8, max: 5.6 }
        })
      })

      // Update only ISO
      act(() => {
        ctx.setCameraSettings({
          iso: { min: 200, max: 1600 }
        })
      })

      expect(ctx.cameraSettings.iso).toEqual({ min: 200, max: 1600 })
      expect(ctx.cameraSettings.aperture).toEqual({ min: 2.8, max: 5.6 }) // Preserved
    })

    it('should set all camera settings at once', async () => {
      await setupContext()

      act(() => {
        ctx.setCameraSettings({
          iso: { min: 100, max: 800 },
          aperture: { min: 2.8, max: 5.6 },
          shutterSpeed: { min: 1/1000, max: 1/60 }
        })
      })

      expect(ctx.cameraSettings).toEqual({
        iso: { min: 100, max: 800 },
        aperture: { min: 2.8, max: 5.6 },
        shutterSpeed: { min: 1/1000, max: 1/60 }
      })
    })
  })

  describe('setNotes action', () => {
    it('should set hasNotes', async () => {
      await setupContext()

      act(() => {
        ctx.setNotes(true, undefined)
      })

      expect(ctx.notes.hasNotes).toBe(true)
      expect(ctx.notes.keywords).toBe('') // Preserved
    })

    it('should set keywords', async () => {
      await setupContext()

      act(() => {
        ctx.setNotes(undefined, 'specimen collected')
      })

      expect(ctx.notes.hasNotes).toBe(null) // Preserved
      expect(ctx.notes.keywords).toBe('specimen collected')
    })

    it('should set both hasNotes and keywords', async () => {
      await setupContext()

      act(() => {
        ctx.setNotes(false, 'no notes')
      })

      expect(ctx.notes.hasNotes).toBe(false)
      expect(ctx.notes.keywords).toBe('no notes')
    })

    it('should handle hasNotes false', async () => {
      await setupContext()

      act(() => {
        ctx.setNotes(false, undefined)
      })

      expect(ctx.notes.hasNotes).toBe(false)
    })

    it('should preserve existing values when passed undefined', async () => {
      await setupContext()

      act(() => {
        ctx.setNotes(true, 'initial')
      })

      act(() => {
        ctx.setNotes(undefined, undefined)
      })

      expect(ctx.notes.hasNotes).toBe(true)
      expect(ctx.notes.keywords).toBe('initial')
    })

    it('should allow setting values to null explicitly', async () => {
      await setupContext()

      act(() => {
        ctx.setNotes(true, 'initial')
      })

      act(() => {
        ctx.setNotes(null, null)
      })

      expect(ctx.notes.hasNotes).toBe(null)
      expect(ctx.notes.keywords).toBe(null)
    })
  })

  describe('setCustomField action', () => {
    it('should set custom field value', async () => {
      await setupContext()

      act(() => {
        ctx.setCustomField('location', 'Forest Edge')
      })

      expect(ctx.customFields.location).toBe('Forest Edge')
    })

    it('should set multiple custom fields', async () => {
      await setupContext()

      act(() => {
        ctx.setCustomField('location', 'Forest Edge')
        ctx.setCustomField('weather', 'Clear')
        ctx.setCustomField('temperature', '22C')
      })

      expect(ctx.customFields).toEqual({
        location: 'Forest Edge',
        weather: 'Clear',
        temperature: '22C'
      })
    })

    it('should update existing custom field', async () => {
      await setupContext()

      act(() => {
        ctx.setCustomField('location', 'Forest Edge')
      })

      act(() => {
        ctx.setCustomField('location', 'Mountain Trail')
      })

      expect(ctx.customFields.location).toBe('Mountain Trail')
    })

    it('should clear custom field when set to empty/null value', async () => {
      await setupContext()

      act(() => {
        ctx.setCustomField('location', 'Forest Edge')
      })

      act(() => {
        ctx.setCustomField('location', '')
      })

      expect(ctx.customFields.location).toBe('')
    })
  })

  describe('clearFilter action', () => {
    it('should clear dateRange filter', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange('7days', '2024-01-01', '2024-01-31')
      })
      expect(ctx.dateRange.preset).toBe('7days')

      act(() => {
        ctx.clearFilter('dateRange')
      })

      expect(ctx.dateRange).toEqual({
        preset: null,
        startDate: null,
        endDate: null,
      })
    })

    it('should clear tags filter', async () => {
      await setupContext()

      act(() => {
        ctx.setTags(['moth', 'butterfly'], 'all')
      })

      act(() => {
        ctx.clearFilter('tags')
      })

      expect(ctx.tags).toEqual({
        selected: [],
        matchMode: 'any',
      })
    })

    it('should clear species filter', async () => {
      await setupContext()

      act(() => {
        ctx.setSpecies(['Actias luna'], true)
      })

      act(() => {
        ctx.clearFilter('species')
      })

      expect(ctx.species).toEqual({
        selected: [],
        includeUnidentified: false,
      })
    })

    it('should clear fileTypes filter', async () => {
      await setupContext()

      act(() => {
        ctx.setFileTypes(['jpg', 'png'])
      })

      act(() => {
        ctx.clearFilter('fileTypes')
      })

      expect(ctx.fileTypes).toEqual({
        selected: [],
      })
    })

    it('should clear cameraSettings filter', async () => {
      await setupContext()

      act(() => {
        ctx.setCameraSettings({
          iso: { min: 100, max: 800 },
          aperture: { min: 2.8, max: 5.6 }
        })
      })

      act(() => {
        ctx.clearFilter('cameraSettings')
      })

      expect(ctx.cameraSettings).toEqual({
        iso: { min: null, max: null },
        aperture: { min: null, max: null },
        shutterSpeed: { min: null, max: null },
      })
    })

    it('should clear notes filter', async () => {
      await setupContext()

      act(() => {
        ctx.setNotes(true, 'some keywords')
      })

      act(() => {
        ctx.clearFilter('notes')
      })

      expect(ctx.notes).toEqual({
        hasNotes: null,
        keywords: '',
      })
    })

    it('should clear customFields filter', async () => {
      await setupContext()

      act(() => {
        ctx.setCustomField('location', 'Forest')
        ctx.setCustomField('weather', 'Clear')
      })

      act(() => {
        ctx.clearFilter('customFields')
      })

      expect(ctx.customFields).toEqual({})
    })

    it('should not affect other filters when clearing one', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange('7days', null, null)
        ctx.setTags(['moth'], null)
        ctx.setSpecies(['Actias luna'], null)
      })

      act(() => {
        ctx.clearFilter('tags')
      })

      expect(ctx.dateRange.preset).toBe('7days') // Preserved
      expect(ctx.tags.selected).toEqual([]) // Cleared
      expect(ctx.species.selected).toEqual(['Actias luna']) // Preserved
    })

    it('should handle invalid filter type gracefully', async () => {
      await setupContext()

      act(() => {
        ctx.setTags(['moth'], null)
      })

      act(() => {
        ctx.clearFilter('nonexistentFilter')
      })

      // State should be unchanged
      expect(ctx.tags.selected).toEqual(['moth'])
    })
  })

  describe('clearAllFilters action', () => {
    it('should reset all filters to initial state', async () => {
      await setupContext()

      // Set all filters
      act(() => {
        ctx.setDateRange('7days', null, null)
        ctx.setTags(['moth'], 'all')
        ctx.setSpecies(['Actias luna'], true)
        ctx.setFileTypes(['jpg'])
        ctx.setCameraSettings({ iso: { min: 100, max: 800 } })
        ctx.setNotes(true, 'keywords')
        ctx.setCustomField('location', 'Forest')
      })

      // Clear all
      act(() => {
        ctx.clearAllFilters()
      })

      expect(ctx.dateRange).toEqual({ preset: null, startDate: null, endDate: null })
      expect(ctx.tags).toEqual({ selected: [], matchMode: 'any' })
      expect(ctx.species).toEqual({ selected: [], includeUnidentified: false })
      expect(ctx.fileTypes).toEqual({ selected: [] })
      expect(ctx.cameraSettings).toEqual({
        iso: { min: null, max: null },
        aperture: { min: null, max: null },
        shutterSpeed: { min: null, max: null }
      })
      expect(ctx.notes).toEqual({ hasNotes: null, keywords: '' })
      expect(ctx.customFields).toEqual({})
    })

    it('should preserve UI state (drawer and sections)', async () => {
      await setupContext()

      // Change UI state
      act(() => {
        ctx.toggleDrawer()
        ctx.toggleSection('tags')
      })

      const initialDrawerState = ctx.isDrawerOpen
      const initialSections = [...ctx.expandedSections]

      // Set and clear filters
      act(() => {
        ctx.setTags(['moth'], null)
        ctx.clearAllFilters()
      })

      expect(ctx.isDrawerOpen).toBe(initialDrawerState) // Preserved
      expect(ctx.expandedSections).toEqual(initialSections) // Preserved
    })
  })

  describe('toggleDrawer action', () => {
    it('should toggle isDrawerOpen from true to false', async () => {
      await setupContext()

      // Initial state is now true (drawer open by default)
      expect(ctx.isDrawerOpen).toBe(true)

      act(() => {
        ctx.toggleDrawer()
      })

      expect(ctx.isDrawerOpen).toBe(false)
    })

    it('should toggle isDrawerOpen from false to true', async () => {
      await setupContext()

      // First toggle: true -> false
      act(() => {
        ctx.toggleDrawer()
      })
      expect(ctx.isDrawerOpen).toBe(false)

      // Second toggle: false -> true
      act(() => {
        ctx.toggleDrawer()
      })

      expect(ctx.isDrawerOpen).toBe(true)
    })

    it('should toggle multiple times', async () => {
      await setupContext()

      // Initial: true
      act(() => {
        ctx.toggleDrawer()
      })
      expect(ctx.isDrawerOpen).toBe(false)

      act(() => {
        ctx.toggleDrawer()
      })
      expect(ctx.isDrawerOpen).toBe(true)

      act(() => {
        ctx.toggleDrawer()
      })
      expect(ctx.isDrawerOpen).toBe(false)
    })
  })

  describe('toggleSection action', () => {
    it('should add section to expandedSections', async () => {
      await setupContext()

      act(() => {
        ctx.toggleSection('tags')
      })

      expect(ctx.expandedSections).toContain('tags')
      expect(ctx.expandedSections).toContain('dateRange') // Initial section preserved
    })

    it('should remove section from expandedSections', async () => {
      await setupContext()

      act(() => {
        ctx.toggleSection('tags')
      })
      expect(ctx.expandedSections).toContain('tags')

      act(() => {
        ctx.toggleSection('tags')
      })

      expect(ctx.expandedSections).not.toContain('tags')
    })

    it('should toggle multiple sections', async () => {
      await setupContext()

      act(() => {
        ctx.toggleSection('tags')
        ctx.toggleSection('species')
        ctx.toggleSection('fileTypes')
      })

      expect(ctx.expandedSections).toContain('dateRange')
      expect(ctx.expandedSections).toContain('tags')
      expect(ctx.expandedSections).toContain('species')
      expect(ctx.expandedSections).toContain('fileTypes')
    })

    it('should collapse initial dateRange section', async () => {
      await setupContext()

      expect(ctx.expandedSections).toContain('dateRange')

      act(() => {
        ctx.toggleSection('dateRange')
      })

      expect(ctx.expandedSections).not.toContain('dateRange')
    })
  })

  describe('loadState action', () => {
    it('should load complete state', async () => {
      await setupContext()

      const newState = {
        dateRange: { preset: '7days', startDate: null, endDate: null },
        tags: { selected: ['moth'], matchMode: 'all' },
        species: { selected: ['Actias luna'], includeUnidentified: true },
        fileTypes: { selected: ['jpg'] },
        cameraSettings: {
          iso: { min: 100, max: 800 },
          aperture: { min: 2.8, max: 5.6 },
          shutterSpeed: { min: null, max: null }
        },
        notes: { hasNotes: true, keywords: 'test' },
        customFields: { location: 'Forest' },
        isDrawerOpen: true,
        expandedSections: ['tags', 'species']
      }

      act(() => {
        ctx.loadState(newState)
      })

      expect(ctx.dateRange).toEqual(newState.dateRange)
      expect(ctx.tags).toEqual(newState.tags)
      expect(ctx.species).toEqual(newState.species)
      expect(ctx.fileTypes).toEqual(newState.fileTypes)
      expect(ctx.cameraSettings).toEqual(newState.cameraSettings)
      expect(ctx.notes).toEqual(newState.notes)
      expect(ctx.customFields).toEqual(newState.customFields)
      expect(ctx.isDrawerOpen).toBe(true)
      expect(ctx.expandedSections).toEqual(['tags', 'species'])
    })

    it('should handle partial state', async () => {
      await setupContext()

      // Set some initial state
      act(() => {
        ctx.setTags(['initial'], 'any')
        ctx.setSpecies(['initial species'], false)
      })

      // Load partial state (only dateRange and tags)
      act(() => {
        ctx.loadState({
          dateRange: { preset: '30days', startDate: null, endDate: null },
          tags: { selected: ['updated'], matchMode: 'all' }
        })
      })

      expect(ctx.dateRange.preset).toBe('30days')
      expect(ctx.tags.selected).toEqual(['updated'])
      expect(ctx.tags.matchMode).toBe('all')
      expect(ctx.species.selected).toEqual(['initial species']) // Preserved
    })

    it('should merge state objects correctly', async () => {
      await setupContext()

      // Initial state: isDrawerOpen is true
      // Toggle it to false, then set a date range
      act(() => {
        ctx.setDateRange('7days', null, null)
        ctx.toggleDrawer() // true -> false
      })

      act(() => {
        ctx.loadState({
          tags: { selected: ['loaded'], matchMode: 'all' }
        })
      })

      // New state loaded
      expect(ctx.tags).toEqual({ selected: ['loaded'], matchMode: 'all' })
      // Existing state preserved
      expect(ctx.dateRange.preset).toBe('7days')
      expect(ctx.isDrawerOpen).toBe(false) // Toggled from true to false
    })
  })

  describe('activeFilterCount computed value', () => {
    it('should count dateRange filter when preset is set', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange('7days', null, null)
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count dateRange filter when startDate is set', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange(null, '2024-01-01', null)
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count dateRange filter when endDate is set', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange(null, null, '2024-01-31')
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count tags filter when tags are selected', async () => {
      await setupContext()

      act(() => {
        ctx.setTags(['moth'], undefined)
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count species filter when species are selected', async () => {
      await setupContext()

      act(() => {
        ctx.setSpecies(['Actias luna'], undefined)
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count species filter when includeUnidentified is true', async () => {
      await setupContext()

      act(() => {
        ctx.setSpecies(undefined, true)
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count fileTypes filter when file types are selected', async () => {
      await setupContext()

      act(() => {
        ctx.setFileTypes(['jpg'])
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count cameraSettings filter when ISO min is set', async () => {
      await setupContext()

      act(() => {
        ctx.setCameraSettings({ iso: { min: 100, max: null } })
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count cameraSettings filter when ISO max is set', async () => {
      await setupContext()

      act(() => {
        ctx.setCameraSettings({ iso: { min: null, max: 800 } })
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count cameraSettings filter when aperture is set', async () => {
      await setupContext()

      act(() => {
        ctx.setCameraSettings({ aperture: { min: 2.8, max: 5.6 } })
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count cameraSettings filter when shutter speed is set', async () => {
      await setupContext()

      act(() => {
        ctx.setCameraSettings({ shutterSpeed: { min: 1/1000, max: null } })
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count cameraSettings as one filter even with multiple settings', async () => {
      await setupContext()

      act(() => {
        ctx.setCameraSettings({
          iso: { min: 100, max: 800 },
          aperture: { min: 2.8, max: 5.6 },
          shutterSpeed: { min: 1/1000, max: 1/60 }
        })
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count notes filter when hasNotes is set', async () => {
      await setupContext()

      act(() => {
        ctx.setNotes(true, null)
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count notes filter when keywords are set', async () => {
      await setupContext()

      act(() => {
        ctx.setNotes(null, 'test keywords')
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count customFields filter when fields are set', async () => {
      await setupContext()

      act(() => {
        ctx.setCustomField('location', 'Forest')
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count customFields as one filter even with multiple fields', async () => {
      await setupContext()

      act(() => {
        ctx.setCustomField('location', 'Forest')
        ctx.setCustomField('weather', 'Clear')
        ctx.setCustomField('temperature', '22C')
      })

      expect(ctx.activeFilterCount).toBe(1)
    })

    it('should count all active filters correctly', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange('7days', null, null)
        ctx.setTags(['moth'], null)
        ctx.setSpecies(['Actias luna'], null)
        ctx.setFileTypes(['jpg'])
        ctx.setCameraSettings({ iso: { min: 100, max: 800 } })
        ctx.setNotes(true, null)
        ctx.setCustomField('location', 'Forest')
      })

      expect(ctx.activeFilterCount).toBe(7)
    })

    it('should update count when filters are cleared', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange('7days', null, null)
        ctx.setTags(['moth'], null)
        ctx.setSpecies(['Actias luna'], null)
      })
      expect(ctx.activeFilterCount).toBe(3)

      act(() => {
        ctx.clearFilter('tags')
      })

      expect(ctx.activeFilterCount).toBe(2)

      act(() => {
        ctx.clearAllFilters()
      })

      expect(ctx.activeFilterCount).toBe(0)
    })
  })

  describe('hasActiveFilters computed value', () => {
    it('should be false when no filters are active', async () => {
      await setupContext()

      expect(ctx.hasActiveFilters).toBe(false)
    })

    it('should be true when at least one filter is active', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange('7days', null, null)
      })

      expect(ctx.hasActiveFilters).toBe(true)
    })

    it('should be true when multiple filters are active', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange('7days', null, null)
        ctx.setTags(['moth'], null)
      })

      expect(ctx.hasActiveFilters).toBe(true)
    })

    it('should become false when all filters are cleared', async () => {
      await setupContext()

      act(() => {
        ctx.setDateRange('7days', null, null)
        ctx.setTags(['moth'], null)
      })
      expect(ctx.hasActiveFilters).toBe(true)

      act(() => {
        ctx.clearAllFilters()
      })

      expect(ctx.hasActiveFilters).toBe(false)
    })
  })

  describe('FilterProvider', () => {
    it('should render children', async () => {
      const { container } = render(
        <FilterProvider>
          <div data-testid="test-child">Test Child</div>
        </FilterProvider>
      )

      expect(container.querySelector('[data-testid="test-child"]')).toBeTruthy()
    })
  })

  describe('useFilterContext hook error handling', () => {
    it('should throw error when used outside FilterProvider', () => {
      // Suppress console.error for this test
      const consoleError = console.error
      console.error = () => {}

      expect(() => {
        render(<TestConsumer onContextReady={() => {}} />)
      }).toThrow('useFilterContext must be used within a FilterProvider')

      console.error = consoleError
    })
  })
})
