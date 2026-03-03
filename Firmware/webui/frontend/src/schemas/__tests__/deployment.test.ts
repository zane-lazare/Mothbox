import { describe, it, expect } from 'vitest'
import {
  deploymentSchema,
  deploymentFieldEntrySchema,
  DEPLOYMENT_DEFAULTS,
  type DeploymentFormData,
} from '../deployment'

/** Helper: create valid deployment, overriding specific fields. */
function validDeployment(overrides: Partial<DeploymentFormData> = {}): DeploymentFormData {
  return { ...DEPLOYMENT_DEFAULTS, deployment_name: 'Test Deployment', ...overrides }
}

describe('deploymentSchema', () => {
  describe('deployment_name', () => {
    it('accepts valid name', () => {
      expect(deploymentSchema.safeParse(validDeployment()).success).toBe(true)
    })

    it('rejects empty name', () => {
      const result = deploymentSchema.safeParse(validDeployment({ deployment_name: '' }))
      expect(result.success).toBe(false)
    })

    it('rejects name over 200 chars', () => {
      const result = deploymentSchema.safeParse(validDeployment({ deployment_name: 'a'.repeat(201) }))
      expect(result.success).toBe(false)
    })

    it('accepts exactly 200 chars', () => {
      expect(deploymentSchema.safeParse(validDeployment({ deployment_name: 'a'.repeat(200) })).success).toBe(true)
    })
  })

  describe('location_name', () => {
    it('accepts empty string', () => {
      expect(deploymentSchema.safeParse(validDeployment({ location_name: '' })).success).toBe(true)
    })

    it('rejects over 500 chars', () => {
      const result = deploymentSchema.safeParse(validDeployment({ location_name: 'a'.repeat(501) }))
      expect(result.success).toBe(false)
    })

    it('accepts exactly 500 chars', () => {
      expect(deploymentSchema.safeParse(validDeployment({ location_name: 'a'.repeat(500) })).success).toBe(true)
    })
  })

  describe('coordinates', () => {
    it('accepts null latitude and longitude', () => {
      expect(deploymentSchema.safeParse(validDeployment({ latitude: null, longitude: null })).success).toBe(true)
    })

    it('accepts valid coordinates', () => {
      expect(deploymentSchema.safeParse(validDeployment({ latitude: 35.96, longitude: -83.92 })).success).toBe(true)
    })

    it('rejects latitude below -90', () => {
      expect(deploymentSchema.safeParse(validDeployment({ latitude: -91 })).success).toBe(false)
    })

    it('rejects latitude above 90', () => {
      expect(deploymentSchema.safeParse(validDeployment({ latitude: 91 })).success).toBe(false)
    })

    it('rejects longitude below -180', () => {
      expect(deploymentSchema.safeParse(validDeployment({ longitude: -181 })).success).toBe(false)
    })

    it('rejects longitude above 180', () => {
      expect(deploymentSchema.safeParse(validDeployment({ longitude: 181 })).success).toBe(false)
    })

    it('accepts boundary values (-90, 90, -180, 180)', () => {
      expect(deploymentSchema.safeParse(validDeployment({ latitude: -90, longitude: -180 })).success).toBe(true)
      expect(deploymentSchema.safeParse(validDeployment({ latitude: 90, longitude: 180 })).success).toBe(true)
    })
  })

  describe('altitude', () => {
    it('accepts null altitude', () => {
      expect(deploymentSchema.safeParse(validDeployment({ altitude: null })).success).toBe(true)
    })

    it('accepts numeric altitude', () => {
      expect(deploymentSchema.safeParse(validDeployment({ altitude: 350.5 })).success).toBe(true)
    })

    it('accepts negative altitude (below sea level)', () => {
      expect(deploymentSchema.safeParse(validDeployment({ altitude: -42 })).success).toBe(true)
    })
  })

  describe('date range', () => {
    it('accepts both dates empty', () => {
      expect(deploymentSchema.safeParse(validDeployment({ start_date: '', end_date: '' })).success).toBe(true)
    })

    it('accepts start_date only', () => {
      expect(deploymentSchema.safeParse(validDeployment({ start_date: '2024-06-01', end_date: '' })).success).toBe(true)
    })

    it('accepts end_date only', () => {
      expect(deploymentSchema.safeParse(validDeployment({ start_date: '', end_date: '2024-08-31' })).success).toBe(true)
    })

    it('accepts valid range (start <= end)', () => {
      expect(deploymentSchema.safeParse(validDeployment({ start_date: '2024-06-01', end_date: '2024-08-31' })).success).toBe(true)
    })

    it('accepts same start and end date', () => {
      expect(deploymentSchema.safeParse(validDeployment({ start_date: '2024-06-01', end_date: '2024-06-01' })).success).toBe(true)
    })

    it('rejects end before start', () => {
      const result = deploymentSchema.safeParse(validDeployment({ start_date: '2024-12-01', end_date: '2024-11-01' }))
      expect(result.success).toBe(false)
    })
  })

  describe('environmental', () => {
    it('accepts empty array', () => {
      expect(deploymentSchema.safeParse(validDeployment({ environmental: [] })).success).toBe(true)
    })

    it('accepts key-value pairs', () => {
      const result = deploymentSchema.safeParse(validDeployment({
        environmental: [{ key: 'temperature', value: '20°C' }]
      }))
      expect(result.success).toBe(true)
    })
  })

  describe('custom', () => {
    it('accepts empty array', () => {
      expect(deploymentSchema.safeParse(validDeployment({ custom: [] })).success).toBe(true)
    })

    it('accepts up to 50 entries', () => {
      const custom = Array.from({ length: 50 }, (_, i) => ({ key: `key${i}`, value: `val${i}` }))
      expect(deploymentSchema.safeParse(validDeployment({ custom })).success).toBe(true)
    })

    it('rejects over 50 entries', () => {
      const custom = Array.from({ length: 51 }, (_, i) => ({ key: `key${i}`, value: `val${i}` }))
      expect(deploymentSchema.safeParse(validDeployment({ custom })).success).toBe(false)
    })
  })

  describe('DEPLOYMENT_DEFAULTS', () => {
    it('fails validation (deployment_name is empty)', () => {
      expect(deploymentSchema.safeParse(DEPLOYMENT_DEFAULTS).success).toBe(false)
    })

    it('passes with a name added', () => {
      expect(deploymentSchema.safeParse({ ...DEPLOYMENT_DEFAULTS, deployment_name: 'Test' }).success).toBe(true)
    })
  })
})

describe('deploymentFieldEntrySchema', () => {
  it('accepts key-value pair', () => {
    expect(deploymentFieldEntrySchema.safeParse({ key: 'temp', value: '20°C' }).success).toBe(true)
  })

  it('accepts empty strings', () => {
    expect(deploymentFieldEntrySchema.safeParse({ key: '', value: '' }).success).toBe(true)
  })
})
