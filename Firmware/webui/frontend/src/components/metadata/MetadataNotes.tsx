import { useRef, useEffect, useCallback } from 'react'
import { useWatch } from 'react-hook-form'
import type { Control, UseFormRegister, UseFormSetValue } from 'react-hook-form'
import { ClockIcon } from '@heroicons/react/24/outline'
import { METADATA_VALIDATION } from '../../constants/config'
import type { MetadataFormData } from '../../schemas/metadata'

interface MetadataNotesProps {
  control: Control<MetadataFormData>
  register: UseFormRegister<MetadataFormData>
  setValue: UseFormSetValue<MetadataFormData>
  disabled?: boolean
}

export default function MetadataNotes({
  control,
  register,
  setValue,
  disabled = false,
}: MetadataNotesProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const maxLength = METADATA_VALIDATION.MAX_NOTES_LENGTH

  const notesValue = useWatch({ control, name: 'notes' }) ?? ''

  // Destructure register to get ref separately for merging
  const { ref: registerRef, ...registerRest } = register('notes')

  // Auto-expand textarea based on content
  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.max(80, textarea.scrollHeight)}px`
    }
  }, [])

  useEffect(() => {
    adjustHeight()
  }, [notesValue, adjustHeight])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    // Ctrl+Enter blurs textarea (triggers auto-save)
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault()
      textareaRef.current?.blur()
    }
  }, [])

  const insertTimestamp = useCallback(() => {
    const now = new Date()
    // Format: YYYY-MM-DD HH:mm - (local time)
    const pad = (n: number) => String(n).padStart(2, '0')
    const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())} - `
    const cursorPos = textareaRef.current?.selectionStart || notesValue.length
    const newValue = notesValue.slice(0, cursorPos) + timestamp + notesValue.slice(cursorPos)
    // Guard against exceeding maxLength (setValue bypasses the HTML attribute)
    if (newValue.length > maxLength) return
    setValue('notes', newValue, { shouldDirty: true })

    // Set cursor after timestamp
    setTimeout(() => {
      if (textareaRef.current) {
        const newPos = cursorPos + timestamp.length
        textareaRef.current.focus()
        textareaRef.current.setSelectionRange(newPos, newPos)
      }
    }, 0)
  }, [notesValue, setValue])

  const charCount = notesValue.length
  const isNearLimit = charCount >= maxLength * 0.9
  const isAtLimit = charCount >= maxLength

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <button
          type="button"
          onClick={insertTimestamp}
          disabled={disabled}
          className="inline-flex items-center gap-1 text-xs text-gray-600 hover:text-blue-600 disabled:opacity-50"
          title="Insert timestamp"
        >
          <ClockIcon className="w-4 h-4" />
          Add timestamp
        </button>
        <span className={`text-xs ${isNearLimit ? (isAtLimit ? 'text-red-500' : 'text-yellow-500') : 'text-gray-400'}`}>
          {charCount.toLocaleString()} / {maxLength.toLocaleString()} characters
        </span>
      </div>

      <textarea
        ref={(el) => {
          registerRef(el)
          textareaRef.current = el
        }}
        {...registerRest}
        onKeyDown={handleKeyDown}
        placeholder="Add notes about this photo..."
        disabled={disabled}
        maxLength={maxLength}
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 resize-none overflow-hidden whitespace-pre-wrap dark:bg-gray-800 dark:border-gray-600 min-h-[80px]"
      />

      <p className="text-xs text-gray-400">
        Ctrl+Enter to finish editing
      </p>
    </div>
  )
}
