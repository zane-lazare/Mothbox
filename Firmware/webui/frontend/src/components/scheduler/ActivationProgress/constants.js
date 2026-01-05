/**
 * Constants for ActivationProgress component (Issue #327)
 *
 * Maps backend activation phases to user-friendly labels and progress values.
 * Backend phase constants are defined in scheduler_service.py:84-97.
 *
 * @module components/scheduler/ActivationProgress/constants
 */

/**
 * Human-readable labels for each activation phase.
 * Keys match backend phase constants from scheduler_service.py.
 */
export const PHASE_LABELS = {
  checking_conflicts: 'Checking for conflicts...',
  generating_cron: 'Generating schedule...',
  applying_cron: 'Writing crontab...',
  updating_state: 'Updating state...',
  complete: 'Complete',
  failed: 'Failed',
}

/**
 * Progress percentages for each activation phase.
 * Values match backend ACTIVATION_PROGRESS_* constants from scheduler_service.py:92-97.
 */
export const PHASE_PROGRESS = {
  checking_conflicts: 10,
  generating_cron: 30,
  applying_cron: 60,
  updating_state: 90,
  complete: 100,
  failed: 0,
}
