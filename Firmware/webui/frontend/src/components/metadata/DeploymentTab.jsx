import PropTypes from 'prop-types';
import MetadataField from './MetadataField';

/**
 * DeploymentTab Component
 *
 * Displays Mothbox deployment metadata including device information,
 * firmware version, session details, and hardware configuration.
 *
 * Features:
 * - Device name (copyable)
 * - Firmware version (copyable)
 * - Session ID (copyable)
 * - Installation type
 * - Raspberry Pi model
 * - Empty state handling
 * - Graceful handling of missing fields
 *
 * @component
 * @example
 * const data = {
 *   device_name: 'mothbox-backyard',
 *   firmware_version: '5.2.1',
 *   session_id: 'session-2025-03-15-143045',
 *   installation_type: 'production',
 *   pi_model: 'Raspberry Pi 5 Model B Rev 1.0'
 * };
 * return <DeploymentTab data={data} />
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

  const {
    device_name,
    firmware_version,
    session_id,
    installation_type,
    pi_model,
  } = data;

  return (
    <div className="space-y-2">
      {/* Device Name */}
      <MetadataField
        label="Device Name"
        value={device_name}
        copyable={!!device_name}
      />

      {/* Firmware Version */}
      <MetadataField
        label="Firmware Version"
        value={firmware_version}
        copyable={!!firmware_version}
      />

      {/* Session ID */}
      <MetadataField
        label="Session ID"
        value={session_id}
        copyable={!!session_id}
      />

      {/* Installation Type */}
      <MetadataField
        label="Installation Type"
        value={installation_type}
        copyable={false}
      />

      {/* Pi Model */}
      <MetadataField
        label="Pi Model"
        value={pi_model}
        copyable={false}
      />
    </div>
  );
}

DeploymentTab.propTypes = {
  /**
   * Deployment metadata object
   */
  data: PropTypes.shape({
    /** Mothbox device name */
    device_name: PropTypes.string,
    /** Firmware version string */
    firmware_version: PropTypes.string,
    /** Session identifier */
    session_id: PropTypes.string,
    /** Installation type (production, legacy, custom) */
    installation_type: PropTypes.string,
    /** Raspberry Pi model string */
    pi_model: PropTypes.string,
  }),
};

export default DeploymentTab;
