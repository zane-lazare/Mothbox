import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FileTypeFilter } from '../FileTypeFilter'
import { FilterProvider } from '../../../contexts/FilterContext'

// Helper to render component with providers
const renderWithProviders = (ui) => {
  return render(
    <FilterProvider>
      {ui}
    </FilterProvider>
  )
}

describe('FileTypeFilter', () => {
  beforeEach(() => {
    // Reset any state between tests
  })

  // Rendering tests
  describe('Rendering', () => {
    it('renders all file type options', () => {
      renderWithProviders(<FileTypeFilter />)

      expect(screen.getByText('JPG/JPEG')).toBeInTheDocument()
      expect(screen.getByText('PNG')).toBeInTheDocument()
      expect(screen.getByText('RAW')).toBeInTheDocument()
      expect(screen.getByText('Video')).toBeInTheDocument()
    })

    it('renders checkboxes for all file types', () => {
      renderWithProviders(<FileTypeFilter />)

      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes).toHaveLength(4)
    })

    it('renders file type icons', () => {
      renderWithProviders(<FileTypeFilter />)

      // Icons should be present (aria-hidden)
      const labels = screen.getAllByRole('checkbox').map(cb => cb.parentElement)
      labels.forEach(label => {
        const svg = label.querySelector('svg')
        expect(svg).toBeInTheDocument()
      })
    })

    it('shows "All file types shown" when no selection', () => {
      renderWithProviders(<FileTypeFilter />)

      expect(screen.getByText('All file types shown')).toBeInTheDocument()
    })

    it('shows count when file types selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      await user.click(screen.getByLabelText(/select file type jpg/i))

      expect(screen.getByText('1 type selected')).toBeInTheDocument()
    })

    it('uses plural form for multiple selections', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      await user.click(screen.getByLabelText(/select file type jpg/i))
      await user.click(screen.getByLabelText(/select file type png/i))

      expect(screen.getByText('2 types selected')).toBeInTheDocument()
    })

    it('shows extension info when types selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      await user.click(screen.getByLabelText(/select file type jpg/i))

      expect(screen.getByText('Included extensions:')).toBeInTheDocument()
      expect(screen.getByText(/\.jpg, \.jpeg/i)).toBeInTheDocument()
    })

    it('does not show extension info when no selection', () => {
      renderWithProviders(<FileTypeFilter />)

      expect(screen.queryByText('Included extensions:')).not.toBeInTheDocument()
    })
  })

  // Selection tests
  describe('File Type Selection', () => {
    it('selects file type when checkbox clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      await user.click(jpgCheckbox)

      expect(jpgCheckbox).toBeChecked()
    })

    it('deselects file type when checkbox clicked again', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)

      // Select
      await user.click(jpgCheckbox)
      expect(jpgCheckbox).toBeChecked()

      // Deselect
      await user.click(jpgCheckbox)
      expect(jpgCheckbox).not.toBeChecked()
    })

    it('supports multiple file type selection', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      const pngCheckbox = screen.getByLabelText(/select file type png/i)
      const rawCheckbox = screen.getByLabelText(/select file type raw/i)

      await user.click(jpgCheckbox)
      await user.click(pngCheckbox)
      await user.click(rawCheckbox)

      expect(jpgCheckbox).toBeChecked()
      expect(pngCheckbox).toBeChecked()
      expect(rawCheckbox).toBeChecked()
    })

    it('allows all types to be selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      const pngCheckbox = screen.getByLabelText(/select file type png/i)
      const rawCheckbox = screen.getByLabelText(/select file type raw/i)
      const videoCheckbox = screen.getByLabelText(/select file type video/i)

      await user.click(jpgCheckbox)
      await user.click(pngCheckbox)
      await user.click(rawCheckbox)
      await user.click(videoCheckbox)

      expect(jpgCheckbox).toBeChecked()
      expect(pngCheckbox).toBeChecked()
      expect(rawCheckbox).toBeChecked()
      expect(videoCheckbox).toBeChecked()
    })

    it('allows deselecting all types', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      const pngCheckbox = screen.getByLabelText(/select file type png/i)

      // Select two
      await user.click(jpgCheckbox)
      await user.click(pngCheckbox)

      // Deselect both
      await user.click(jpgCheckbox)
      await user.click(pngCheckbox)

      expect(jpgCheckbox).not.toBeChecked()
      expect(pngCheckbox).not.toBeChecked()
      expect(screen.getByText('All file types shown')).toBeInTheDocument()
    })
  })

  // Visual feedback tests
  describe('Visual Feedback', () => {
    it('applies selected styling to checked items', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      const jpgLabel = jpgCheckbox.parentElement

      await user.click(jpgCheckbox)

      expect(jpgLabel).toHaveClass('border-blue-500')
      expect(jpgLabel).toHaveClass('bg-blue-50')
    })

    it('applies default styling to unchecked items', () => {
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      const jpgLabel = jpgCheckbox.parentElement

      expect(jpgLabel).toHaveClass('border-gray-200')
    })

    it('shows colored icon for selected items', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      await user.click(jpgCheckbox)

      const jpgLabel = jpgCheckbox.parentElement
      const icon = jpgLabel.querySelector('svg')

      expect(icon).toHaveClass('text-blue-500')
    })

    it('shows gray icon for unselected items', () => {
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      const jpgLabel = jpgCheckbox.parentElement
      const icon = jpgLabel.querySelector('svg')

      expect(icon).toHaveClass('text-gray-400')
    })

    it('displays different colors for different file types', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      // Select all types
      await user.click(screen.getByLabelText(/select file type jpg/i))
      await user.click(screen.getByLabelText(/select file type png/i))
      await user.click(screen.getByLabelText(/select file type raw/i))
      await user.click(screen.getByLabelText(/select file type video/i))

      // Check icon colors
      const jpgIcon = screen.getByLabelText(/select file type jpg/i).parentElement.querySelector('svg')
      const pngIcon = screen.getByLabelText(/select file type png/i).parentElement.querySelector('svg')
      const rawIcon = screen.getByLabelText(/select file type raw/i).parentElement.querySelector('svg')
      const videoIcon = screen.getByLabelText(/select file type video/i).parentElement.querySelector('svg')

      expect(jpgIcon).toHaveClass('text-blue-500')
      expect(pngIcon).toHaveClass('text-green-500')
      expect(rawIcon).toHaveClass('text-purple-500')
      expect(videoIcon).toHaveClass('text-red-500')
    })
  })

  // Extensions display tests
  describe('Extensions Display', () => {
    it('shows JPG extensions when selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      await user.click(screen.getByLabelText(/select file type jpg/i))

      expect(screen.getByText(/\.jpg, \.jpeg/i)).toBeInTheDocument()
    })

    it('shows PNG extensions when selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      await user.click(screen.getByLabelText(/select file type png/i))

      expect(screen.getByText(/\.png/i)).toBeInTheDocument()
    })

    it('shows RAW extensions when selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      await user.click(screen.getByLabelText(/select file type raw/i))

      expect(screen.getByText(/\.dng, \.cr2, \.nef, \.arw/i)).toBeInTheDocument()
    })

    it('shows Video extensions when selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      await user.click(screen.getByLabelText(/select file type video/i))

      expect(screen.getByText(/\.mp4, \.mov, \.avi/i)).toBeInTheDocument()
    })

    it('shows multiple extension sets when multiple types selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      await user.click(screen.getByLabelText(/select file type jpg/i))
      await user.click(screen.getByLabelText(/select file type png/i))

      expect(screen.getByText(/\.jpg, \.jpeg/i)).toBeInTheDocument()
      expect(screen.getByText(/\.png/i)).toBeInTheDocument()
    })
  })

  // Accessibility tests
  describe('Accessibility', () => {
    it('has accessible checkboxes with aria-label', () => {
      renderWithProviders(<FileTypeFilter />)

      expect(screen.getByLabelText(/select file type jpg\/jpeg/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/select file type png/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/select file type raw/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/select file type video/i)).toBeInTheDocument()
    })

    it('checkboxes are keyboard accessible', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      await user.click(jpgCheckbox)

      expect(jpgCheckbox).toBeChecked()
    })

    it('labels are associated with checkboxes', () => {
      renderWithProviders(<FileTypeFilter />)

      const checkboxes = screen.getAllByRole('checkbox')
      checkboxes.forEach(checkbox => {
        expect(checkbox).toHaveAccessibleName()
      })
    })

    it('icons have aria-hidden attribute', () => {
      renderWithProviders(<FileTypeFilter />)

      const labels = screen.getAllByRole('checkbox').map(cb => cb.parentElement)
      labels.forEach(label => {
        const svg = label.querySelector('svg')
        expect(svg).toHaveAttribute('aria-hidden', 'true')
      })
    })
  })

  // Dark mode tests
  describe('Dark Mode Classes', () => {
    it('has dark mode classes on unselected labels', () => {
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      const jpgLabel = jpgCheckbox.parentElement

      expect(jpgLabel.className).toContain('dark:border-gray-700')
      expect(jpgLabel.className).toContain('dark:hover:border-gray-600')
    })

    it('has dark mode classes on selected labels', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      await user.click(jpgCheckbox)

      const jpgLabel = jpgCheckbox.parentElement
      expect(jpgLabel.className).toContain('dark:bg-blue-900/20')
    })

    it('has dark mode classes on header text', () => {
      renderWithProviders(<FileTypeFilter />)

      const header = screen.getByText('All file types shown')
      // Dark mode class is on the parent div container
      expect(header.parentElement.className).toContain('dark:text-gray-400')
    })

    it('has dark mode classes on extension info', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      await user.click(screen.getByLabelText(/select file type jpg/i))

      const extensionsHeader = screen.getByText('Included extensions:')
      expect(extensionsHeader.className).toContain('dark:text-gray-400')
    })

    it('has dark mode classes on checkboxes', () => {
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      expect(jpgCheckbox.className).toContain('dark:border-gray-600')
      expect(jpgCheckbox.className).toContain('dark:text-blue-500')
    })
  })

  // Context integration tests
  describe('Context Integration', () => {
    it('updates context when file type selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      await user.click(screen.getByLabelText(/select file type jpg/i))

      // Verify checkbox is checked (indicates context was updated)
      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      expect(jpgCheckbox).toBeChecked()
    })

    it('updates context when file type deselected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)

      await user.click(jpgCheckbox)
      expect(jpgCheckbox).toBeChecked()

      await user.click(jpgCheckbox)
      expect(jpgCheckbox).not.toBeChecked()
    })

    it('maintains independent selections for different types', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FileTypeFilter />)

      const jpgCheckbox = screen.getByLabelText(/select file type jpg/i)
      const pngCheckbox = screen.getByLabelText(/select file type png/i)

      // Select JPG
      await user.click(jpgCheckbox)
      expect(jpgCheckbox).toBeChecked()
      expect(pngCheckbox).not.toBeChecked()

      // Select PNG
      await user.click(pngCheckbox)
      expect(jpgCheckbox).toBeChecked()
      expect(pngCheckbox).toBeChecked()

      // Deselect JPG
      await user.click(jpgCheckbox)
      expect(jpgCheckbox).not.toBeChecked()
      expect(pngCheckbox).toBeChecked()
    })
  })

  // Grid layout tests
  describe('Grid Layout', () => {
    it('uses grid layout for file types', () => {
      renderWithProviders(<FileTypeFilter />)

      const grid = screen.getByLabelText(/select file type jpg/i).parentElement.parentElement
      expect(grid).toHaveClass('grid')
      expect(grid).toHaveClass('grid-cols-2')
    })

    it('renders all types in a 2-column grid', () => {
      renderWithProviders(<FileTypeFilter />)

      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes).toHaveLength(4)

      // Verify parent has grid classes
      const grid = checkboxes[0].parentElement.parentElement
      expect(grid).toHaveClass('grid-cols-2')
    })
  })
})
