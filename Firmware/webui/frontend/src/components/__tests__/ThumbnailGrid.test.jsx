import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ThumbnailGrid from '../ThumbnailGrid'
import { HOVER_POPUP_CONFIG } from '../../constants/config'

describe('ThumbnailGrid', () => {
  const mockPhotos = [
    {
      path: 'photo1.jpg',
      filename: 'photo1.jpg',
      lat: 37.7749,
      lon: -122.4194,
      timestamp: '2024-01-15T10:30:00',
      tags: ['moth', 'night'],
    },
    {
      path: 'photo2.jpg',
      filename: 'photo2.jpg',
      lat: 37.7750,
      lon: -122.4195,
      timestamp: '2024-01-15T10:31:00',
      tags: ['butterfly'],
    },
    {
      path: 'photo3.jpg',
      filename: 'photo3.jpg',
      lat: 37.7751,
      lon: -122.4196,
      timestamp: '2024-01-15T10:32:00',
      tags: ['beetle'],
    },
    {
      path: 'photo4.jpg',
      filename: 'photo4.jpg',
      lat: 37.7752,
      lon: -122.4197,
      timestamp: '2024-01-15T10:33:00',
      tags: [],
    },
    {
      path: 'photo5.jpg',
      filename: 'photo5.jpg',
      lat: 37.7753,
      lon: -122.4198,
      timestamp: '2024-01-15T10:34:00',
      tags: ['moth'],
    },
    {
      path: 'photo6.jpg',
      filename: 'photo6.jpg',
      lat: 37.7754,
      lon: -122.4199,
      timestamp: '2024-01-15T10:35:00',
      tags: [],
    },
    {
      path: 'photo7.jpg',
      filename: 'photo7.jpg',
      lat: 37.7755,
      lon: -122.4200,
      timestamp: '2024-01-15T10:36:00',
      tags: ['dragonfly'],
    },
    {
      path: 'photo8.jpg',
      filename: 'photo8.jpg',
      lat: 37.7756,
      lon: -122.4201,
      timestamp: '2024-01-15T10:37:00',
      tags: [],
    },
    {
      path: 'photo9.jpg',
      filename: 'photo9.jpg',
      lat: 37.7757,
      lon: -122.4202,
      timestamp: '2024-01-15T10:38:00',
      tags: ['spider'],
    },
    {
      path: 'photo10.jpg',
      filename: 'photo10.jpg',
      lat: 37.7758,
      lon: -122.4203,
      timestamp: '2024-01-15T10:39:00',
      tags: [],
    },
    {
      path: 'photo11.jpg',
      filename: 'photo11.jpg',
      lat: 37.7759,
      lon: -122.4204,
      timestamp: '2024-01-15T10:40:00',
      tags: ['wasp'],
    },
  ]

  let mockOnPhotoClick

  beforeEach(() => {
    mockOnPhotoClick = vi.fn()
  })

  describe('Rendering', () => {
    it('renders correct number of thumbnails up to maxPhotos', () => {
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const images = screen.getAllByRole('img')
      expect(images).toHaveLength(9)
    })

    it('renders all photos when photos.length < maxPhotos', () => {
      const fewPhotos = mockPhotos.slice(0, 5)
      render(<ThumbnailGrid photos={fewPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const images = screen.getAllByRole('img')
      expect(images).toHaveLength(5)
    })

    it('uses default maxPhotos from config when not specified', () => {
      render(<ThumbnailGrid photos={mockPhotos} onPhotoClick={mockOnPhotoClick} />)

      const images = screen.getAllByRole('img')
      expect(images).toHaveLength(HOVER_POPUP_CONFIG.MAX_PHOTOS)
    })

    it('each thumbnail has correct src URL', () => {
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const images = screen.getAllByRole('img')
      images.forEach((img, index) => {
        const photoPath = mockPhotos[index].path
        expect(img).toHaveAttribute(
          'src',
          `/api/gallery/thumbnail/${photoPath}?size=${HOVER_POPUP_CONFIG.THUMBNAIL_SIZE}`
        )
      })
    })

    it('each thumbnail has alt text', () => {
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const images = screen.getAllByRole('img')
      images.forEach((img, index) => {
        expect(img).toHaveAttribute('alt', mockPhotos[index].filename)
      })
    })

    it('uses custom thumbnailSize when provided', () => {
      const customSize = 256
      render(
        <ThumbnailGrid
          photos={mockPhotos}
          maxPhotos={9}
          thumbnailSize={customSize}
          onPhotoClick={mockOnPhotoClick}
        />
      )

      const images = screen.getAllByRole('img')
      images.forEach((img, index) => {
        const photoPath = mockPhotos[index].path
        expect(img).toHaveAttribute('src', `/api/gallery/thumbnail/${photoPath}?size=${customSize}`)
      })
    })

    it('applies additional className', () => {
      const { container } = render(
        <ThumbnailGrid
          photos={mockPhotos}
          maxPhotos={9}
          onPhotoClick={mockOnPhotoClick}
          className="custom-class"
        />
      )

      const gridContainer = container.querySelector('.grid')
      expect(gridContainer).toHaveClass('custom-class')
    })

    it('has 3x3 grid layout classes', () => {
      const { container } = render(
        <ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />
      )

      const gridContainer = container.querySelector('.grid')
      expect(gridContainer).toHaveClass('grid')
      expect(gridContainer).toHaveClass('grid-cols-3')
      expect(gridContainer).toHaveClass('gap-1')
    })
  })

  describe('More Photos Indicator', () => {
    it('shows "+N more" text when photos > maxPhotos', () => {
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const remainingText = screen.getByText('+2 more photos')
      expect(remainingText).toBeInTheDocument()
    })

    it('does not show "+N more" when photos.length === maxPhotos', () => {
      const exactPhotos = mockPhotos.slice(0, 9)
      render(
        <ThumbnailGrid photos={exactPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />
      )

      const remainingText = screen.queryByText(/\+\d+ more photos/)
      expect(remainingText).not.toBeInTheDocument()
    })

    it('does not show "+N more" when photos.length < maxPhotos', () => {
      const fewPhotos = mockPhotos.slice(0, 5)
      render(<ThumbnailGrid photos={fewPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const remainingText = screen.queryByText(/\+\d+ more photos/)
      expect(remainingText).not.toBeInTheDocument()
    })

    it('calculates remaining count correctly', () => {
      // 11 total photos, 9 max = +2 more
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)
      expect(screen.getByText('+2 more photos')).toBeInTheDocument()

      // 11 total photos, 5 max = +6 more
      render(
        <ThumbnailGrid photos={mockPhotos} maxPhotos={5} onPhotoClick={mockOnPhotoClick} />
      )
      expect(screen.getByText('+6 more photos')).toBeInTheDocument()
    })
  })

  describe('Loading State', () => {
    it('shows skeleton loaders when isLoading is true', () => {
      render(
        <ThumbnailGrid photos={mockPhotos} maxPhotos={9} isLoading={true} onPhotoClick={mockOnPhotoClick} />
      )

      const skeletons = screen.getAllByRole('status')
      expect(skeletons).toHaveLength(9)
      skeletons.forEach((skeleton) => {
        expect(skeleton).toHaveAttribute('aria-busy', 'true')
        expect(skeleton).toHaveAttribute('aria-label', 'Loading thumbnail')
      })
    })

    it('shows correct number of skeletons based on maxPhotos', () => {
      render(
        <ThumbnailGrid photos={mockPhotos} maxPhotos={6} isLoading={true} onPhotoClick={mockOnPhotoClick} />
      )

      const skeletons = screen.getAllByRole('status')
      expect(skeletons).toHaveLength(6)
    })

    it('does not show actual images when loading', () => {
      render(
        <ThumbnailGrid photos={mockPhotos} maxPhotos={9} isLoading={true} onPhotoClick={mockOnPhotoClick} />
      )

      const images = screen.queryAllByRole('img')
      expect(images).toHaveLength(0)
    })

    it('shows images when isLoading is false', () => {
      render(
        <ThumbnailGrid photos={mockPhotos} maxPhotos={9} isLoading={false} onPhotoClick={mockOnPhotoClick} />
      )

      const images = screen.getAllByRole('img')
      expect(images).toHaveLength(9)
      const skeletons = screen.queryAllByRole('status')
      expect(skeletons).toHaveLength(0)
    })
  })

  describe('Empty State', () => {
    it('handles empty photos array gracefully', () => {
      render(<ThumbnailGrid photos={[]} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      expect(screen.getByText('No photos available')).toBeInTheDocument()
      const images = screen.queryAllByRole('img')
      expect(images).toHaveLength(0)
    })

    it('handles undefined photos gracefully', () => {
      render(<ThumbnailGrid photos={undefined} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      expect(screen.getByText('No photos available')).toBeInTheDocument()
      const images = screen.queryAllByRole('img')
      expect(images).toHaveLength(0)
    })

    it('handles null photos gracefully', () => {
      render(<ThumbnailGrid photos={null} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      expect(screen.getByText('No photos available')).toBeInTheDocument()
      const images = screen.queryAllByRole('img')
      expect(images).toHaveLength(0)
    })

    it('applies className to empty state container', () => {
      const { container } = render(
        <ThumbnailGrid photos={[]} maxPhotos={9} onPhotoClick={mockOnPhotoClick} className="custom-empty" />
      )

      const emptyContainer = container.querySelector('.custom-empty')
      expect(emptyContainer).toBeInTheDocument()
      expect(emptyContainer).toHaveTextContent('No photos available')
    })
  })

  describe('Click Handling', () => {
    it('calls onPhotoClick with correct photo when thumbnail is clicked', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[0])

      expect(mockOnPhotoClick).toHaveBeenCalledTimes(1)
      expect(mockOnPhotoClick).toHaveBeenCalledWith(mockPhotos[0])
    })

    it('calls onPhotoClick with correct photo for different thumbnails', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')

      // Click third thumbnail
      await user.click(buttons[2])
      expect(mockOnPhotoClick).toHaveBeenCalledWith(mockPhotos[2])

      // Click fifth thumbnail
      await user.click(buttons[4])
      expect(mockOnPhotoClick).toHaveBeenCalledWith(mockPhotos[4])
    })

    it('does not error when onPhotoClick is undefined', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} />)

      const buttons = screen.getAllByRole('button')
      await expect(user.click(buttons[0])).resolves.not.toThrow()
    })

    it('does not call onPhotoClick during loading state', () => {
      render(
        <ThumbnailGrid photos={mockPhotos} maxPhotos={9} isLoading={true} onPhotoClick={mockOnPhotoClick} />
      )

      const buttons = screen.queryAllByRole('button')
      expect(buttons).toHaveLength(0)
      expect(mockOnPhotoClick).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('each thumbnail button has proper focus styles', () => {
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach((button) => {
        expect(button).toHaveClass('focus:outline-none')
        expect(button).toHaveClass('focus:ring-2')
        expect(button).toHaveClass('focus:ring-blue-500')
      })
    })

    it('images have lazy loading attribute', () => {
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const images = screen.getAllByRole('img')
      images.forEach((img) => {
        expect(img).toHaveAttribute('loading', 'lazy')
      })
    })

    it('buttons have type="button" to prevent form submission', () => {
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      buttons.forEach((button) => {
        expect(button).toHaveAttribute('type', 'button')
      })
    })

    it('skeletons have proper ARIA attributes', () => {
      render(
        <ThumbnailGrid photos={mockPhotos} maxPhotos={9} isLoading={true} onPhotoClick={mockOnPhotoClick} />
      )

      const skeletons = screen.getAllByRole('status')
      skeletons.forEach((skeleton) => {
        expect(skeleton).toHaveAttribute('role', 'status')
        expect(skeleton).toHaveAttribute('aria-busy', 'true')
        expect(skeleton).toHaveAttribute('aria-label', 'Loading thumbnail')
      })
    })
  })

  describe('PropTypes Validation', () => {
    it('accepts valid photo objects', () => {
      expect(() => {
        render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)
      }).not.toThrow()
    })

    it('accepts photos with optional properties', () => {
      const minimalPhotos = [
        {
          path: 'photo1.jpg',
        },
        {
          path: 'photo2.jpg',
          lat: 37.7749,
        },
      ]

      expect(() => {
        render(<ThumbnailGrid photos={minimalPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)
      }).not.toThrow()
    })
  })

  describe('Keyboard Navigation', () => {
    it('moves focus to next thumbnail on ArrowRight', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[0]) // Focus first item

      await user.keyboard('{ArrowRight}')
      expect(buttons[1]).toHaveFocus()
    })

    it('moves focus to previous thumbnail on ArrowLeft', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[2]) // Focus third item

      await user.keyboard('{ArrowLeft}')
      expect(buttons[1]).toHaveFocus()
    })

    it('moves focus down one row on ArrowDown', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[0]) // Focus first item (index 0)

      await user.keyboard('{ArrowDown}')
      expect(buttons[3]).toHaveFocus() // Should move to index 3 (down one row)
    })

    it('moves focus up one row on ArrowUp', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[3]) // Focus fourth item (index 3)

      await user.keyboard('{ArrowUp}')
      expect(buttons[0]).toHaveFocus() // Should move to index 0 (up one row)
    })

    it('focuses first thumbnail on Home key', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[5]) // Focus middle item

      await user.keyboard('{Home}')
      expect(buttons[0]).toHaveFocus()
    })

    it('focuses last thumbnail on End key', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[0]) // Focus first item

      await user.keyboard('{End}')
      expect(buttons[8]).toHaveFocus() // Last displayed item (9 total)
    })

    it('activates focused thumbnail on Enter key', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[0]) // Focus first item

      await user.keyboard('{Enter}')
      expect(mockOnPhotoClick).toHaveBeenCalledWith(mockPhotos[0])
    })

    it('activates focused thumbnail on Space key', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[2]) // Focus third item

      await user.keyboard(' ')
      expect(mockOnPhotoClick).toHaveBeenCalledWith(mockPhotos[2])
    })

    it('does not move beyond last item with ArrowRight', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[8]) // Focus last item

      await user.keyboard('{ArrowRight}')
      expect(buttons[8]).toHaveFocus() // Should stay on last item
    })

    it('does not move before first item with ArrowLeft', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[0]) // Focus first item

      await user.keyboard('{ArrowLeft}')
      expect(buttons[0]).toHaveFocus() // Should stay on first item
    })

    it('only focused item has tabIndex=0', () => {
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      expect(buttons[0]).toHaveAttribute('tabIndex', '0')
      buttons.slice(1).forEach((button) => {
        expect(button).toHaveAttribute('tabIndex', '-1')
      })
    })

    it('handles ArrowDown at bottom edge gracefully', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[6]) // Focus item in last row

      await user.keyboard('{ArrowDown}')
      expect(buttons[8]).toHaveFocus() // Should move to last item (not beyond)
    })

    it('handles ArrowUp at top edge gracefully', async () => {
      const user = userEvent.setup()
      render(<ThumbnailGrid photos={mockPhotos} maxPhotos={9} onPhotoClick={mockOnPhotoClick} />)

      const buttons = screen.getAllByRole('button')
      await user.click(buttons[1]) // Focus item in first row

      await user.keyboard('{ArrowUp}')
      expect(buttons[0]).toHaveFocus() // Should move to first item (not negative)
    })
  })
})
