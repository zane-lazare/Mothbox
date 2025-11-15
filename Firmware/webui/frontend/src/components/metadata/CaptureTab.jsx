import PropTypes from 'prop-types';
import MetadataField from './MetadataField';
import { formatTimestamp } from '../../utils/metadataFormatters';

/**
 * CaptureTab Component
 *
 * Displays photo capture metadata including timestamp, HDR status,
 * focus bracket information, and camera settings.
 *
 * Features:
 * - Formatted timestamp display
 * - Conditional HDR status (only shown when enabled)
 * - Conditional focus bracket info (only shown when enabled)
 * - Focus distance in meters
 * - Exposure and metering modes
 * - Copyable fields for timestamp and modes
 * - Empty state handling
 *
 * @component
 * @example
 * const data = {
 *   timestamp: '2025-03-15T14:30:45Z',
 *   hdr_enabled: true,
 *   focus_bracket_enabled: true,
 *   focus_bracket_position: 2,
 *   focus_bracket_total: 5,
 *   focus_distance: 1.5,
 *   exposure_mode: 'auto',
 *   metering_mode: 'center-weighted'
 * };
 * return <CaptureTab data={data} />
 */
function CaptureTab({ data }) {
  // Handle null or undefined data
  if (!data) {
    return (
      <div className="text-gray-500 text-sm">
        No capture data available
      </div>
    );
  }

  const {
    timestamp,
    hdr_enabled,
    focus_bracket_enabled,
    focus_bracket_position,
    focus_bracket_total,
    focus_distance,
    exposure_mode,
    metering_mode,
  } = data;

  // Format focus bracket display
  const getFocusBracketValue = () => {
    if (focus_bracket_position != null && focus_bracket_total != null) {
      return `${focus_bracket_position} of ${focus_bracket_total}`;
    }
    return null;
  };

  // Format focus distance
  const focusDistanceFormatted = focus_distance != null ? `${focus_distance}m` : null;

  return (
    <div className="space-y-2">
      {/* Timestamp */}
      <MetadataField
        label="Timestamp"
        value={formatTimestamp(timestamp)}
        copyable={!!timestamp}
      />

      {/* HDR Status - only shown when enabled */}
      {hdr_enabled && (
        <MetadataField
          label="HDR Status"
          value="Enabled"
          copyable={false}
        />
      )}

      {/* Focus Bracket - only shown when enabled */}
      {focus_bracket_enabled && (
        <MetadataField
          label="Focus Bracket"
          value={getFocusBracketValue()}
          copyable={false}
        />
      )}

      {/* Focus Distance */}
      <MetadataField
        label="Focus Distance"
        value={focusDistanceFormatted}
        copyable={false}
      />

      {/* Exposure Mode */}
      <MetadataField
        label="Exposure Mode"
        value={exposure_mode}
        copyable={!!exposure_mode}
      />

      {/* Metering Mode */}
      <MetadataField
        label="Metering Mode"
        value={metering_mode}
        copyable={!!metering_mode}
      />
    </div>
  );
}

CaptureTab.propTypes = {
  /**
   * Capture metadata object
   */
  data: PropTypes.shape({
    /** ISO 8601 timestamp string */
    timestamp: PropTypes.string,
    /** HDR enabled flag */
    hdr_enabled: PropTypes.bool,
    /** Focus bracket enabled flag */
    focus_bracket_enabled: PropTypes.bool,
    /** Current focus bracket position (1-indexed) */
    focus_bracket_position: PropTypes.number,
    /** Total number of focus bracket images */
    focus_bracket_total: PropTypes.number,
    /** Focus distance in meters */
    focus_distance: PropTypes.number,
    /** Exposure mode (auto, manual, etc.) */
    exposure_mode: PropTypes.string,
    /** Metering mode (center-weighted, spot, etc.) */
    metering_mode: PropTypes.string,
  }),
};

export default CaptureTab;
