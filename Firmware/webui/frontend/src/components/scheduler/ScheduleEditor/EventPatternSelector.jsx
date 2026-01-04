import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { PatternList } from '../PatternLibrary';
import { RoutineEditor } from '../RoutineEditor';
import { PatternSelectionPropType } from './propTypes';

/**
 * EventPatternSelector Component
 *
 * A component that allows users to select an event pattern for a schedule,
 * either from the pattern library or by creating a custom embedded pattern.
 *
 * @component
 * @example
 * <EventPatternSelector
 *   value={{
 *     source: 'library',
 *     pattern: { pattern_id: '...', name: '...', actions: [...] }
 *   }}
 *   onChange={(newValue) => console.log(newValue)}
 * />
 */
const EventPatternSelector = ({
  value = { source: 'library', pattern: null },
  onChange,
  disabled = false,
  errors = {},
}) => {
  /**
   * Get current source from value
   */
  const source = value?.source || 'library';
  const pattern = value?.pattern || null;

  /**
   * Internal state for managing tab when no value.source is provided
   */
  const [activeTab, setActiveTab] = useState(source);

  /**
   * Sync activeTab with value.source
   */
  useEffect(() => {
    if (value?.source) {
      setActiveTab(value.source);
    }
  }, [value?.source]);

  /**
   * Handle tab change
   */
  const handleTabChange = (newTab) => {
    if (disabled) return;
    setActiveTab(newTab);
    onChange({
      source: newTab,
      pattern: pattern,
    });
  };

  /**
   * Handle pattern selection from library
   */
  const handleLibrarySelect = (selectedPattern) => {
    onChange({
      source: 'library',
      pattern: selectedPattern,
    });
  };

  /**
   * Handle custom pattern save
   */
  const handleCustomSave = (savedPattern) => {
    onChange({
      source: 'custom',
      pattern: savedPattern,
    });
  };

  /**
   * Handle custom pattern cancel
   */
  const handleCustomCancel = () => {
    setActiveTab('library');
    onChange({
      source: 'library',
      pattern: pattern,
    });
  };

  /**
   * Handle clear selection
   */
  const handleClear = () => {
    onChange({
      source: source,
      pattern: null,
    });
  };

  /**
   * Format action count text
   */
  const getActionCountText = (actions) => {
    const count = actions?.length || 0;
    return count === 1 ? '1 action' : `${count} actions`;
  };

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        Event Pattern
      </h3>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-700" role="tablist">
        <div className="flex -mb-px">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'library'}
            disabled={disabled}
            onClick={() => handleTabChange('library')}
            data-testid="pattern-tab-library"
            className={`
              px-4 py-2 text-sm font-medium border-b-2 transition-colors
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
              dark:focus:ring-offset-gray-800
              disabled:opacity-50 disabled:cursor-not-allowed
              ${
                activeTab === 'library'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-300 dark:hover:text-gray-300'
              }
            `}
          >
            Library
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'custom'}
            disabled={disabled}
            onClick={() => handleTabChange('custom')}
            data-testid="pattern-tab-custom"
            className={`
              px-4 py-2 text-sm font-medium border-b-2 transition-colors
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
              dark:focus:ring-offset-gray-800
              disabled:opacity-50 disabled:cursor-not-allowed
              ${
                activeTab === 'custom'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-300 dark:hover:text-gray-300'
              }
            `}
          >
            Custom
          </button>
        </div>
      </div>

      {/* Selected Pattern Summary */}
      {activeTab === 'library' && (
        <div
          className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4"
          data-testid="selected-pattern-summary"
        >
          {pattern ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {pattern.name}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-300">
                  {getActionCountText(pattern.actions)}
                </p>
              </div>
              <button
                type="button"
                onClick={handleClear}
                disabled={disabled}
                className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300
                           disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Clear selection"
              >
                Clear
              </button>
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-300 italic">
              No pattern selected
            </p>
          )}
        </div>
      )}

      {/* Tab Content */}
      <div className="mt-4">
        {activeTab === 'library' ? (
          <PatternList
            mode="embedded"
            selectedPatternId={pattern?.pattern_id}
            onPatternSelect={handleLibrarySelect}
          />
        ) : (
          <RoutineEditor
            routine={pattern}
            onSave={handleCustomSave}
            onCancel={handleCustomCancel}
          />
        )}
      </div>

      {/* Error Message */}
      {errors.pattern && (
        <p className="mt-2 text-sm text-red-600 dark:text-red-400">
          {errors.pattern}
        </p>
      )}
    </div>
  );
};

EventPatternSelector.propTypes = {
  /** Pattern selection configuration with source ('library' or 'custom') and selected pattern */
  value: PatternSelectionPropType,
  /** Callback when pattern selection changes */
  onChange: PropTypes.func.isRequired,
  /** Whether the pattern selector is disabled */
  disabled: PropTypes.bool,
  /** Validation errors for pattern fields */
  errors: PropTypes.shape({
    pattern: PropTypes.string,
  }),
};

export default EventPatternSelector;
