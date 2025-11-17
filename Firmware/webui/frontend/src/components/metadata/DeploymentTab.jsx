import PropTypes from 'prop-types';
import MetadataField from './MetadataField';

/**
 * DeploymentTab Component
 *
 * Displays Mothbox deployment metadata including device information,
 * firmware version, and series details.
 *
 * Features:
 * - Mothbox ID (copyable)
 * - Firmware version (copyable)
 * - Series type (HDR/focus bracket/single)
 * - Series count and index
 * - Empty state handling
 * - Graceful handling of missing fields
 *
 * @component
 * @example
 * const metadata = {
 *   deployment: {
 *     mothbox_id: 'mothbox-backyard',
 *     firmware_version: '5',
 *     series_type: 'single',
 *     series_count: null,
 *     series_index: null
 *   }
 * };
 * return <DeploymentTab data={metadata} />
 */
function DeploymentTab({ data }) {
  // Handle null or undefined data
  if (!data) {
    return (
      <div className="text-gray-500 text-sm">
        No deployment data available
      </div>
    );
  }

  const deployment = data.deployment || {};
  const {
    mothbox_id,
    firmware_version,
    series_type,
    series_count,
    series_index,
  } = deployment;

  return (
    <div className="space-y-2">
      {/* Mothbox ID */}
      <MetadataField
        label="Mothbox ID"
        value={mothbox_id || 'N/A'}
        copyable={!!mothbox_id}
      />

      {/* Firmware Version */}
      <MetadataField
        label="Firmware Version"
        value={firmware_version || 'N/A'}
        copyable={!!firmware_version}
      />

      {/* Series Type */}
      <MetadataField
        label="Series Type"
        value={series_type || 'single'}
        copyable={false}
      />

      {/* Series Count */}
      {series_count !== null && series_count !== undefined && (
        <MetadataField
          label="Series Count"
          value={series_count.toString()}
          copyable={false}
        />
      )}

      {/* Series Index */}
      {series_index !== null && series_index !== undefined && (
        <MetadataField
          label="Series Index"
          value={series_index.toString()}
          copyable={false}
        />
      )}
    </div>
  );
}

DeploymentTab.propTypes = {
  /**
   * Full metadata object from backend API
   */
  data: PropTypes.shape({
    deployment: PropTypes.shape({
      /** Mothbox device identifier */
      mothbox_id: PropTypes.string,
      /** Firmware version string */
      firmware_version: PropTypes.string,
      /** Series type (single, hdr, focus_bracket) */
      series_type: PropTypes.string,
      /** Number of photos in series */
      series_count: PropTypes.number,
      /** Index of this photo in series */
      series_index: PropTypes.number,
    }),
  }),
};

export default DeploymentTab;
