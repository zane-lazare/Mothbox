import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MetadataNotes from '../MetadataNotes'

describe('MetadataNotes', () => {
  let mockOnChange

  beforeEach(() => {
    mockOnChange = vi.fn()
  })

  it('test_renders_textarea_with_current_value', () => {
    const testValue = 'These are my current notes'
    render(<MetadataNotes value={testValue} onChange={mockOnChange} />)

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)
    expect(textarea).toBeInTheDocument()
    expect(textarea.value).toBe(testValue)
  })

  it('test_textarea_auto_expands_on_content', async () => {
    const { rerender } = render(<MetadataNotes value="" onChange={mockOnChange} />)

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)

    // Mock scrollHeight to simulate actual browser behavior
    Object.defineProperty(textarea, 'scrollHeight', {
      configurable: true,
      value: 150
    })

    // Add multi-line content
    const longText = 'Line 1\nLine 2\nLine 3\nLine 4\nLine 5'
    rerender(<MetadataNotes value={longText} onChange={mockOnChange} />)

    await waitFor(() => {
      // Height should be set based on scrollHeight (minimum 80px)
      const heightValue = parseInt(textarea.style.height)
      expect(heightValue).toBeGreaterThanOrEqual(80)
      // With mocked scrollHeight of 150, should use that value
      expect(heightValue).toBe(150)
    })
  })

  it('test_shows_character_count', () => {
    const testValue = 'Hello World'
    render(<MetadataNotes value={testValue} onChange={mockOnChange} />)

    // Should show character count (default max is 10,000 from METADATA_VALIDATION.MAX_NOTES_LENGTH)
    expect(screen.getByText(/11.*10,000 characters/i)).toBeInTheDocument()
  })

  it('test_calls_onChange_on_input', async () => {
    const user = userEvent.setup()
    render(<MetadataNotes value="" onChange={mockOnChange} />)

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)
    await user.type(textarea, 'New text')

    expect(mockOnChange).toHaveBeenCalled()
    // Should be called once per character typed
    expect(mockOnChange.mock.calls.length).toBeGreaterThan(0)
  })

  it('test_timestamp_button_inserts_timestamp', async () => {
    const user = userEvent.setup()
    const initialValue = 'Existing notes'
    render(<MetadataNotes value={initialValue} onChange={mockOnChange} />)

    const timestampButton = screen.getByRole('button', { name: /insert timestamp|add timestamp/i })
    await user.click(timestampButton)

    expect(mockOnChange).toHaveBeenCalled()
    const newValue = mockOnChange.mock.calls[0][0]

    // Should contain timestamp format YYYY-MM-DD HH:mm -
    expect(newValue).toMatch(/\d{4}-\d{2}-\d{2} \d{2}:\d{2} - /)
    // Should append to existing content
    expect(newValue).toContain('Existing notes')
  })

  it('test_preserves_whitespace_and_newlines', () => {
    const testValue = 'Line 1\n  Indented line\n\nDouble newline'
    render(<MetadataNotes value={testValue} onChange={mockOnChange} />)

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)
    expect(textarea.value).toBe(testValue)

    // Check that textarea has whitespace-pre-wrap styling
    const styles = window.getComputedStyle(textarea)
    expect(styles.whiteSpace).toMatch(/pre-wrap/)
  })

  it('test_placeholder_when_empty', () => {
    render(<MetadataNotes value="" onChange={mockOnChange} />)

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)
    expect(textarea).toBeInTheDocument()
    expect(textarea.value).toBe('')
  })

  it('test_disabled_state', async () => {
    const user = userEvent.setup()
    render(<MetadataNotes value="" onChange={mockOnChange} disabled={true} />)

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)
    const timestampButton = screen.getByRole('button', { name: /insert timestamp|add timestamp/i })

    expect(textarea).toBeDisabled()
    expect(timestampButton).toBeDisabled()

    // Try to type - should not work
    await user.type(textarea, 'Test')
    expect(mockOnChange).not.toHaveBeenCalled()
  })

  it('test_max_length_indicator', () => {
    const maxLength = 100
    const nearLimitValue = 'x'.repeat(91) // 91% of 100
    const atLimitValue = 'x'.repeat(100)

    // Test near limit (90%+)
    const { rerender } = render(
      <MetadataNotes value={nearLimitValue} onChange={mockOnChange} maxLength={maxLength} />
    )

    let charCountElement = screen.getByText(/91.*100 characters/i)
    expect(charCountElement).toHaveClass('text-yellow-500')

    // Test at limit
    rerender(<MetadataNotes value={atLimitValue} onChange={mockOnChange} maxLength={maxLength} />)

    charCountElement = screen.getByText(/100.*100 characters/i)
    expect(charCountElement).toHaveClass('text-red-500')
  })

  it('test_keyboard_ctrl_enter_blur', async () => {
    render(<MetadataNotes value="Test" onChange={mockOnChange} />)

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)

    // Focus the textarea
    textarea.focus()
    expect(document.activeElement).toBe(textarea)

    // Press Ctrl+Enter
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true })

    await waitFor(() => {
      expect(document.activeElement).not.toBe(textarea)
    })
  })

  it('test_prevents_exceeding_max_length', async () => {
    const user = userEvent.setup()
    const maxLength = 10
    const initialValue = 'x'.repeat(10)

    render(<MetadataNotes value={initialValue} onChange={mockOnChange} maxLength={maxLength} />)

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)

    // Try to add more text
    await user.type(textarea, 'y')

    // onChange should not be called with value exceeding max length
    if (mockOnChange.mock.calls.length > 0) {
      const newValue = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0]
      expect(newValue.length).toBeLessThanOrEqual(maxLength)
    }
  })

  it('test_timestamp_inserts_at_cursor_position', async () => {
    const user = userEvent.setup()
    const initialValue = 'Start Middle End'
    render(<MetadataNotes value={initialValue} onChange={mockOnChange} />)

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)

    // Set cursor position to middle (after "Start ")
    textarea.focus()
    textarea.setSelectionRange(6, 6)

    const timestampButton = screen.getByRole('button', { name: /insert timestamp|add timestamp/i })
    await user.click(timestampButton)

    expect(mockOnChange).toHaveBeenCalled()
    const newValue = mockOnChange.mock.calls[0][0]

    // Timestamp should be inserted at cursor position (after "Start ")
    expect(newValue).toMatch(/^Start \d{4}-\d{2}-\d{2} \d{2}:\d{2} - Middle End$/)
  })

  it('test_displays_helpful_keyboard_hint', () => {
    render(<MetadataNotes value="" onChange={mockOnChange} />)

    expect(screen.getByText(/ctrl\+enter to finish editing/i)).toBeInTheDocument()
  })
})
