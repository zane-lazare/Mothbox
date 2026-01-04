import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MoonPhaseTriggerForm from '../MoonPhaseTriggerForm'
import { MOON_PHASES } from '../constants'

describe('MoonPhaseTriggerForm', () => {
  const mockOnChange = vi.fn()
  const defaultTrigger = {
    trigger_type: 'moon_phase',
    phases: ['full'],
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders moon phase grid with 4 options', () => {
      render(<MoonPhaseTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('moon-phase-trigger-form')).toBeInTheDocument()
      expect(screen.getByTestId('moon-phase-grid')).toBeInTheDocument()

      MOON_PHASES.forEach((phase) => {
        expect(screen.getByTestId(`moon-phase-${phase.value}`)).toBeInTheDocument()
      })
    })

    it('shows correct phase as selected', () => {
      render(<MoonPhaseTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('moon-phase-full')).toBeChecked()
      expect(screen.getByTestId('moon-phase-new')).not.toBeChecked()
    })

    it('renders emojis for each phase', () => {
      render(<MoonPhaseTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByText('🌑')).toBeInTheDocument()
      expect(screen.getByText('🌓')).toBeInTheDocument()
      expect(screen.getByText('🌕')).toBeInTheDocument()
      expect(screen.getByText('🌗')).toBeInTheDocument()
    })

    it('shows preview text', () => {
      render(<MoonPhaseTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('moon-phase-preview')).toBeInTheDocument()
    })
  })

  describe('Phase Selection', () => {
    it('adds phase when unselected phase clicked', async () => {
      const user = userEvent.setup()
      render(<MoonPhaseTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      await user.click(screen.getByTestId('moon-phase-new'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultTrigger,
        phases: ['full', 'new'],
      })
    })

    it('removes phase when selected phase clicked (multiple phases)', async () => {
      const user = userEvent.setup()
      render(
        <MoonPhaseTriggerForm
          trigger={{ ...defaultTrigger, phases: ['full', 'new'] }}
          onChange={mockOnChange}
        />
      )

      await user.click(screen.getByTestId('moon-phase-full'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultTrigger,
        phases: ['new'],
      })
    })

    it('prevents removing last phase', async () => {
      const user = userEvent.setup()
      render(<MoonPhaseTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      await user.click(screen.getByTestId('moon-phase-full'))

      // Should not call onChange - can't remove last phase
      expect(mockOnChange).not.toHaveBeenCalled()
    })

    it('allows selecting multiple phases', async () => {
      const user = userEvent.setup()
      render(<MoonPhaseTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      await user.click(screen.getByTestId('moon-phase-new'))

      expect(mockOnChange).toHaveBeenCalledWith({
        ...defaultTrigger,
        phases: ['full', 'new'],
      })
    })
  })

  describe('Disabled State', () => {
    it('disables all checkboxes when disabled prop is true', () => {
      render(<MoonPhaseTriggerForm trigger={defaultTrigger} onChange={mockOnChange} disabled />)

      MOON_PHASES.forEach((phase) => {
        expect(screen.getByTestId(`moon-phase-${phase.value}`)).toBeDisabled()
      })
    })
  })

  describe('data-testid attributes', () => {
    it('has moon-phase-trigger-form on container', () => {
      render(<MoonPhaseTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('moon-phase-trigger-form')).toBeInTheDocument()
    })

    it('has moon-phase-grid on grid container', () => {
      render(<MoonPhaseTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('moon-phase-grid')).toBeInTheDocument()
    })

    it('has moon-phase-{value} on each checkbox', () => {
      render(<MoonPhaseTriggerForm trigger={defaultTrigger} onChange={mockOnChange} />)

      expect(screen.getByTestId('moon-phase-new')).toBeInTheDocument()
      expect(screen.getByTestId('moon-phase-first_quarter')).toBeInTheDocument()
      expect(screen.getByTestId('moon-phase-full')).toBeInTheDocument()
      expect(screen.getByTestId('moon-phase-last_quarter')).toBeInTheDocument()
    })
  })
})
