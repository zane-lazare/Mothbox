import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { renderWithForm } from '../../test-utils/renderWithForm';
import { useFormField } from '../useFormField';
import { useFormContext } from 'react-hook-form';

// A component that uses the useFormField hook
function FieldConsumer({ name }: { name: string }) {
  const { control } = useFormContext();
  const { field, error, isInvalid, isDirty, isTouched } = useFormField({
    control,
    name,
  });

  return (
    <div>
      <input data-testid="field-input" {...field} />
      <span data-testid="is-invalid">{String(isInvalid)}</span>
      <span data-testid="is-dirty">{String(isDirty)}</span>
      <span data-testid="is-touched">{String(isTouched)}</span>
      {error && <span data-testid="error-message">{error.message}</span>}
    </div>
  );
}

describe('useFormField', () => {
  it('returns field props bound to the form', () => {
    const { getByTestId } = renderWithForm(<FieldConsumer name="username" />, {
      defaultValues: { username: 'test-user' },
    });

    const input = getByTestId('field-input') as HTMLInputElement;
    expect(input.value).toBe('test-user');
  });

  it('starts with isInvalid=false, isDirty=false, isTouched=false', () => {
    const { getByTestId } = renderWithForm(<FieldConsumer name="username" />, {
      defaultValues: { username: '' },
    });

    expect(getByTestId('is-invalid').textContent).toBe('false');
    expect(getByTestId('is-dirty').textContent).toBe('false');
    expect(getByTestId('is-touched').textContent).toBe('false');
  });

  it('works with a Zod schema for validation', () => {
    const schema = z.object({
      username: z.string().min(3, 'Too short'),
    });

    const { getByTestId } = renderWithForm(<FieldConsumer name="username" />, {
      defaultValues: { username: 'ok' },
      schema,
    });

    // Initially no error is shown until form is validated
    expect(getByTestId('is-invalid').textContent).toBe('false');
  });
});
