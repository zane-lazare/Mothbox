import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MoonPhaseIcon from '../MoonPhaseIcon'

describe('MoonPhaseIcon', () => {
  describe('Rendering', () => {
    it('should render moon icon', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      // Check for SVG element (MoonIcon from Heroicons)
      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
    })

    it('should render with default small size', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('h-4', 'w-4')
    })

    it('should render with medium size', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} size="md" />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('h-5', 'w-5')
    })

    it('should render with large size', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} size="lg" />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('h-6', 'w-6')
    })

    it('should fallback to small size for invalid size prop', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} size="invalid" />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('h-4', 'w-4')
    })
  })

  describe('Phase Styling', () => {
    it('should render new moon with gray color', () => {
      const phase = {
        phase: 'new',
        phase_name: 'New Moon',
        illumination: 0.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-gray-400')
    })

    it('should render full moon with yellow color and fill', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-yellow-300')
      expect(icon).toHaveClass('fill-yellow-300')
    })

    it('should render waxing crescent with light yellow', () => {
      const phase = {
        phase: 'waxing_crescent',
        phase_name: 'Waxing Crescent',
        illumination: 0.25,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-yellow-200')
    })

    it('should render first quarter with partial fill', () => {
      const phase = {
        phase: 'first_quarter',
        phase_name: 'First Quarter',
        illumination: 0.5,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-yellow-300')
      expect(icon).toHaveClass('fill-yellow-100')
    })

    it('should render waxing gibbous with bright yellow', () => {
      const phase = {
        phase: 'waxing_gibbous',
        phase_name: 'Waxing Gibbous',
        illumination: 0.75,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-yellow-300')
      expect(icon).toHaveClass('fill-yellow-200')
    })

    it('should render waning gibbous with bright yellow', () => {
      const phase = {
        phase: 'waning_gibbous',
        phase_name: 'Waning Gibbous',
        illumination: 0.75,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-yellow-300')
      expect(icon).toHaveClass('fill-yellow-200')
    })

    it('should render last quarter with partial fill', () => {
      const phase = {
        phase: 'last_quarter',
        phase_name: 'Last Quarter',
        illumination: 0.5,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-yellow-300')
      expect(icon).toHaveClass('fill-yellow-100')
    })

    it('should render waning crescent with light yellow', () => {
      const phase = {
        phase: 'waning_crescent',
        phase_name: 'Waning Crescent',
        illumination: 0.25,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-yellow-200')
    })

    it('should render unknown phase with gray color', () => {
      const phase = {
        phase: 'unknown_phase',
        phase_name: 'Unknown',
        illumination: 0.5,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-gray-400')
    })
  })

  describe('Dark Mode', () => {
    it('should apply dark mode classes', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      // Check that dark mode classes are present in the className
      expect(icon.className).toContain('dark:')
    })

    it('should have dark mode gray color for new moon', () => {
      const phase = {
        phase: 'new',
        phase_name: 'New Moon',
        illumination: 0.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('dark:text-gray-500')
    })

    it('should have dark mode yellow fill for full moon', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('dark:fill-yellow-400')
    })
  })

  describe('Tooltip', () => {
    it('should render tooltip with phase name and illumination', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      render(<MoonPhaseIcon phase={phase} />)

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toBeInTheDocument()
      expect(tooltip).toHaveTextContent('Full Moon (100% illuminated)')
    })

    it('should show tooltip on hover', async () => {
      const user = userEvent.setup()
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const tooltip = screen.getByRole('tooltip')
      const iconContainer = container.querySelector('.group')

      // Initially invisible
      expect(tooltip).toHaveClass('invisible')
      expect(tooltip).toHaveClass('opacity-0')

      // Hover over icon
      await user.hover(iconContainer)

      // Should become visible with transition classes
      expect(tooltip).toHaveClass('group-hover:visible')
      expect(tooltip).toHaveClass('group-hover:opacity-100')
    })

    it('should format illumination percentage correctly', () => {
      const phase = {
        phase: 'waxing_gibbous',
        phase_name: 'Waxing Gibbous',
        illumination: 0.752,
      }

      render(<MoonPhaseIcon phase={phase} />)

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveTextContent('Waxing Gibbous (75% illuminated)')
    })

    it('should handle zero illumination', () => {
      const phase = {
        phase: 'new',
        phase_name: 'New Moon',
        illumination: 0.0,
      }

      render(<MoonPhaseIcon phase={phase} />)

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveTextContent('New Moon (0% illuminated)')
    })

    it('should show illumination only if phase_name is missing', () => {
      const phase = {
        phase: 'full',
        illumination: 0.987,
      }

      render(<MoonPhaseIcon phase={phase} />)

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveTextContent('99% illuminated')
      expect(tooltip).not.toHaveTextContent('Full Moon')
    })

    it('should position tooltip above icon', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      render(<MoonPhaseIcon phase={phase} />)

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveClass('bottom-full', 'mb-2')
    })

    it('should center tooltip horizontally', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      render(<MoonPhaseIcon phase={phase} />)

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveClass('left-1/2', '-translate-x-1/2')
    })

    it('should render tooltip arrow', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      render(<MoonPhaseIcon phase={phase} />)

      const tooltip = screen.getByRole('tooltip')
      const arrow = tooltip.querySelector('div')
      expect(arrow).toHaveClass('border-t-gray-900')
    })
  })

  describe('Missing/Invalid Props', () => {
    it('should handle missing phase prop gracefully', () => {
      const { container } = render(<MoonPhaseIcon />)

      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
      expect(icon).toHaveClass('text-gray-400')
    })

    it('should handle null phase prop', () => {
      const { container } = render(<MoonPhaseIcon phase={null} />)

      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
      expect(icon).toHaveClass('text-gray-400')
    })

    it('should handle phase object without phase property', () => {
      const phase = {
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
      expect(icon).toHaveClass('text-gray-400')
    })

    it('should handle missing illumination property', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
      }

      render(<MoonPhaseIcon phase={phase} />)

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveTextContent('Full Moon (0% illuminated)')
    })

    it('should handle phase without phase_name', () => {
      const phase = {
        phase: 'full',
        illumination: 1.0,
      }

      render(<MoonPhaseIcon phase={phase} />)

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveTextContent('100% illuminated')
    })
  })

  describe('Accessibility', () => {
    it('should have aria-hidden on icon', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      const { container } = render(<MoonPhaseIcon phase={phase} />)

      const icon = container.querySelector('svg')
      expect(icon).toHaveAttribute('aria-hidden', 'true')
    })

    it('should have role="tooltip" on tooltip element', () => {
      const phase = {
        phase: 'full',
        phase_name: 'Full Moon',
        illumination: 1.0,
      }

      render(<MoonPhaseIcon phase={phase} />)

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveAttribute('role', 'tooltip')
    })
  })

  describe('All Moon Phases', () => {
    const allPhases = [
      { phase: 'new', phase_name: 'New Moon', illumination: 0.0 },
      { phase: 'waxing_crescent', phase_name: 'Waxing Crescent', illumination: 0.25 },
      { phase: 'first_quarter', phase_name: 'First Quarter', illumination: 0.5 },
      { phase: 'waxing_gibbous', phase_name: 'Waxing Gibbous', illumination: 0.75 },
      { phase: 'full', phase_name: 'Full Moon', illumination: 1.0 },
      { phase: 'waning_gibbous', phase_name: 'Waning Gibbous', illumination: 0.75 },
      { phase: 'last_quarter', phase_name: 'Last Quarter', illumination: 0.5 },
      { phase: 'waning_crescent', phase_name: 'Waning Crescent', illumination: 0.25 },
    ]

    it.each(allPhases)('should render $phase_name correctly', (phaseData) => {
      const { container } = render(<MoonPhaseIcon phase={phaseData} />)

      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveTextContent(phaseData.phase_name)
    })
  })
})
