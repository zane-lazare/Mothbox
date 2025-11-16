import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ProgressiveImage from '../ProgressiveImage'

// Mock useProgressiveImage hook
vi.mock('../../hooks/useProgressiveImage', () => ({
  default: vi.fn()
}))

// Mock MothIcon component
vi.mock('../MothIcon', () => ({
  default: vi.fn(({ size }) => (
    <svg role="img" aria-label="moth icon" width={size} height={size}>
      <text>Moth Icon</text>
    </svg>
  ))
}))

import useProgressiveImage from '../../hooks/useProgressiveImage'

describe('ProgressiveImage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Progressive Loading Mode (with photoPath)', () => {
    it('uses progressive loading hook when photoPath is provided', () => {
      useProgressiveImage.mockReturnValue({
        src: null,
        isLoading: true,
        error: null,
        stage: 'idle'
      })

      render(<ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" />)

      expect(useProgressiveImage).toHaveBeenCalledWith('2024/photo.jpg', {
        thumbnailSize: 64,
        fullSize: 256,
        autoLoad: true
      })
    })

    it('shows blurred thumbnail during loading', () => {
      useProgressiveImage.mockReturnValue({
        src: '/api/photos/thumbnail?path=2024/photo.jpg&size=64',
        isLoading: false,
        error: null,
        stage: 'thumbnail'
      })

      render(<ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" />)

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveClass('blur-sm')
      expect(img).toHaveClass('opacity-80')
      expect(img).toHaveClass('scale-105')
    })

    it('removes blur when full image loads', () => {
      useProgressiveImage.mockReturnValue({
        src: '/api/photos/thumbnail?path=2024/photo.jpg&size=256',
        isLoading: false,
        error: null,
        stage: 'loaded'
      })

      render(<ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" />)

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveClass('blur-0')
      expect(img).toHaveClass('opacity-100')
      expect(img).toHaveClass('scale-100')
    })

    it('shows moth icon fallback when progressive loading fails', () => {
      useProgressiveImage.mockReturnValue({
        src: null,
        isLoading: false,
        error: new Error('Failed to load'),
        stage: 'error'
      })

      render(<ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" iconSize={100} />)

      const mothIcon = screen.getByRole('img', { name: /moth icon/i })
      expect(mothIcon).toBeInTheDocument()
      expect(mothIcon).toHaveAttribute('width', '100')
      expect(mothIcon).toHaveAttribute('height', '100')
    })

    it('calls onLoad callback when full image loads', () => {
      const mockOnLoad = vi.fn()

      // First render with thumbnail
      const { rerender } = render(
        <ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" onLoad={mockOnLoad} />
      )

      useProgressiveImage.mockReturnValue({
        src: '/api/photos/thumbnail?path=2024/photo.jpg&size=64',
        isLoading: false,
        error: null,
        stage: 'thumbnail'
      })

      expect(mockOnLoad).not.toHaveBeenCalled()

      // Update to loaded stage
      useProgressiveImage.mockReturnValue({
        src: '/api/photos/thumbnail?path=2024/photo.jpg&size=256',
        isLoading: false,
        error: null,
        stage: 'loaded'
      })

      rerender(<ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" onLoad={mockOnLoad} />)

      expect(mockOnLoad).toHaveBeenCalledTimes(1)
    })

    it('calls onError callback when progressive loading fails', () => {
      const mockOnError = vi.fn()
      const error = new Error('Failed to load')

      useProgressiveImage.mockReturnValue({
        src: null,
        isLoading: false,
        error,
        stage: 'error'
      })

      render(<ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" onError={mockOnError} />)

      expect(mockOnError).toHaveBeenCalledWith(error)
    })

    it('displays filename when showFilenameOnError is true', () => {
      useProgressiveImage.mockReturnValue({
        src: null,
        isLoading: false,
        error: new Error('Failed to load'),
        stage: 'error'
      })

      render(
        <ProgressiveImage
          photoPath="2024/photo.jpg"
          alt="photo.jpg"
          showFilenameOnError
        />
      )

      expect(screen.getByText(/photo.jpg/i)).toBeInTheDocument()
    })

    it('applies custom thumbnailSize and fullSize', () => {
      useProgressiveImage.mockReturnValue({
        src: null,
        isLoading: true,
        error: null,
        stage: 'idle'
      })

      render(
        <ProgressiveImage
          photoPath="2024/photo.jpg"
          alt="Test image"
          thumbnailSize={128}
          fullSize={512}
        />
      )

      expect(useProgressiveImage).toHaveBeenCalledWith('2024/photo.jpg', {
        thumbnailSize: 128,
        fullSize: 512,
        autoLoad: true
      })
    })

    it('can disable progressive loading with progressive=false', () => {
      useProgressiveImage.mockReturnValue({
        src: null,
        isLoading: false,
        error: null,
        stage: 'idle'
      })

      render(
        <ProgressiveImage
          photoPath="2024/photo.jpg"
          src="/fallback.jpg"
          alt="Test image"
          progressive={false}
        />
      )

      // Should not use progressive hook
      expect(useProgressiveImage).toHaveBeenCalledWith(null, {
        thumbnailSize: 64,
        fullSize: 256,
        autoLoad: false
      })

      // Should use fallback src
      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveAttribute('src', '/fallback.jpg')
    })
  })

  describe('Backward Compatibility Mode (with src only)', () => {
    beforeEach(() => {
      // Mock hook to return idle state (not used)
      useProgressiveImage.mockReturnValue({
        src: null,
        isLoading: false,
        error: null,
        stage: 'idle'
      })
    })

    it('renders image with src when photoPath not provided', () => {
      render(<ProgressiveImage src="/test.jpg" alt="Test image" />)

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toBeInTheDocument()
      expect(img).toHaveAttribute('src', '/test.jpg')
    })

    it('does not use progressive hook when only src provided', () => {
      render(<ProgressiveImage src="/test.jpg" alt="Test image" />)

      expect(useProgressiveImage).toHaveBeenCalledWith(null, {
        thumbnailSize: 64,
        fullSize: 256,
        autoLoad: false
      })
    })

    it('does not show blur effect in backward compatibility mode', () => {
      render(<ProgressiveImage src="/test.jpg" alt="Test image" />)

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveClass('blur-0')
      expect(img).toHaveClass('opacity-100')
      expect(img).toHaveClass('scale-100')
    })

    it('calls onError callback when src image fails to load', async () => {
      const mockOnError = vi.fn()

      render(<ProgressiveImage src="/broken.jpg" alt="Broken image" onError={mockOnError} />)

      const img = screen.getByRole('img', { name: /Broken image/i })
      fireEvent.error(img)

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalled()
      })
    })

    it('does not show moth icon fallback for src-only errors', async () => {
      render(<ProgressiveImage src="/broken.jpg" alt="Broken image" />)

      const img = screen.getByRole('img', { name: /Broken image/i })
      fireEvent.error(img)

      // Should not show moth icon (backward compatibility - just shows broken image icon)
      await waitFor(() => {
        expect(screen.queryByRole('img', { name: /moth icon/i })).not.toBeInTheDocument()
      })
    })
  })

  describe('Styling and Animations', () => {
    it('applies transition-all with 300ms duration', () => {
      useProgressiveImage.mockReturnValue({
        src: '/api/photos/thumbnail?path=2024/photo.jpg&size=256',
        isLoading: false,
        error: null,
        stage: 'loaded'
      })

      render(<ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" />)

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveClass('transition-all')
      expect(img).toHaveClass('duration-300')
    })

    it('applies custom className to image', () => {
      useProgressiveImage.mockReturnValue({
        src: '/api/photos/thumbnail?path=2024/photo.jpg&size=256',
        isLoading: false,
        error: null,
        stage: 'loaded'
      })

      render(<ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" className="custom-class" />)

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveClass('custom-class')
      expect(img).toHaveClass('transition-all')
    })

    it('applies className to error fallback container', () => {
      useProgressiveImage.mockReturnValue({
        src: null,
        isLoading: false,
        error: new Error('Failed'),
        stage: 'error'
      })

      const { container } = render(
        <ProgressiveImage
          photoPath="2024/photo.jpg"
          alt="Test image"
          className="w-48 h-32 rounded"
        />
      )

      const fallbackContainer = container.querySelector('.bg-gray-100')
      expect(fallbackContainer).toHaveClass('w-48')
      expect(fallbackContainer).toHaveClass('h-32')
      expect(fallbackContainer).toHaveClass('rounded')
    })
  })

  describe('Accessibility', () => {
    it('includes alt text on image', () => {
      useProgressiveImage.mockReturnValue({
        src: '/api/photos/thumbnail?path=2024/photo.jpg&size=256',
        isLoading: false,
        error: null,
        stage: 'loaded'
      })

      render(<ProgressiveImage photoPath="2024/photo.jpg" alt="A beautiful moth" />)

      const img = screen.getByRole('img', { name: /A beautiful moth/i })
      expect(img).toHaveAttribute('alt', 'A beautiful moth')
    })

    it('moth icon fallback has proper aria-label', () => {
      useProgressiveImage.mockReturnValue({
        src: null,
        isLoading: false,
        error: new Error('Failed'),
        stage: 'error'
      })

      render(<ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" />)

      const mothIcon = screen.getByRole('img', { name: /moth icon/i })
      expect(mothIcon).toHaveAccessibleName()
    })

    it('preserves ARIA labels during loading transitions', () => {
      const { rerender } = render(
        <ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" />
      )

      useProgressiveImage.mockReturnValue({
        src: '/api/photos/thumbnail?path=2024/photo.jpg&size=64',
        isLoading: false,
        error: null,
        stage: 'thumbnail'
      })

      rerender(<ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" />)

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveAttribute('alt', 'Test image')

      useProgressiveImage.mockReturnValue({
        src: '/api/photos/thumbnail?path=2024/photo.jpg&size=256',
        isLoading: false,
        error: null,
        stage: 'loaded'
      })

      rerender(<ProgressiveImage photoPath="2024/photo.jpg" alt="Test image" />)

      expect(img).toHaveAttribute('alt', 'Test image')
    })
  })

  describe('Edge Cases', () => {
    it('handles null photoPath gracefully', () => {
      useProgressiveImage.mockReturnValue({
        src: null,
        isLoading: false,
        error: null,
        stage: 'idle'
      })

      render(<ProgressiveImage photoPath={null} src="/fallback.jpg" alt="Test image" />)

      // Should fall back to src mode
      expect(useProgressiveImage).toHaveBeenCalledWith(null, expect.any(Object))

      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveAttribute('src', '/fallback.jpg')
    })

    it('handles undefined photoPath gracefully', () => {
      useProgressiveImage.mockReturnValue({
        src: null,
        isLoading: false,
        error: null,
        stage: 'idle'
      })

      render(<ProgressiveImage photoPath={undefined} src="/fallback.jpg" alt="Test image" />)

      // Should fall back to src mode
      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveAttribute('src', '/fallback.jpg')
    })

    it('handles empty string photoPath gracefully', () => {
      useProgressiveImage.mockReturnValue({
        src: null,
        isLoading: false,
        error: null,
        stage: 'idle'
      })

      render(<ProgressiveImage photoPath="" src="/fallback.jpg" alt="Test image" />)

      // Should fall back to src mode
      const img = screen.getByRole('img', { name: /Test image/i })
      expect(img).toHaveAttribute('src', '/fallback.jpg')
    })
  })
})
