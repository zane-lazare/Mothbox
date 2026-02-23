import { describe, it, expect } from 'vitest'
import { cameraPresetFormSchema, WORKFLOW_VALUES } from '../camera-preset'

describe('cameraPresetFormSchema', () => {
  const validData = { name: 'my_preset', description: '', workflow: 'both' as const }

  describe('name', () => {
    it('accepts valid alphanumeric+underscore names', () => {
      const result = cameraPresetFormSchema.safeParse(validData)
      expect(result.success).toBe(true)
    })

    it('rejects empty name', () => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, name: '' })
      expect(result.success).toBe(false)
      expect(result.error!.issues[0].message).toBe('Preset name is required')
    })

    it('rejects name shorter than 3 characters', () => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, name: 'ab' })
      expect(result.success).toBe(false)
      expect(result.error!.issues[0].message).toBe('Name must be at least 3 characters')
    })

    it('rejects name with spaces or special characters', () => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, name: 'my preset!' })
      expect(result.success).toBe(false)
      expect(result.error!.issues[0].message).toBe(
        'Name can only contain letters, numbers, and underscores'
      )
    })

    it('rejects name longer than 50 characters', () => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, name: 'a'.repeat(51) })
      expect(result.success).toBe(false)
      expect(result.error!.issues[0].message).toBe('Name must be 50 characters or less')
    })

    it('trims whitespace before validation', () => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, name: '  my_preset  ' })
      expect(result.success).toBe(true)
      expect(result.data!.name).toBe('my_preset')
    })
  })

  describe('description', () => {
    it('defaults to empty string when omitted', () => {
      const result = cameraPresetFormSchema.safeParse({ name: 'abc', workflow: 'both' })
      expect(result.success).toBe(true)
      expect(result.data!.description).toBe('')
    })

    it('accepts description up to 200 characters', () => {
      const result = cameraPresetFormSchema.safeParse({
        ...validData,
        description: 'x'.repeat(200),
      })
      expect(result.success).toBe(true)
    })

    it('rejects description longer than 200 characters', () => {
      const result = cameraPresetFormSchema.safeParse({
        ...validData,
        description: 'x'.repeat(201),
      })
      expect(result.success).toBe(false)
      expect(result.error!.issues[0].message).toBe(
        'Description must be 200 characters or less'
      )
    })
  })

  describe('workflow', () => {
    it.each(['photo', 'liveview', 'both'] as const)('accepts "%s"', (wf) => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, workflow: wf })
      expect(result.success).toBe(true)
    })

    it('rejects invalid workflow value', () => {
      const result = cameraPresetFormSchema.safeParse({ ...validData, workflow: 'invalid' })
      expect(result.success).toBe(false)
    })

    it('defaults to "both" when omitted', () => {
      const result = cameraPresetFormSchema.safeParse({ name: 'abc', description: '' })
      expect(result.success).toBe(true)
      expect(result.data!.workflow).toBe('both')
    })
  })

  describe('WORKFLOW_VALUES', () => {
    it('exports the three workflow options', () => {
      expect(WORKFLOW_VALUES).toEqual(['photo', 'liveview', 'both'])
    })
  })
})
