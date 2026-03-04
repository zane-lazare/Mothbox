import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'

/**
 * Warning banner shown when schedule approaches cron entry limit.
 *
 * The system has a 10,000 cron entry limit. This component warns users
 * when their schedule configuration is approaching or exceeding this limit.
 *
 * Issue #385 review: Document 10k cron limit in user-facing UI
 */

interface CronLimitWarningProps {
  estimatedEntries?: number;
}

/** Maximum cron entries supported by the system */
const MAX_CRON_ENTRIES = 10000

/** Threshold percentage for showing warning (75%) */
const WARNING_THRESHOLD = 0.75

/**
 * CronLimitWarning component
 *
 * @param {Object} props
 * @param {number} props.estimatedEntries - Estimated number of cron entries
 * @returns {JSX.Element|null}
 */
function CronLimitWarning({ estimatedEntries }: CronLimitWarningProps) {
  if (!estimatedEntries || estimatedEntries < MAX_CRON_ENTRIES * WARNING_THRESHOLD) {
    return null
  }

  const isOverLimit = estimatedEntries > MAX_CRON_ENTRIES
  const percentage = Math.round((estimatedEntries / MAX_CRON_ENTRIES) * 100)

  return (
    <div
      role="alert"
      className={`flex items-start gap-2 p-3 rounded-lg text-sm ${
        isOverLimit
          ? 'bg-red-50 border border-red-200 text-red-800'
          : 'bg-amber-50 border border-amber-200 text-amber-800'
      }`}
    >
      <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0 mt-0.5" />
      <div>
        <p className="font-medium">
          {isOverLimit ? 'Schedule exceeds system limit' : 'Approaching system limit'}
        </p>
        <p className="mt-1">
          {isOverLimit ? (
            <>
              This schedule would generate ~{estimatedEntries.toLocaleString()} cron entries,
              exceeding the {MAX_CRON_ENTRIES.toLocaleString()} entry limit.
              Reduce frequency or duration.
            </>
          ) : (
            <>
              This schedule generates ~{estimatedEntries.toLocaleString()} cron entries
              ({percentage}% of {MAX_CRON_ENTRIES.toLocaleString()} limit).
              Consider reducing frequency for complex schedules.
            </>
          )}
        </p>
      </div>
    </div>
  )
}

export default CronLimitWarning
