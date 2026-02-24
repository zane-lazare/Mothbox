import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { useForm, type Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import MetadataCustomFields from '../MetadataCustomFields'
import {
  metadataFormSchema,
  type MetadataFormData,
} from '../../../schemas/metadata'

const DEFAULT_VALUES: MetadataFormData = {
  tags: [],
  species: '',
  commonName: '',
  confidence: 'unknown',
  referenceUrl: '',
  notes: '',
  custom: [],
}

function renderCustomFields(
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

    const { control, register } = useForm<MetadataFormData>({
      resolver,
      defaultValues: { ...DEFAULT_VALUES, ...overrides },
      mode: 'onBlur',
    })

    return <MetadataCustomFields control={control} register={register} disabled={opts.disabled} />
  }

  return render(<Wrapper />)
}

describe('MetadataCustomFields', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders existing key-value pairs with delete buttons', () => {
    renderCustomFields({
      custom: [
        { key: 'Location', value: 'Forest' },
        { key: 'Weather', value: 'Sunny' },
        { key: 'Temperature', value: '72F' },
      ],
    })

    expect(screen.getByDisplayValue('Location')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Forest')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Weather')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Sunny')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Temperature')).toBeInTheDocument()
    expect(screen.getByDisplayValue('72F')).toBeInTheDocument()

    const deleteButtons = screen.getAllByLabelText(/Delete field/i)
    expect(deleteButtons).toHaveLength(3)
  })

  it('add field creates new pair with auto-generated key', async () => {
    renderCustomFields({
      custom: [{ key: 'existing', value: 'value' }],
    })

    const addButton = screen.getByRole('button', {
      name: /Add custom field/i,
    })
    fireEvent.click(addButton)

    await waitFor(() => {
      // Should have two fields now: the existing one plus a new auto-generated one
      expect(screen.getByDisplayValue('existing')).toBeInTheDocument()
      expect(screen.getByDisplayValue('value')).toBeInTheDocument()
      expect(screen.getByDisplayValue('field_1')).toBeInTheDocument()
    })
  })

  it('editing a key updates the field', async () => {
    renderCustomFields({
      custom: [{ key: 'OldKey', value: 'value' }],
    })

    const keyInput = screen.getByDisplayValue('OldKey')
    fireEvent.change(keyInput, { target: { value: 'NewKey' } })

    await waitFor(() => {
      expect(screen.getByDisplayValue('NewKey')).toBeInTheDocument()
      expect(screen.queryByDisplayValue('OldKey')).not.toBeInTheDocument()
    })
  })

  it('editing a value updates the field', async () => {
    renderCustomFields({
      custom: [{ key: 'key', value: 'OldValue' }],
    })

    const valueInput = screen.getByDisplayValue('OldValue')
    fireEvent.change(valueInput, { target: { value: 'NewValue' } })

    await waitFor(() => {
      expect(screen.getByDisplayValue('NewValue')).toBeInTheDocument()
      expect(screen.queryByDisplayValue('OldValue')).not.toBeInTheDocument()
    })
  })

  it('delete removes a field', async () => {
    renderCustomFields({
      custom: [
        { key: 'Field1', value: 'Value1' },
        { key: 'Field2', value: 'Value2' },
      ],
    })

    const deleteButton = screen.getByLabelText('Delete field Field1')
    fireEvent.click(deleteButton)

    await waitFor(() => {
      expect(screen.queryByDisplayValue('Field1')).not.toBeInTheDocument()
      expect(screen.queryByDisplayValue('Value1')).not.toBeInTheDocument()
    })
    expect(screen.getByDisplayValue('Field2')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Value2')).toBeInTheDocument()
  })

  it('duplicate key validation shows error', () => {
    renderCustomFields({
      custom: [
        { key: 'existing', value: 'value1' },
        { key: 'another', value: 'value2' },
      ],
    })

    // Try to change 'another' to 'existing' (duplicate)
    const keyInput = screen.getByDisplayValue('another')
    fireEvent.change(keyInput, { target: { value: 'existing' } })

    // Should show error message (key input accepts the value but error is displayed)
    expect(
      screen.getByText('Key "existing" already exists'),
    ).toBeInTheDocument()
  })

  it('max 100 fields: add button disabled', () => {
    const custom = Array.from({ length: 100 }, (_, i) => ({
      key: `field${i}`,
      value: `value${i}`,
    }))

    renderCustomFields({ custom })

    const addButton = screen.getByRole('button', {
      name: /Add custom field/i,
    })
    expect(addButton).toBeDisabled()
    expect(screen.getByText(/max 100/i)).toBeInTheDocument()
  })

  it('empty state: shows "No custom fields" + add button', () => {
    renderCustomFields({ custom: [] })

    expect(screen.getByText('No custom fields')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Add custom field/i }),
    ).toBeInTheDocument()
  })

  it('disabled state: all inputs and buttons disabled', () => {
    renderCustomFields(
      { custom: [{ key: 'key', value: 'value' }] },
      { disabled: true },
    )

    const keyInput = screen.getByDisplayValue('key')
    const valueInput = screen.getByDisplayValue('value')
    expect(keyInput).toBeDisabled()
    expect(valueInput).toBeDisabled()

    const deleteButton = screen.getByLabelText('Delete field key')
    expect(deleteButton).toBeDisabled()

    const addButton = screen.getByRole('button', {
      name: /Add custom field/i,
    })
    expect(addButton).toBeDisabled()
  })

  it('placeholders: "Field name" and "Value"', async () => {
    renderCustomFields({ custom: [] })

    // Click add to create a field, then check placeholders
    const addButton = screen.getByRole('button', {
      name: /Add custom field/i,
    })
    fireEvent.click(addButton)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Field name')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Value')).toBeInTheDocument()
    })
  })
})
