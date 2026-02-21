import { render, type RenderOptions } from '@testing-library/react';
import {
  FormProvider,
  useForm,
  type UseFormProps,
  type FieldValues,
  type UseFormReturn,
  type Resolver,
} from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import type { ReactElement } from 'react';
import type { ZodType } from 'zod';

interface RenderWithFormOptions<T extends FieldValues>
  extends Omit<RenderOptions, 'wrapper'> {
  /** Default form values */
  defaultValues?: T;
  /** Zod schema for validation */
  schema?: ZodType;
  /** Additional useForm options */
  formOptions?: Omit<UseFormProps<T>, 'defaultValues' | 'resolver'>;
}

/**
 * Render a component wrapped in a FormProvider for testing.
 * Returns all @testing-library/react utilities plus form methods.
 *
 * @example
 * ```tsx
 * const { getByRole } = renderWithForm(
 *   <FormField name="email" label="Email">
 *     <input />
 *   </FormField>,
 *   { defaultValues: { email: '' } }
 * );
 * ```
 */
export function renderWithForm<T extends FieldValues = FieldValues>(
  ui: ReactElement,
  options: RenderWithFormOptions<T> = {},
) {
  const { defaultValues, schema, formOptions, ...renderOptions } = options;

  // Function-scoped capture — no shared module state between calls.
  let capturedMethods: UseFormReturn<T> | null = null;

  // zodResolver's Zod 4 overload expects $ZodType<Output, FieldValues> but
  // Zod 4's public ZodType uses `unknown` for its input parameter. The cast
  // through `unknown` is safe because the schema validates the same shape at
  // runtime. TODO: Remove when @hookform/resolvers aligns with Zod 4 generics.
  const resolver = schema
    ? (zodResolver(schema as unknown as Parameters<typeof zodResolver>[0]) as Resolver<T>)
    : undefined;

  // Wrapper component that creates the form context
  function FormWrapper({ children }: { children: React.ReactNode }) {
    const methods = useForm<T>({
      defaultValues: defaultValues as UseFormProps<T>['defaultValues'],
      resolver,
      ...formOptions,
    });

    capturedMethods = methods;

    return <FormProvider {...methods}>{children}</FormProvider>;
  }

  const result = render(ui, {
    wrapper: FormWrapper,
    ...renderOptions,
  });

  return {
    ...result,
    /** Access to the underlying react-hook-form methods */
    formMethods: capturedMethods as unknown as UseFormReturn<T>,
  };
}
