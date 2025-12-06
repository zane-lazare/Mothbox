import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AdvancedSearchBuilder } from '../AdvancedSearchBuilder'

describe('AdvancedSearchBuilder', () => {
  describe('rendering', () => {
    it('should render the builder dialog', () => {
      render(<AdvancedSearchBuilder onQueryChange={() => {}} onClose={() => {}} />)
      expect(screen.getByText(/advanced search/i)).toBeInTheDocument()
    })

    it('should render close button', () => {
      render(<AdvancedSearchBuilder onQueryChange={() => {}} onClose={() => {}} />)
      expect(screen.getByLabelText(/close/i)).toBeInTheDocument()
    })

    it('should render initial condition row', () => {
      render(<AdvancedSearchBuilder onQueryChange={() => {}} onClose={() => {}} />)
      expect(screen.getByLabelText(/field/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/operator/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/value/i)).toBeInTheDocument()
    })
  })

  describe('adding conditions', () => {
    it('should add new condition when clicking add button', async () => {
      const user = userEvent.setup()
      render(<AdvancedSearchBuilder onQueryChange={() => {}} onClose={() => {}} />)

      const addButton = screen.getByText(/add condition/i)
      await user.click(addButton)

      // Should now have 2 value inputs
      expect(screen.getAllByLabelText(/value/i)).toHaveLength(2)
    })

    it('should show boolean operator between conditions', async () => {
      const user = userEvent.setup()
      render(<AdvancedSearchBuilder onQueryChange={() => {}} onClose={() => {}} />)

      await user.click(screen.getByText(/add condition/i))

      expect(screen.getByLabelText(/combine with/i)).toBeInTheDocument()
    })

    it('should allow removing conditions', async () => {
      const user = userEvent.setup()
      render(<AdvancedSearchBuilder onQueryChange={() => {}} onClose={() => {}} />)

      await user.click(screen.getByText(/add condition/i))
      const removeButtons = screen.getAllByLabelText(/remove/i)
      await user.click(removeButtons[0])

      expect(screen.getAllByLabelText(/value/i)).toHaveLength(1)
    })
  })

  describe('query generation', () => {
    it('should generate simple tag query', async () => {
      const user = userEvent.setup()
      const onQueryChange = vi.fn()
      render(<AdvancedSearchBuilder onQueryChange={onQueryChange} onClose={() => {}} />)

      // Select Tags field
      await user.selectOptions(screen.getByLabelText(/field/i), 'tags')
      // Enter value
      await user.type(screen.getByLabelText(/value/i), 'moth')

      // Click apply
      await user.click(screen.getByText(/apply/i))

      expect(onQueryChange).toHaveBeenCalledWith('tag:moth')
    })

    it('should generate phrase query for equals operator', async () => {
      const user = userEvent.setup()
      const onQueryChange = vi.fn()
      render(<AdvancedSearchBuilder onQueryChange={onQueryChange} onClose={() => {}} />)

      await user.selectOptions(screen.getByLabelText(/field/i), 'species')
      await user.selectOptions(screen.getByLabelText(/operator/i), 'equals')
      await user.type(screen.getByLabelText(/value/i), 'Actias luna')

      await user.click(screen.getByText(/apply/i))

      expect(onQueryChange).toHaveBeenCalledWith('species:"Actias luna"')
    })

    it('should generate prefix query for starts with', async () => {
      const user = userEvent.setup()
      const onQueryChange = vi.fn()
      render(<AdvancedSearchBuilder onQueryChange={onQueryChange} onClose={() => {}} />)

      await user.selectOptions(screen.getByLabelText(/field/i), 'tags')
      await user.selectOptions(screen.getByLabelText(/operator/i), 'starts_with')
      await user.type(screen.getByLabelText(/value/i), 'noc')

      await user.click(screen.getByText(/apply/i))

      expect(onQueryChange).toHaveBeenCalledWith('tag:noc*')
    })

    it('should generate NOT query for excludes', async () => {
      const user = userEvent.setup()
      const onQueryChange = vi.fn()
      render(<AdvancedSearchBuilder onQueryChange={onQueryChange} onClose={() => {}} />)

      await user.selectOptions(screen.getByLabelText(/field/i), 'tags')
      await user.selectOptions(screen.getByLabelText(/operator/i), 'excludes')
      await user.type(screen.getByLabelText(/value/i), 'butterfly')

      await user.click(screen.getByText(/apply/i))

      expect(onQueryChange).toHaveBeenCalledWith('NOT tag:butterfly')
    })

    it('should combine conditions with AND', async () => {
      const user = userEvent.setup()
      const onQueryChange = vi.fn()
      render(<AdvancedSearchBuilder onQueryChange={onQueryChange} onClose={() => {}} />)

      // First condition
      await user.selectOptions(screen.getByLabelText(/field/i), 'tags')
      await user.type(screen.getByLabelText(/value/i), 'moth')

      // Add second condition
      await user.click(screen.getByText(/add condition/i))

      const fields = screen.getAllByLabelText(/field/i)
      const values = screen.getAllByLabelText(/value/i)

      await user.selectOptions(fields[1], 'species')
      await user.type(values[1], 'actias')

      await user.click(screen.getByText(/apply/i))

      expect(onQueryChange).toHaveBeenCalledWith('tag:moth AND species:actias')
    })

    it('should combine conditions with OR when selected', async () => {
      const user = userEvent.setup()
      const onQueryChange = vi.fn()
      render(<AdvancedSearchBuilder onQueryChange={onQueryChange} onClose={() => {}} />)

      await user.selectOptions(screen.getByLabelText(/field/i), 'tags')
      await user.type(screen.getByLabelText(/value/i), 'moth')

      await user.click(screen.getByText(/add condition/i))
      await user.selectOptions(screen.getByLabelText(/combine with/i), 'OR')

      const fields = screen.getAllByLabelText(/field/i)
      const values = screen.getAllByLabelText(/value/i)

      await user.selectOptions(fields[1], 'tags')
      await user.type(values[1], 'butterfly')

      await user.click(screen.getByText(/apply/i))

      expect(onQueryChange).toHaveBeenCalledWith('tag:moth OR tag:butterfly')
    })
  })

  describe('date range', () => {
    it('should render date range inputs', () => {
      render(<AdvancedSearchBuilder onQueryChange={() => {}} onClose={() => {}} />)
      expect(screen.getByLabelText(/from date/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/to date/i)).toBeInTheDocument()
    })

    it('should include date range in query', async () => {
      const user = userEvent.setup()
      const onQueryChange = vi.fn()
      render(<AdvancedSearchBuilder onQueryChange={onQueryChange} onClose={() => {}} />)

      await user.type(screen.getByLabelText(/from date/i), '2024-01-01')
      await user.type(screen.getByLabelText(/to date/i), '2024-12-31')

      await user.click(screen.getByText(/apply/i))

      expect(onQueryChange).toHaveBeenCalledWith(expect.stringContaining('date:2024-01-01..2024-12-31'))
    })
  })

  describe('query preview', () => {
    it('should show generated query preview', async () => {
      const user = userEvent.setup()
      render(<AdvancedSearchBuilder onQueryChange={() => {}} onClose={() => {}} />)

      await user.selectOptions(screen.getByLabelText(/field/i), 'tags')
      await user.type(screen.getByLabelText(/value/i), 'moth')

      expect(screen.getByTestId('query-preview')).toHaveTextContent('tag:moth')
    })
  })

  describe('clear all', () => {
    it('should reset all conditions when clear clicked', async () => {
      const user = userEvent.setup()
      render(<AdvancedSearchBuilder onQueryChange={() => {}} onClose={() => {}} />)

      await user.type(screen.getByLabelText(/value/i), 'moth')
      await user.click(screen.getByText(/clear all/i))

      expect(screen.getByLabelText(/value/i)).toHaveValue('')
    })
  })

  describe('close behavior', () => {
    it('should call onClose when close button clicked', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()
      render(<AdvancedSearchBuilder onQueryChange={() => {}} onClose={onClose} />)

      await user.click(screen.getByLabelText(/close/i))
      expect(onClose).toHaveBeenCalled()
    })
  })

  describe('initial query parsing', () => {
    it('should parse initial query into conditions', () => {
      render(
        <AdvancedSearchBuilder
          onQueryChange={() => {}}
          onClose={() => {}}
          initialQuery="tag:moth"
        />
      )

      expect(screen.getByLabelText(/field/i)).toHaveValue('tags')
      expect(screen.getByLabelText(/value/i)).toHaveValue('moth')
    })
  })
})
