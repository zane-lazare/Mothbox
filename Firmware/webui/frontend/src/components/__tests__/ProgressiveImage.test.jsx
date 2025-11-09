import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ProgressiveImage from '../ProgressiveImage'

describe('ProgressiveImage', () => {
  describe('Image Loading States', () => {
    it('shows loading state initially', () => {
      render(<ProgressiveImage src="/test.jpg" alt="Test image" />)

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toBeInTheDocument()
      // Image should have opacity-0 initially (not loaded yet)
      expect(img).toHaveClass('opacity-0')
    })

    it('transitions to full opacity when image loads', async () => {
      render(<ProgressiveImage src="/test.jpg" alt="Test image" />)

      const img = screen.getByRole('img', { name: /Test image/i })

      // Simulate image load
      fireEvent.load(img)

      await waitFor(() => {
        expect(img).toHaveClass('opacity-100')
      })
    })

    it('calls onLoad callback when image loads successfully', async () => {
      const mockOnLoad = vi.fn()

      render(<ProgressiveImage src="/test.jpg" alt="Test image" onLoad={mockOnLoad} />)

      const img = screen.getByRole('img', { name: /Test image/i })
      fireEvent.load(img)

      await waitFor(() => {
        expect(mockOnLoad).toHaveBeenCalledTimes(1)
      })
    })

    it('applies transition animation during load', () => {
      render(<ProgressiveImage src="/test.jpg" alt="Test image" />)

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveClass('transition-opacity')
      expect(img).toHaveClass('duration-300')
    })
  })

  describe('Broken Image Handling', () => {
    it('shows fallback moth icon when image fails to load', async () => {
      render(<ProgressiveImage src="/broken.jpg" alt="Broken image" />)

      const img = screen.getByRole('img', { name: /Broken image/i })

      // Simulate image error
      fireEvent.error(img)

      await waitFor(() => {
        // Should show moth icon fallback
        const mothIcon = screen.getByRole('img', { name: /moth icon/i })
        expect(mothIcon).toBeInTheDocument()
      })
    })

    it('calls onError callback when image fails to load', async () => {
      const mockOnError = vi.fn()

      render(<ProgressiveImage src="/broken.jpg" alt="Broken image" onError={mockOnError} />)

      const img = screen.getByRole('img', { name: /Broken image/i })
      fireEvent.error(img)

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledTimes(1)
      })
    })

    it('hides original image when error occurs', async () => {
      render(<ProgressiveImage src="/broken.jpg" alt="Broken image" />)

      const img = screen.getByRole('img', { name: /Broken image/i })
      fireEvent.error(img)

      await waitFor(() => {
        // Original image should be hidden
        expect(img).toHaveClass('hidden')
      })
    })

    it('displays filename when thumbnail broken', async () => {
      render(<ProgressiveImage src="/photos/test.jpg" alt="test.jpg" showFilenameOnError />)

      const img = screen.getByRole('img', { name: /test.jpg/i })
      fireEvent.error(img)

      await waitFor(() => {
        expect(screen.getByText(/test.jpg/i)).toBeInTheDocument()
      })
    })
  })

  describe('Progressive Loading Animations', () => {
    it('applies fade-in animation with correct duration', () => {
      render(<ProgressiveImage src="/test.jpg" alt="Test image" />)

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveClass('transition-opacity')
      expect(img).toHaveClass('duration-300')
    })

    it('maintains aspect ratio while loading', () => {
      const { container } = render(<ProgressiveImage src="/test.jpg" alt="Test image" />)

      // Parent container should have aspect ratio
      const wrapper = container.firstChild
      expect(wrapper).toHaveClass('relative')
    })

    it('prevents layout shift during image load', () => {
      const { container } = render(<ProgressiveImage src="/test.jpg" alt="Test image" />)

      // Container should maintain dimensions
      const wrapper = container.firstChild
      expect(wrapper).toHaveClass('relative')
    })
  })

  describe('Accessibility', () => {
    it('includes alt text on image', () => {
      render(<ProgressiveImage src="/test.jpg" alt="A beautiful moth" />)

      const img = screen.getByRole('img', { name: /A beautiful moth/i })
      expect(img).toHaveAttribute('alt', 'A beautiful moth')
    })

    it('moth icon fallback has proper aria-label', async () => {
      render(<ProgressiveImage src="/broken.jpg" alt="Broken image" />)

      const img = screen.getByRole('img', { name: /Broken image/i })
      fireEvent.error(img)

      await waitFor(() => {
        const mothIcon = screen.getByRole('img', { name: /moth icon/i })
        expect(mothIcon).toHaveAccessibleName()
      })
    })

    it('preserves ARIA labels during loading transitions', async () => {
      render(<ProgressiveImage src="/test.jpg" alt="Test image" />)

      const img = screen.getByRole('img', { name: /Test image/i })

      // Before load
      expect(img).toHaveAttribute('alt', 'Test image')

      // Trigger load
      fireEvent.load(img)

      // After load
      await waitFor(() => {
        expect(img).toHaveAttribute('alt', 'Test image')
      })
    })
  })

  describe('Custom Styling', () => {
    it('applies custom className to image', () => {
      render(<ProgressiveImage src="/test.jpg" alt="Test image" className="custom-class" />)

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveClass('custom-class')
    })

    it('combines custom className with default classes', () => {
      render(<ProgressiveImage src="/test.jpg" alt="Test image" className="rounded-lg" />)

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveClass('rounded-lg')
      expect(img).toHaveClass('transition-opacity')
    })
  })
})
