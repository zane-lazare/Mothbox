import PropTypes from 'prop-types';
import MetadataField from './MetadataField';
import { formatTimestamp } from '../../utils/metadataFormatters';

/**
 * CaptureTab Component
 *
 * Displays photo capture metadata including timestamp.
 *
 * Features:
 * - Formatted timestamp display
 * - Copyable timestamp field
 * - Empty state handling
 *
 * @component
 * @example
 * const metadata = {
 *   capture: {
 *     timestamp: '2024-10-15 14:30:00'
 *   }
 * };
 * return <CaptureTab data={metadata} />
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

  const capture = data.capture || {};
  const { timestamp } = capture;

  return (
    <div className="space-y-2">
      {/* Timestamp */}
      <MetadataField
        label="Timestamp"
        value={formatTimestamp(timestamp)}
        copyable={!!timestamp}
      />
    </div>
  );
}

CaptureTab.propTypes = {
  /**
   * Full metadata object from backend API
   */
  data: PropTypes.shape({
    capture: PropTypes.shape({
      /** Timestamp string */
      timestamp: PropTypes.string,
      /** Exposure time (e.g., "1/500") */
      exposure_time: PropTypes.string,
      /** F-number (aperture) */
      f_number: PropTypes.number,
      /** ISO sensitivity */
      iso: PropTypes.number,
      /** Focal length (e.g., "24mm") */
      focal_length: PropTypes.string,
      /** White balance setting */
      white_balance: PropTypes.string,
      /** Flash status */
      flash: PropTypes.string,
    }),
  }),
};

export default CaptureTab;
