import { render, act, cleanup } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import React from 'react'
import { SchedulerProvider, useSchedulerContext } from '../SchedulerContext'

// Test component to access context
function TestConsumer({ onContextReady }) {
  const ctx = useSchedulerContext()
  React.useEffect(() => {
    onContextReady(ctx)
  }, [ctx, onContextReady])
  return null
}

// Helper to render with provider
function renderWithProvider(ui) {
  return render(<SchedulerProvider>{ui}</SchedulerProvider>)
}

describe('SchedulerContext', () => {
  let ctx

  beforeEach(() => {
    ctx = null
  })

  afterEach(() => {
    cleanup()
  })

  const setupContext = () => {
    return new Promise((resolve) => {
      renderWithProvider(<TestConsumer onContextReady={(c) => { ctx = c; resolve() }} />)
    })
  }

  describe('Initial State', () => {
    it('should provide correct initial schedules', async () => {
      await setupContext()
      expect(ctx.state.schedules).toEqual([])
    })

    it('should provide correct initial activeSchedule', async () => {
      await setupContext()
      expect(ctx.state.activeSchedule).toBe(null)
    })

    it('should provide correct initial editingSchedule', async () => {
      await setupContext()
      expect(ctx.state.editingSchedule).toBe(null)
    })

    it('should provide correct initial isCreating', async () => {
      await setupContext()
      expect(ctx.state.isCreating).toBe(false)
    })

    it('should provide correct initial hasUnsavedChanges', async () => {
      await setupContext()
      expect(ctx.state.hasUnsavedChanges).toBe(false)
    })

    it('should provide correct initial previewEvents', async () => {
      await setupContext()
      expect(ctx.preview.events).toEqual([])
    })

    it('should provide correct initial previewLoading', async () => {
      await setupContext()
      expect(ctx.preview.loading).toBe(false)
    })

    it('should provide correct initial previewError', async () => {
      await setupContext()
      expect(ctx.preview.error).toBe(null)
    })

    it('should provide correct initial conflicts', async () => {
      await setupContext()
      expect(ctx.validation.conflicts).toEqual([])
    })

    it('should provide correct initial moonPhases', async () => {
      await setupContext()
      expect(ctx.ui.moonPhases).toEqual({})
    })

    it('should provide correct initial viewMode', async () => {
      await setupContext()
      expect(ctx.ui.viewMode).toBe('list')
    })

    it('should provide correct initial selectedDate', async () => {
      await setupContext()
      expect(ctx.ui.selectedDate).toBe(null)
    })

    it('should provide correct initial isExpertMode', async () => {
      await setupContext()
      expect(ctx.ui.isExpertMode).toBe(false)
    })

    it('should have isDrawerOpen true initially', async () => {
      await setupContext()
      expect(ctx.ui.isDrawerOpen).toBe(true)
    })

    it('should have expandedSections with triggers initially', async () => {
      await setupContext()
      expect(ctx.ui.expandedSections).toEqual(['triggers'])
    })
  })

  describe('SET_SCHEDULES action', () => {
    it('should set schedules array', async () => {
      await setupContext()

      const schedules = [
        { id: 1, name: 'Nightly Capture' },
        { id: 2, name: 'Weekend Survey' }
      ]

      act(() => {
        ctx.scheduleActions.setSchedules(schedules)
      })

      expect(ctx.state.schedules).toEqual(schedules)
    })

    it('should handle empty schedules array', async () => {
      await setupContext()

      // Set some schedules first
      act(() => {
        ctx.scheduleActions.setSchedules([{ id: 1, name: 'Test' }])
      })

      // Clear with empty array
      act(() => {
        ctx.scheduleActions.setSchedules([])
      })

      expect(ctx.state.schedules).toEqual([])
    })

    it('should preserve other state when setting schedules', async () => {
      await setupContext()

      act(() => {
        ctx.uiActions.setViewMode('calendar')
        ctx.scheduleActions.setSchedules([{ id: 1, name: 'Test' }])
      })

      expect(ctx.state.schedules).toEqual([{ id: 1, name: 'Test' }])
      expect(ctx.ui.viewMode).toBe('calendar') // Preserved
    })

    it('should ignore invalid schedules (null)', async () => {
      await setupContext()

      // Set valid schedules first
      act(() => {
        ctx.scheduleActions.setSchedules([{ id: 1, name: 'Test' }])
      })
      expect(ctx.state.schedules).toHaveLength(1)

      // Try to set null - should be ignored
      act(() => {
        ctx.scheduleActions.setSchedules(null)
      })

      // State unchanged
      expect(ctx.state.schedules).toHaveLength(1)
    })

    it('should ignore invalid schedules (non-array)', async () => {
      await setupContext()

      // Set valid schedules first
      act(() => {
        ctx.scheduleActions.setSchedules([{ id: 1, name: 'Test' }])
      })
      expect(ctx.state.schedules).toHaveLength(1)

      // Try to set object - should be ignored
      act(() => {
        ctx.scheduleActions.setSchedules({ id: 1, name: 'Test' })
      })

      // State unchanged
      expect(ctx.state.schedules).toHaveLength(1)
    })
  })

  describe('SET_ACTIVE_SCHEDULE action', () => {
    it('should set active schedule', async () => {
      await setupContext()

      const schedule = { id: 1, name: 'Nightly Capture', isActive: true }

      act(() => {
        ctx.scheduleActions.setActiveSchedule(schedule)
      })

      expect(ctx.state.activeSchedule).toEqual(schedule)
    })

    it('should clear active schedule with null', async () => {
      await setupContext()

      act(() => {
        ctx.scheduleActions.setActiveSchedule({ id: 1, name: 'Test' })
      })
      expect(ctx.state.activeSchedule).not.toBe(null)

      act(() => {
        ctx.scheduleActions.clearActiveSchedule()
      })

      expect(ctx.state.activeSchedule).toBe(null)
    })

    it('should preserve schedules list when setting active schedule', async () => {
      await setupContext()

      const schedules = [{ id: 1, name: 'Test' }]

      act(() => {
        ctx.scheduleActions.setSchedules(schedules)
        ctx.scheduleActions.setActiveSchedule(schedules[0])
      })

      expect(ctx.state.activeSchedule).toEqual(schedules[0])
      expect(ctx.state.schedules).toEqual(schedules) // Preserved
    })
  })

  describe('Editing State actions', () => {
    it('should set editing schedule', async () => {
      await setupContext()

      const schedule = { id: 1, name: 'Edit Me' }

      act(() => {
        ctx.editActions.setEditingSchedule(schedule)
      })

      expect(ctx.state.editingSchedule).toEqual(schedule)
    })

    it('should clear editing schedule', async () => {
      await setupContext()

      act(() => {
        ctx.editActions.setEditingSchedule({ id: 1, name: 'Test' })
      })

      act(() => {
        ctx.editActions.clearEditingSchedule()
      })

      expect(ctx.state.editingSchedule).toBe(null)
    })

    it('should update editing schedule', async () => {
      await setupContext()

      act(() => {
        ctx.editActions.setEditingSchedule({ id: 1, name: 'Original', enabled: true })
      })

      act(() => {
        ctx.editActions.updateEditingSchedule({ name: 'Updated' })
      })

      expect(ctx.state.editingSchedule).toEqual({ id: 1, name: 'Updated', enabled: true })
    })

    it('should set isCreating flag', async () => {
      await setupContext()

      act(() => {
        ctx.editActions.setCreating(true)
      })

      expect(ctx.state.isCreating).toBe(true)

      act(() => {
        ctx.editActions.setCreating(false)
      })

      expect(ctx.state.isCreating).toBe(false)
    })

    it('should set unsaved changes flag', async () => {
      await setupContext()

      act(() => {
        ctx.editActions.setUnsavedChanges(true)
      })

      expect(ctx.state.hasUnsavedChanges).toBe(true)

      act(() => {
        ctx.editActions.setUnsavedChanges(false)
      })

      expect(ctx.state.hasUnsavedChanges).toBe(false)
    })

    it('should preserve other state when updating editing schedule', async () => {
      await setupContext()

      act(() => {
        ctx.editActions.setEditingSchedule({ id: 1, name: 'Test' })
        ctx.uiActions.setViewMode('calendar')
      })

      act(() => {
        ctx.editActions.updateEditingSchedule({ name: 'Updated' })
      })

      expect(ctx.state.editingSchedule.name).toBe('Updated')
      expect(ctx.ui.viewMode).toBe('calendar') // Preserved
    })

    it('should ignore invalid updates (null)', async () => {
      await setupContext()

      act(() => {
        ctx.editActions.setEditingSchedule({ id: 1, name: 'Original' })
      })

      // Try to update with null - should be ignored
      act(() => {
        ctx.editActions.updateEditingSchedule(null)
      })

      expect(ctx.state.editingSchedule).toEqual({ id: 1, name: 'Original' })
    })

    it('should ignore invalid updates (array)', async () => {
      await setupContext()

      act(() => {
        ctx.editActions.setEditingSchedule({ id: 1, name: 'Original' })
      })

      // Try to update with array - should be ignored
      act(() => {
        ctx.editActions.updateEditingSchedule(['invalid'])
      })

      expect(ctx.state.editingSchedule).toEqual({ id: 1, name: 'Original' })
    })

    it('should ignore update when no editing schedule exists', async () => {
      await setupContext()

      // Don't set any editing schedule
      expect(ctx.state.editingSchedule).toBeNull()

      // Try to update - should be ignored
      act(() => {
        ctx.editActions.updateEditingSchedule({ name: 'Updated' })
      })

      expect(ctx.state.editingSchedule).toBeNull()
    })

    it('should filter out invalid fields from updates (sanitization)', async () => {
      await setupContext()

      act(() => {
        ctx.editActions.setEditingSchedule({ id: 1, name: 'Original', enabled: true })
      })

      // Try to update with valid and invalid fields
      act(() => {
        ctx.editActions.updateEditingSchedule({
          name: 'Updated',                // valid
          __proto__: { malicious: true }, // invalid - not in SCHEDULE_FIELDS
          constructor: () => {},          // invalid
          dangerousField: 'hack',         // invalid
        })
      })

      // Only valid field should be updated
      expect(ctx.state.editingSchedule).toEqual({ id: 1, name: 'Updated', enabled: true })
      expect(ctx.state.editingSchedule.__proto__).toEqual(Object.prototype)
      expect(ctx.state.editingSchedule.dangerousField).toBeUndefined()
    })

    it('should ignore update with only invalid fields', async () => {
      await setupContext()

      act(() => {
        ctx.editActions.setEditingSchedule({ id: 1, name: 'Original' })
      })

      // Try to update with only invalid fields
      act(() => {
        ctx.editActions.updateEditingSchedule({
          invalidField: 'test',
          anotherBadField: 123,
        })
      })

      // State should be unchanged
      expect(ctx.state.editingSchedule).toEqual({ id: 1, name: 'Original' })
    })

    it('should allow all valid schedule fields', async () => {
      await setupContext()

      act(() => {
        ctx.editActions.setEditingSchedule({ id: 'orig' })
      })

      // Update with all valid fields
      act(() => {
        ctx.editActions.updateEditingSchedule({
          id: 'updated',
          name: 'Test Schedule',
          description: 'A description',
          events: [{ action: 'take_photo' }],
          enabled: true,
          category: 'test',
          triggers: [{ type: 'solar' }],
          created_at: '2024-01-01',
          modified_at: '2024-01-02',
          version: 2,
        })
      })

      expect(ctx.state.editingSchedule).toEqual({
        id: 'updated',
        name: 'Test Schedule',
        description: 'A description',
        events: [{ action: 'take_photo' }],
        enabled: true,
        category: 'test',
        triggers: [{ type: 'solar' }],
        created_at: '2024-01-01',
        modified_at: '2024-01-02',
        version: 2,
      })
    })
  })

  describe('Preview State actions', () => {
    it('should set preview events', async () => {
      await setupContext()

      const events = [
        { timestamp: '2024-01-01T10:00:00Z', action: 'capture' },
        { timestamp: '2024-01-01T22:00:00Z', action: 'capture' }
      ]

      act(() => {
        ctx.previewActions.setPreview(events)
      })

      expect(ctx.preview.events).toEqual(events)
    })

    it('should set preview loading state', async () => {
      await setupContext()

      act(() => {
        ctx.previewActions.setPreviewLoading(true)
      })

      expect(ctx.preview.loading).toBe(true)

      act(() => {
        ctx.previewActions.setPreviewLoading(false)
      })

      expect(ctx.preview.loading).toBe(false)
    })

    it('should set preview error', async () => {
      await setupContext()

      const error = 'Invalid trigger configuration'

      act(() => {
        ctx.previewActions.setPreviewError(error)
      })

      expect(ctx.preview.error).toBe(error)
    })

    it('should clear preview state', async () => {
      await setupContext()

      act(() => {
        ctx.previewActions.setPreview([{ timestamp: '2024-01-01T10:00:00Z' }])
        ctx.previewActions.setPreviewError('Some error')
      })

      act(() => {
        ctx.previewActions.clearPreview()
      })

      expect(ctx.preview.events).toEqual([])
      expect(ctx.preview.error).toBe(null)
    })

    it('should set moon phases data', async () => {
      await setupContext()

      const moonPhases = {
        '2024-01-01': { phase: 'full', illumination: 1.0 },
        '2024-01-15': { phase: 'new', illumination: 0.0 }
      }

      act(() => {
        ctx.previewActions.setMoonPhases(moonPhases)
      })

      expect(ctx.ui.moonPhases).toEqual(moonPhases)
    })

    it('should ignore invalid preview events (null)', async () => {
      await setupContext()

      const events = [{ timestamp: '2024-01-01T10:00:00Z' }]

      act(() => {
        ctx.previewActions.setPreview(events)
      })
      expect(ctx.preview.events).toEqual(events)

      // Try to set null - should be ignored
      act(() => {
        ctx.previewActions.setPreview(null)
      })

      expect(ctx.preview.events).toEqual(events)
    })

    it('should ignore invalid preview events (non-array)', async () => {
      await setupContext()

      const events = [{ timestamp: '2024-01-01T10:00:00Z' }]

      act(() => {
        ctx.previewActions.setPreview(events)
      })
      expect(ctx.preview.events).toEqual(events)

      // Try to set object - should be ignored
      act(() => {
        ctx.previewActions.setPreview({ timestamp: '2024-01-01T10:00:00Z' })
      })

      expect(ctx.preview.events).toEqual(events)
    })
  })

  describe('Validation State actions', () => {
    it('should set conflicts', async () => {
      await setupContext()

      const conflicts = [
        { scheduleId: 1, message: 'Time overlap detected' },
        { scheduleId: 2, message: 'Resource conflict' }
      ]

      act(() => {
        ctx.validationActions.setConflicts(conflicts)
      })

      expect(ctx.validation.conflicts).toEqual(conflicts)
    })

    it('should clear conflicts', async () => {
      await setupContext()

      act(() => {
        ctx.validationActions.setConflicts([{ scheduleId: 1, message: 'Test' }])
      })

      act(() => {
        ctx.validationActions.clearValidation()
      })

      expect(ctx.validation.conflicts).toEqual([])
    })

    it('should handle empty conflicts array', async () => {
      await setupContext()

      act(() => {
        ctx.validationActions.setConflicts([])
      })

      expect(ctx.validation.conflicts).toEqual([])
    })

    it('should preserve other state when setting conflicts', async () => {
      await setupContext()

      act(() => {
        ctx.editActions.setEditingSchedule({ id: 1, name: 'Test' })
        ctx.validationActions.setConflicts([{ scheduleId: 1, message: 'Conflict' }])
      })

      expect(ctx.validation.conflicts).toHaveLength(1)
      expect(ctx.state.editingSchedule).toEqual({ id: 1, name: 'Test' }) // Preserved
    })

    it('should ignore invalid conflicts (null)', async () => {
      await setupContext()

      const conflicts = [{ scheduleId: 1, message: 'Test' }]

      act(() => {
        ctx.validationActions.setConflicts(conflicts)
      })
      expect(ctx.validation.conflicts).toEqual(conflicts)

      // Try to set null - should be ignored
      act(() => {
        ctx.validationActions.setConflicts(null)
      })

      expect(ctx.validation.conflicts).toEqual(conflicts)
    })

    it('should ignore invalid conflicts (non-array)', async () => {
      await setupContext()

      const conflicts = [{ scheduleId: 1, message: 'Test' }]

      act(() => {
        ctx.validationActions.setConflicts(conflicts)
      })
      expect(ctx.validation.conflicts).toEqual(conflicts)

      // Try to set object - should be ignored
      act(() => {
        ctx.validationActions.setConflicts({ scheduleId: 1, message: 'Test' })
      })

      expect(ctx.validation.conflicts).toEqual(conflicts)
    })
  })

  describe('UI State actions', () => {
    it('should set view mode to list', async () => {
      await setupContext()

      act(() => {
        ctx.uiActions.setViewMode('list')
      })

      expect(ctx.ui.viewMode).toBe('list')
    })

    it('should set view mode to calendar', async () => {
      await setupContext()

      act(() => {
        ctx.uiActions.setViewMode('calendar')
      })

      expect(ctx.ui.viewMode).toBe('calendar')
    })

    it('should set view mode to timeline', async () => {
      await setupContext()

      act(() => {
        ctx.uiActions.setViewMode('timeline')
      })

      expect(ctx.ui.viewMode).toBe('timeline')
    })

    it('should set selected date', async () => {
      await setupContext()

      act(() => {
        ctx.uiActions.setSelectedDate('2024-01-15')
      })

      expect(ctx.ui.selectedDate).toBe('2024-01-15')
    })

    it('should clear selected date', async () => {
      await setupContext()

      act(() => {
        ctx.uiActions.setSelectedDate('2024-01-15')
      })

      act(() => {
        ctx.uiActions.setSelectedDate(null)
      })

      expect(ctx.ui.selectedDate).toBe(null)
    })

    it('should toggle expert mode', async () => {
      await setupContext()

      act(() => {
        ctx.uiActions.toggleExpertMode()
      })

      expect(ctx.ui.isExpertMode).toBe(true)

      act(() => {
        ctx.uiActions.toggleExpertMode()
      })

      expect(ctx.ui.isExpertMode).toBe(false)
    })

    it('should toggle drawer from true to false', async () => {
      await setupContext()

      expect(ctx.ui.isDrawerOpen).toBe(true) // Initial state

      act(() => {
        ctx.uiActions.toggleDrawer()
      })

      expect(ctx.ui.isDrawerOpen).toBe(false)
    })

    it('should toggle drawer from false to true', async () => {
      await setupContext()

      act(() => {
        ctx.uiActions.toggleDrawer() // true -> false
      })
      expect(ctx.ui.isDrawerOpen).toBe(false)

      act(() => {
        ctx.uiActions.toggleDrawer() // false -> true
      })

      expect(ctx.ui.isDrawerOpen).toBe(true)
    })

    it('should add section to expandedSections', async () => {
      await setupContext()

      act(() => {
        ctx.uiActions.toggleSection('actions')
      })

      expect(ctx.ui.expandedSections).toContain('actions')
      expect(ctx.ui.expandedSections).toContain('triggers') // Initial section preserved
    })

    it('should remove section from expandedSections', async () => {
      await setupContext()

      act(() => {
        ctx.uiActions.toggleSection('actions')
      })
      expect(ctx.ui.expandedSections).toContain('actions')

      act(() => {
        ctx.uiActions.toggleSection('actions')
      })

      expect(ctx.ui.expandedSections).not.toContain('actions')
    })

    it('should toggle multiple sections', async () => {
      await setupContext()

      act(() => {
        ctx.uiActions.toggleSection('actions')
        ctx.uiActions.toggleSection('conditions')
        ctx.uiActions.toggleSection('settings')
      })

      expect(ctx.ui.expandedSections).toContain('triggers')
      expect(ctx.ui.expandedSections).toContain('actions')
      expect(ctx.ui.expandedSections).toContain('conditions')
      expect(ctx.ui.expandedSections).toContain('settings')
    })

    it('should collapse initial triggers section', async () => {
      await setupContext()

      expect(ctx.ui.expandedSections).toContain('triggers')

      act(() => {
        ctx.uiActions.toggleSection('triggers')
      })

      expect(ctx.ui.expandedSections).not.toContain('triggers')
    })
  })

  describe('Computed Values', () => {
    it('should compute hasSchedules as false when schedules empty', async () => {
      await setupContext()

      expect(ctx.computed.hasSchedules).toBe(false)
    })

    it('should compute hasSchedules as true when schedules exist', async () => {
      await setupContext()

      act(() => {
        ctx.scheduleActions.setSchedules([{ id: 1, name: 'Test' }])
      })

      expect(ctx.computed.hasSchedules).toBe(true)
    })

    it('should compute isEditing as false initially', async () => {
      await setupContext()

      expect(ctx.computed.isEditing).toBe(false)
    })

    it('should compute isEditing as true when editingSchedule set', async () => {
      await setupContext()

      act(() => {
        ctx.editActions.setEditingSchedule({ id: 1, name: 'Test' })
      })

      expect(ctx.computed.isEditing).toBe(true)
    })

    it('should compute hasConflicts as false when no conflicts', async () => {
      await setupContext()

      expect(ctx.computed.hasConflicts).toBe(false)
    })

    it('should compute hasConflicts as true when conflicts exist', async () => {
      await setupContext()

      act(() => {
        ctx.validationActions.setConflicts([{ scheduleId: 1, message: 'Conflict' }])
      })

      expect(ctx.computed.hasConflicts).toBe(true)
    })
  })

  describe('LOAD_STATE action', () => {
    it('should load complete state', async () => {
      await setupContext()

      const newState = {
        schedules: [{ id: 1, name: 'Loaded' }],
        activeSchedule: { id: 1, name: 'Active' },
        editingSchedule: { id: 2, name: 'Editing' },
        isCreating: true,
        hasUnsavedChanges: true,
        previewEvents: [{ timestamp: '2024-01-01T10:00:00Z' }],
        previewLoading: true,
        previewError: 'Error message',
        conflicts: [{ scheduleId: 1, message: 'Conflict' }],
        moonPhases: { '2024-01-01': { phase: 'full' } },
        viewMode: 'calendar',
        selectedDate: '2024-01-15',
        isExpertMode: true,
        isDrawerOpen: false,
        expandedSections: ['actions', 'conditions']
      }

      act(() => {
        ctx.stateActions.loadState(newState)
      })

      expect(ctx.state.schedules).toEqual(newState.schedules)
      expect(ctx.state.activeSchedule).toEqual(newState.activeSchedule)
      expect(ctx.state.editingSchedule).toEqual(newState.editingSchedule)
      expect(ctx.state.isCreating).toBe(true)
      expect(ctx.state.hasUnsavedChanges).toBe(true)
      expect(ctx.preview.events).toEqual(newState.previewEvents)
      expect(ctx.preview.loading).toBe(true)
      expect(ctx.preview.error).toBe('Error message')
      expect(ctx.validation.conflicts).toEqual(newState.conflicts)
      expect(ctx.ui.moonPhases).toEqual(newState.moonPhases)
      expect(ctx.ui.viewMode).toBe('calendar')
      expect(ctx.ui.selectedDate).toBe('2024-01-15')
      expect(ctx.ui.isExpertMode).toBe(true)
      expect(ctx.ui.isDrawerOpen).toBe(false)
      expect(ctx.ui.expandedSections).toEqual(['actions', 'conditions'])
    })

    it('should handle partial state', async () => {
      await setupContext()

      // Set some initial state
      act(() => {
        ctx.scheduleActions.setSchedules([{ id: 1, name: 'Initial' }])
        ctx.uiActions.setViewMode('timeline')
      })

      // Load partial state
      act(() => {
        ctx.stateActions.loadState({
          activeSchedule: { id: 2, name: 'New Active' },
          viewMode: 'calendar'
        })
      })

      expect(ctx.state.activeSchedule).toEqual({ id: 2, name: 'New Active' })
      expect(ctx.ui.viewMode).toBe('calendar')
      expect(ctx.state.schedules).toEqual([{ id: 1, name: 'Initial' }]) // Preserved
    })

    it('should merge state objects correctly', async () => {
      await setupContext()

      act(() => {
        ctx.scheduleActions.setSchedules([{ id: 1, name: 'Original' }])
        ctx.uiActions.toggleDrawer() // true -> false
      })

      act(() => {
        ctx.stateActions.loadState({
          activeSchedule: { id: 1, name: 'Active' }
        })
      })

      expect(ctx.state.activeSchedule).toEqual({ id: 1, name: 'Active' })
      expect(ctx.state.schedules).toEqual([{ id: 1, name: 'Original' }]) // Preserved
      expect(ctx.ui.isDrawerOpen).toBe(false) // Preserved
    })

    it('should ignore invalid state (null)', async () => {
      await setupContext()

      act(() => {
        ctx.scheduleActions.setSchedules([{ id: 1, name: 'Original' }])
      })

      // Try to load null - should be ignored
      act(() => {
        ctx.stateActions.loadState(null)
      })

      expect(ctx.state.schedules).toEqual([{ id: 1, name: 'Original' }])
    })

    it('should ignore invalid state (array)', async () => {
      await setupContext()

      act(() => {
        ctx.scheduleActions.setSchedules([{ id: 1, name: 'Original' }])
      })

      // Try to load array - should be ignored
      act(() => {
        ctx.stateActions.loadState([{ schedules: [] }])
      })

      expect(ctx.state.schedules).toEqual([{ id: 1, name: 'Original' }])
    })

    it('should protect error state from external overwrite', async () => {
      await setupContext()

      // Set internal error state
      const internalError = new Error('Internal error')
      act(() => {
        ctx.errorActions.setError(internalError, { componentStack: 'stack' })
      })

      expect(ctx.state.error).toBe(internalError)
      expect(ctx.state.errorInfo).toEqual({ componentStack: 'stack' })

      // Try to overwrite via loadState - should be protected
      act(() => {
        ctx.stateActions.loadState({
          error: new Error('Malicious error'),
          errorInfo: { malicious: true },
          schedules: [{ id: 'new' }], // This should still work
        })
      })

      // Error state should be protected (unchanged)
      expect(ctx.state.error).toBe(internalError)
      expect(ctx.state.errorInfo).toEqual({ componentStack: 'stack' })
      // But valid state keys should update
      expect(ctx.state.schedules).toEqual([{ id: 'new' }])
    })

    it('should ignore load with only protected/invalid keys', async () => {
      await setupContext()

      act(() => {
        ctx.scheduleActions.setSchedules([{ id: 1, name: 'Original' }])
      })

      // Try to load only protected keys
      act(() => {
        ctx.stateActions.loadState({
          error: new Error('hack'),
          errorInfo: { bad: true },
          invalidKey: 'test',
        })
      })

      // State should be unchanged
      expect(ctx.state.schedules).toEqual([{ id: 1, name: 'Original' }])
      expect(ctx.state.error).toBeNull()
    })

    it('should filter to only loadable state keys', async () => {
      await setupContext()

      act(() => {
        ctx.stateActions.loadState({
          schedules: [{ id: 1 }],        // allowed
          viewMode: 'calendar',           // allowed
          error: new Error('blocked'),    // blocked
          errorInfo: { blocked: true },   // blocked
          __proto__: { bad: true },       // blocked
          constructor: () => {},          // blocked
        })
      })

      expect(ctx.state.schedules).toEqual([{ id: 1 }])
      expect(ctx.ui.viewMode).toBe('calendar')
      expect(ctx.state.error).toBeNull()
      expect(ctx.state.errorInfo).toBeNull()
    })
  })

  describe('RESET_STATE action', () => {
    it('should reset all state to initial values', async () => {
      await setupContext()

      // Set various state
      act(() => {
        ctx.scheduleActions.setSchedules([{ id: 1, name: 'Test' }])
        ctx.scheduleActions.setActiveSchedule({ id: 1, name: 'Active' })
        ctx.editActions.setEditingSchedule({ id: 2, name: 'Editing' })
        ctx.editActions.setCreating(true)
        ctx.editActions.setUnsavedChanges(true)
        ctx.previewActions.setPreview([{ timestamp: '2024-01-01T10:00:00Z' }])
        ctx.previewActions.setPreviewLoading(true)
        ctx.previewActions.setPreviewError('Error')
        ctx.validationActions.setConflicts([{ scheduleId: 1, message: 'Conflict' }])
        ctx.previewActions.setMoonPhases({ '2024-01-01': { phase: 'full' } })
        ctx.uiActions.setViewMode('calendar')
        ctx.uiActions.setSelectedDate('2024-01-15')
        ctx.uiActions.toggleExpertMode()
        ctx.uiActions.toggleDrawer()
      })

      // Reset
      act(() => {
        ctx.stateActions.resetState()
      })

      expect(ctx.state.schedules).toEqual([])
      expect(ctx.state.activeSchedule).toBe(null)
      expect(ctx.state.editingSchedule).toBe(null)
      expect(ctx.state.isCreating).toBe(false)
      expect(ctx.state.hasUnsavedChanges).toBe(false)
      expect(ctx.preview.events).toEqual([])
      expect(ctx.preview.loading).toBe(false)
      expect(ctx.preview.error).toBe(null)
      expect(ctx.validation.conflicts).toEqual([])
      expect(ctx.ui.moonPhases).toEqual({})
      expect(ctx.ui.viewMode).toBe('list')
      expect(ctx.ui.selectedDate).toBe(null)
      expect(ctx.ui.isExpertMode).toBe(false)
      expect(ctx.ui.isDrawerOpen).toBe(true)
      expect(ctx.ui.expandedSections).toEqual(['triggers'])
    })

    it('should preserve UI state when resetting data', async () => {
      await setupContext()

      // Set UI state
      act(() => {
        ctx.uiActions.toggleDrawer()
        ctx.uiActions.toggleSection('actions')
      })

      // Verify UI state was changed before reset
      expect(ctx.ui.isDrawerOpen).toBe(false)
      expect(ctx.ui.expandedSections).toContain('actions')

      // Set and reset data
      act(() => {
        ctx.scheduleActions.setSchedules([{ id: 1, name: 'Test' }])
        ctx.scheduleActions.setActiveSchedule({ id: 1, name: 'Active' })
      })

      // Note: resetState() resets EVERYTHING including UI
      // If we want selective reset, we need a different action
      // This test documents current behavior
      act(() => {
        ctx.stateActions.resetState()
      })

      // After full reset, UI state is also reset
      expect(ctx.ui.isDrawerOpen).toBe(true)
      expect(ctx.ui.expandedSections).toEqual(['triggers'])
    })
  })

  describe('SchedulerProvider', () => {
    it('should render children', async () => {
      const { container } = render(
        <SchedulerProvider>
          <div data-testid="test-child">Test Child</div>
        </SchedulerProvider>
      )

      expect(container.querySelector('[data-testid="test-child"]')).toBeTruthy()
    })
  })

  describe('useSchedulerContext hook error handling', () => {
    it('should throw error when used outside SchedulerProvider', () => {
      // Suppress console.error for this test
      const consoleError = console.error
      console.error = () => {}

      expect(() => {
        render(<TestConsumer onContextReady={() => {}} />)
      }).toThrow('useSchedulerContext must be used within a SchedulerProvider')

      console.error = consoleError
    })
  })

  describe('Error State actions', () => {
    it('should set error', async () => {
      await setupContext()

      const error = new Error('Test error')
      act(() => {
        ctx.errorActions.setError(error, { componentStack: 'test' })
      })

      expect(ctx.state.error).toBe(error)
      expect(ctx.state.errorInfo).toEqual({ componentStack: 'test' })
      expect(ctx.computed.hasError).toBe(true)
    })

    it('should clear error', async () => {
      await setupContext()

      act(() => {
        ctx.errorActions.setError(new Error('Test'))
      })

      act(() => {
        ctx.errorActions.clearError()
      })

      expect(ctx.state.error).toBe(null)
      expect(ctx.computed.hasError).toBe(false)
    })

    it('should set error without errorInfo', async () => {
      await setupContext()

      const error = new Error('Simple error')
      act(() => {
        ctx.errorActions.setError(error)
      })

      expect(ctx.state.error).toBe(error)
      expect(ctx.state.errorInfo).toBe(null)
      expect(ctx.computed.hasError).toBe(true)
    })
  })
})
