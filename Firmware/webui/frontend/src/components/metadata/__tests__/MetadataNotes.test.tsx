import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useForm, type Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import MetadataNotes from '../MetadataNotes'
import { metadataFormSchema, type MetadataFormData } from '../../../schemas/metadata'
import { METADATA_VALIDATION } from '../../../constants/config'

const DEFAULT_VALUES: MetadataFormData = {
  tags: [],
  species: '',
  commonName: '',
  confidence: 'unknown',
  referenceUrl: '',
  notes: '',
  custom: [],
}

function renderNotes(
  overrides: Partial<MetadataFormData> = {},
  opts: { disabled?: boolean } = {},
) {
  function Wrapper() {
    // zodResolver's Zod 4 overload expects $ZodType<Output, FieldValues> but
    // Zod 4's public ZodType uses `unknown` for its input parameter. The cast
    // through `unknown` is safe because the schema validates the same shape at
    // runtime. TODO: Remove when @hookform/resolvers aligns with Zod 4 generics.
    const resolver = zodResolver(
      metadataFormSchema as unknown as Parameters<typeof zodResolver>[0],
    ) as unknown as Resolver<MetadataFormData>

    const { control, register, setValue } = useForm<MetadataFormData>({
      resolver,
      defaultValues: { ...DEFAULT_VALUES, ...overrides },
      mode: 'onBlur',
    })

    return (
      <MetadataNotes
        control={control}
        register={register}
        setValue={setValue}
        disabled={opts.disabled}
      />
    )
  }

  return render(<Wrapper />)
}

describe('MetadataNotes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('test_renders_textarea_with_current_value', () => {
    const testValue = 'These are my current notes'
    renderNotes({ notes: testValue })

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)
    expect(textarea).toBeInTheDocument()
    expect(textarea).toHaveValue(testValue)
  })

  it('test_textarea_auto_expands_on_content', async () => {
    const user = userEvent.setup()
    renderNotes({ notes: '' })

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)

    // Mock scrollHeight to simulate actual browser behavior
    Object.defineProperty(textarea, 'scrollHeight', {
      configurable: true,
      value: 150,
    })

    // Type multi-line content to trigger re-render and height adjustment
    await user.type(textarea, 'Line 1\nLine 2\nLine 3')

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
    renderNotes({ notes: testValue })

    // Should show character count with max from METADATA_VALIDATION
    expect(
      screen.getByText(
        new RegExp(`11.*${METADATA_VALIDATION.MAX_NOTES_LENGTH.toLocaleString()} characters`, 'i'),
      ),
    ).toBeInTheDocument()
  })

  it('test_calls_onChange_on_input', async () => {
    const user = userEvent.setup()
    renderNotes({ notes: '' })

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)
    await user.type(textarea, 'New text')

    // With react-hook-form, verify the DOM value has been updated
    expect(textarea).toHaveValue('New text')
  })

  it('test_timestamp_button_inserts_timestamp', async () => {
    const user = userEvent.setup()
    renderNotes({ notes: 'Existing notes' })

    const timestampButton = screen.getByRole('button', { name: /insert timestamp|add timestamp/i })
    await user.click(timestampButton)

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)

    await waitFor(() => {
      const value = (textarea as HTMLTextAreaElement).value
      // Should contain timestamp format YYYY-MM-DD HH:mm -
      expect(value).toMatch(/\d{4}-\d{2}-\d{2} \d{2}:\d{2} - /)
      // Should contain the existing content
      expect(value).toContain('Existing notes')
    })
  })

  it('test_preserves_whitespace_and_newlines', () => {
    const testValue = 'Line 1\n  Indented line\n\nDouble newline'
    renderNotes({ notes: testValue })

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)
    expect(textarea).toHaveValue(testValue)

    // Check that textarea has whitespace-pre-wrap styling
    const styles = window.getComputedStyle(textarea)
    expect(styles.whiteSpace).toMatch(/pre-wrap/)
  })

  it('test_placeholder_when_empty', () => {
    renderNotes({ notes: '' })

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)
    expect(textarea).toBeInTheDocument()
    expect(textarea).toHaveValue('')
  })

  it('test_disabled_state', async () => {
    const user = userEvent.setup()
    renderNotes({ notes: '' }, { disabled: true })

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)
    const timestampButton = screen.getByRole('button', { name: /insert timestamp|add timestamp/i })

    expect(textarea).toBeDisabled()
    expect(timestampButton).toBeDisabled()

    // Try to type - should not work
    await user.type(textarea, 'Test')
    expect(textarea).toHaveValue('')
  })

  it('test_max_length_indicator', async () => {
    const user = userEvent.setup()
    // Use a small maxLength by typing close to the HTML maxlength.
    // Since maxLength is fixed at METADATA_VALIDATION.MAX_NOTES_LENGTH (10000),
    // we test the color logic by providing values at specific thresholds.

    // Near limit: 90%+ of 10000 = 9000+
    const nearLimitValue = 'x'.repeat(9001)
    renderNotes({ notes: nearLimitValue })

    let charCountElement = screen.getByText(
      new RegExp(`9,001.*${METADATA_VALIDATION.MAX_NOTES_LENGTH.toLocaleString()} characters`, 'i'),
    )
    expect(charCountElement).toHaveClass('text-yellow-500')
  })

  it('test_max_length_indicator_at_limit', () => {
    const atLimitValue = 'x'.repeat(METADATA_VALIDATION.MAX_NOTES_LENGTH)
    renderNotes({ notes: atLimitValue })

    const charCountElement = screen.getByText(
      new RegExp(
        `${METADATA_VALIDATION.MAX_NOTES_LENGTH.toLocaleString()}.*${METADATA_VALIDATION.MAX_NOTES_LENGTH.toLocaleString()} characters`,
        'i',
      ),
    )
    expect(charCountElement).toHaveClass('text-red-500')
  })

  it('test_keyboard_ctrl_enter_blur', async () => {
    renderNotes({ notes: 'Test' })

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
    // With react-hook-form + HTML maxLength attribute, the browser enforces the limit.
    // We verify maxLength attribute is set on the textarea.
    renderNotes({ notes: '' })

    const textarea = screen.getByPlaceholderText(/add notes about this photo/i)
    expect(textarea).toHaveAttribute(
      'maxLength',
      String(METADATA_VALIDATION.MAX_NOTES_LENGTH),
    )
  })

  it('test_timestamp_inserts_at_cursor_position', async () => {
    const user = userEvent.setup()
    const initialValue = 'Start Middle End'
    renderNotes({ notes: initialValue })

    const textarea = screen.getByPlaceholderText(
      /add notes about this photo/i,
    ) as HTMLTextAreaElement

    // Set cursor position to middle (after "Start ")
    textarea.focus()
    textarea.setSelectionRange(6, 6)

    const timestampButton = screen.getByRole('button', { name: /insert timestamp|add timestamp/i })
    await user.click(timestampButton)

    await waitFor(() => {
      const value = textarea.value
      // Timestamp should be inserted at cursor position (after "Start ")
      expect(value).toMatch(/^Start \d{4}-\d{2}-\d{2} \d{2}:\d{2} - Middle End$/)
    })
  })

  it('test_displays_helpful_keyboard_hint', () => {
    renderNotes({ notes: '' })

    expect(screen.getByText(/ctrl\+enter to finish editing/i)).toBeInTheDocument()
  })
})
