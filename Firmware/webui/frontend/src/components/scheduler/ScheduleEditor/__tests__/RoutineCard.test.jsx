import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RoutineCard from '../RoutineCard'

// Mock TriggerSelector to simplify tests
vi.mock('../../TriggerSelector', () => ({
  default: vi.fn(({ trigger, onChange, disabled }) => (
    <div data-testid="mock-trigger-selector">
      <span>Trigger: {trigger?.trigger_type}</span>
      <button
        onClick={() => onChange({ trigger_type: 'interval', interval_minutes: 30 })}
        disabled={disabled}
      >
        Change Trigger
      </button>
    </div>
  )),
}))

// Mock ActionList to simplify tests
vi.mock('../../RoutineEditor/ActionList', () => ({
  default: vi.fn(({ actions, onActionsChange, disabled }) => (
    <div data-testid="mock-action-list">
      <span>Actions: {actions?.length || 0}</span>
      <button
        onClick={() =>
          onActionsChange([
            ...actions,
            { id: 'new', action_type: 'camera', action_name: 'takephoto' },
          ])
        }
        disabled={disabled}
      >
        Add Action
      </button>
    </div>
  )),
}))

describe('RoutineCard', () => {
  const defaultRoutine = {
    routine_id: 'test-routine-1',
    name: '',
    trigger: { trigger_type: 'solar', solar_event: 'dusk' },
    actions: [{ id: '1', action_type: 'gpio', action_name: 'attract_on' }],
  }

  const defaultProps = {
    routine: defaultRoutine,
    index: 0,
    onUpdate: vi.fn(),
    onDelete: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('rendering', () => {
    it('renders with auto-generated name', () => {
      render(<RoutineCard {...defaultProps} />)
      expect(screen.getByTestId('routine-name')).toHaveTextContent('Attract On at Dusk')
    })

    it('renders with explicit name when provided', () => {
      render(
        <RoutineCard
          {...defaultProps}
          routine={{ ...defaultRoutine, name: 'My Custom Routine' }}
        />
      )
      expect(screen.getByTestId('routine-name')).toHaveTextContent('My Custom Routine')
    })

    it('renders trigger label', () => {
      render(<RoutineCard {...defaultProps} />)
      expect(screen.getByTestId('trigger-badge')).toHaveTextContent('Solar')
    })

    it('renders action color dot', () => {
      render(<RoutineCard {...defaultProps} />)
      const dot = screen.getByTestId('routine-0').querySelector('.bg-orange-400')
      expect(dot).toBeInTheDocument()
    })

    it('renders blue dot for camera actions', () => {
      render(
        <RoutineCard
          {...defaultProps}
          routine={{
            ...defaultRoutine,
            actions: [{ id: '1', action_type: 'camera', action_name: 'takephoto' }],
          }}
        />
      )
      const dot = screen.getByTestId('routine-0').querySelector('.bg-blue-400')
      expect(dot).toBeInTheDocument()
    })

    it('renders delete button', () => {
      render(<RoutineCard {...defaultProps} />)
      expect(screen.getByTestId('delete-routine-0')).toBeInTheDocument()
    })
  })

  describe('data-testid attributes', () => {
    it('has routine-{index} on container', () => {
      render(<RoutineCard {...defaultProps} index={2} />)
      expect(screen.getByTestId('routine-2')).toBeInTheDocument()
    })

    it('has routine-name on name element', () => {
      render(<RoutineCard {...defaultProps} />)
      expect(screen.getByTestId('routine-name')).toBeInTheDocument()
    })

    it('has trigger-badge on trigger label', () => {
      render(<RoutineCard {...defaultProps} />)
      expect(screen.getByTestId('trigger-badge')).toBeInTheDocument()
    })

    it('has delete-routine-{index} on delete button', () => {
      render(<RoutineCard {...defaultProps} index={1} />)
      expect(screen.getByTestId('delete-routine-1')).toBeInTheDocument()
    })
  })

  describe('expand/collapse', () => {
    it('starts collapsed by default', () => {
      render(<RoutineCard {...defaultProps} />)
      // Check that aria-expanded is false
      const header = screen.getByRole('button', { expanded: false })
      expect(header).toBeInTheDocument()
      // Check that the body has max-h-0 class (collapsed)
      const body = screen.getByTestId('mock-trigger-selector').closest('.overflow-hidden')
      expect(body).toHaveClass('max-h-0')
    })

    it('starts expanded when defaultExpanded is true', () => {
      render(<RoutineCard {...defaultProps} defaultExpanded={true} />)
      // Check that aria-expanded is true
      const header = screen.getByRole('button', { expanded: true })
      expect(header).toBeInTheDocument()
      // Check that the body has max-h-[800px] class (expanded)
      const body = screen.getByTestId('mock-trigger-selector').closest('.overflow-hidden')
      expect(body).toHaveClass('max-h-[800px]')
    })

    it('expands on header click', async () => {
      const user = userEvent.setup()
      render(<RoutineCard {...defaultProps} />)

      const header = screen.getByRole('button', { expanded: false })
      await user.click(header)

      await waitFor(() => {
        const body = screen.getByTestId('mock-trigger-selector').closest('.overflow-hidden')
        expect(body).toHaveClass('max-h-[800px]')
      })
    })

    it('collapses on second header click', async () => {
      const user = userEvent.setup()
      render(<RoutineCard {...defaultProps} defaultExpanded={true} />)

      const header = screen.getByRole('button', { expanded: true })
      await user.click(header)

      await waitFor(() => {
        const body = screen.getByTestId('mock-trigger-selector').closest('.overflow-hidden')
        expect(body).toHaveClass('max-h-0')
      })
    })

    it('expands on Enter key', async () => {
      const user = userEvent.setup()
      render(<RoutineCard {...defaultProps} />)

      const header = screen.getByRole('button', { expanded: false })
      header.focus()
      await user.keyboard('{Enter}')

      await waitFor(() => {
        const body = screen.getByTestId('mock-trigger-selector').closest('.overflow-hidden')
        expect(body).toHaveClass('max-h-[800px]')
      })
    })

    it('expands on Space key', async () => {
      const user = userEvent.setup()
      render(<RoutineCard {...defaultProps} />)

      const header = screen.getByRole('button', { expanded: false })
      header.focus()
      await user.keyboard(' ')

      await waitFor(() => {
        const body = screen.getByTestId('mock-trigger-selector').closest('.overflow-hidden')
        expect(body).toHaveClass('max-h-[800px]')
      })
    })

    it('rotates chevron when expanded', async () => {
      const user = userEvent.setup()
      render(<RoutineCard {...defaultProps} />)

      const chevron = screen.getByTestId('routine-0').querySelector('svg.text-gray-600')
      expect(chevron).not.toHaveClass('rotate-180')

      const header = screen.getByRole('button', { expanded: false })
      await user.click(header)

      await waitFor(() => {
        expect(chevron).toHaveClass('rotate-180')
      })
    })
  })

  describe('delete functionality', () => {
    it('calls onDelete with routine_id when delete clicked', async () => {
      const user = userEvent.setup()
      const onDelete = vi.fn()
      render(<RoutineCard {...defaultProps} onDelete={onDelete} />)

      await user.click(screen.getByTestId('delete-routine-0'))

      expect(onDelete).toHaveBeenCalledWith('test-routine-1')
    })

    it('does not expand card when delete is clicked', async () => {
      const user = userEvent.setup()
      render(<RoutineCard {...defaultProps} />)

      await user.click(screen.getByTestId('delete-routine-0'))

      // Card should remain collapsed
      const body = screen.getByTestId('mock-trigger-selector').closest('.overflow-hidden')
      expect(body).toHaveClass('max-h-0')
    })

    it('disables delete button when disabled prop is true', () => {
      render(<RoutineCard {...defaultProps} disabled={true} />)
      expect(screen.getByTestId('delete-routine-0')).toBeDisabled()
    })
  })

  describe('editing functionality', () => {
    it('calls onUpdate when trigger changes', async () => {
      const user = userEvent.setup()
      const onUpdate = vi.fn()
      render(<RoutineCard {...defaultProps} onUpdate={onUpdate} defaultExpanded={true} />)

      await user.click(screen.getByText('Change Trigger'))

      expect(onUpdate).toHaveBeenCalledWith({
        ...defaultRoutine,
        trigger: { trigger_type: 'interval', interval_minutes: 30 },
      })
    })

    it('calls onUpdate when actions change', async () => {
      const user = userEvent.setup()
      const onUpdate = vi.fn()
      render(<RoutineCard {...defaultProps} onUpdate={onUpdate} defaultExpanded={true} />)

      await user.click(screen.getByText('Add Action'))

      expect(onUpdate).toHaveBeenCalledWith({
        ...defaultRoutine,
        actions: [
          ...defaultRoutine.actions,
          { id: 'new', action_type: 'camera', action_name: 'takephoto' },
        ],
      })
    })

    it('passes disabled prop to child components', () => {
      render(<RoutineCard {...defaultProps} disabled={true} defaultExpanded={true} />)

      expect(screen.getByText('Change Trigger')).toBeDisabled()
      expect(screen.getByText('Add Action')).toBeDisabled()
    })
  })

  describe('styling', () => {
    it('has correct border color when collapsed', () => {
      render(<RoutineCard {...defaultProps} />)
      const card = screen.getByTestId('routine-0')
      expect(card).toHaveClass('border-gray-800')
    })

    it('has different border color when expanded', async () => {
      const user = userEvent.setup()
      render(<RoutineCard {...defaultProps} />)

      const header = screen.getByRole('button', { expanded: false })
      await user.click(header)

      const card = screen.getByTestId('routine-0')
      expect(card).toHaveClass('border-gray-700')
    })
  })
})
