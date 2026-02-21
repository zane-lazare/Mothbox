import {
  useController,
  type UseControllerProps,
  type FieldValues,
  type FieldPath,
} from 'react-hook-form';

/**
 * Shared controlled-field hook wrapping useController.
 * Provides field props, error state, and validation status in one call.
 *
 * @example
 * ```tsx
 * function MyInput({ control, name }) {
 *   const { field, error, isInvalid } = useFormField({ control, name });
 *   return (
 *     <FormField name={name} error={error}>
 *       <input {...field} aria-invalid={isInvalid} />
 *     </FormField>
 *   );
 * }
 * ```
 */
export function useFormField<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
>(props: UseControllerProps<TFieldValues, TName>) {
  const { field, fieldState } = useController(props);

  return {
    /** Spread onto input: { value, onChange, onBlur, name, ref } */
    field,
    /** Field error object (undefined if valid) */
    error: fieldState.error,
    /** Whether field has a validation error */
    isInvalid: !!fieldState.error,
    /** Whether field value has been modified */
    isDirty: fieldState.isDirty,
    /** Whether field has been touched (blurred) */
    isTouched: fieldState.isTouched,
  };
}
