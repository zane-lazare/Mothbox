import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import DeploymentTab from '../DeploymentTab';

describe('DeploymentTab', () => {
  describe('Basic Field Rendering', () => {
    it('renders device name', () => {
      const data = {
        device_name: 'mothbox-001',
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Device Name')).toBeInTheDocument();
      expect(screen.getByText('mothbox-001')).toBeInTheDocument();
    });

    it('renders firmware version', () => {
      const data = {
        firmware_version: '5.2.1',
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Firmware Version')).toBeInTheDocument();
      expect(screen.getByText('5.2.1')).toBeInTheDocument();
    });

    it('renders session ID', () => {
      const data = {
        session_id: 'session-2025-03-15-143045',
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Session ID')).toBeInTheDocument();
      expect(screen.getByText('session-2025-03-15-143045')).toBeInTheDocument();
    });

    it('renders installation type', () => {
      const data = {
        installation_type: 'production',
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Installation Type')).toBeInTheDocument();
      expect(screen.getByText('production')).toBeInTheDocument();
    });

    it('renders Pi model', () => {
      const data = {
        pi_model: 'Raspberry Pi 5 Model B Rev 1.0',
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Pi Model')).toBeInTheDocument();
      expect(screen.getByText('Raspberry Pi 5 Model B Rev 1.0')).toBeInTheDocument();
    });
  });

  describe('Null Data Handling', () => {
    it('handles null data', () => {
      render(<DeploymentTab data={null} />);

      expect(screen.getByText('No deployment data available')).toBeInTheDocument();
    });

    it('handles undefined data', () => {
      render(<DeploymentTab />);

      expect(screen.getByText('No deployment data available')).toBeInTheDocument();
    });
  });

  describe('Partial Data Handling', () => {
    it('handles missing device name', () => {
      const data = {
        firmware_version: '5.2.1',
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Device Name')).toBeInTheDocument();
      // Multiple N/A values expected for missing fields
      expect(screen.getAllByText('N/A').length).toBeGreaterThan(0);
    });

    it('handles missing firmware version', () => {
      const data = {
        device_name: 'mothbox-001',
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Firmware Version')).toBeInTheDocument();
      // Multiple N/A values expected for missing fields
      expect(screen.getAllByText('N/A').length).toBeGreaterThan(0);
    });

    it('handles missing session ID', () => {
      const data = {
        device_name: 'mothbox-001',
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Session ID')).toBeInTheDocument();
      // Multiple N/A values expected for missing fields
      expect(screen.getAllByText('N/A').length).toBeGreaterThan(0);
    });

    it('handles some fields null', () => {
      const data = {
        device_name: 'mothbox-001',
        firmware_version: null,
        session_id: 'session-123',
        installation_type: null,
        pi_model: 'Raspberry Pi 5',
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('mothbox-001')).toBeInTheDocument();
      expect(screen.getByText('session-123')).toBeInTheDocument();
      expect(screen.getByText('Raspberry Pi 5')).toBeInTheDocument();
      expect(screen.getAllByText('N/A')).toHaveLength(2); // firmware and installation
    });
  });

  describe('Copyable Fields', () => {
    it('device name is copyable when present', () => {
      const data = {
        device_name: 'mothbox-001',
      };

      render(<DeploymentTab data={data} />);

      const deviceField = screen.getByText('mothbox-001').closest('div');
      expect(deviceField).toBeInTheDocument();
    });

    it('firmware version is copyable when present', () => {
      const data = {
        firmware_version: '5.2.1',
      };

      render(<DeploymentTab data={data} />);

      const firmwareField = screen.getByText('5.2.1').closest('div');
      expect(firmwareField).toBeInTheDocument();
    });

    it('session ID is copyable when present', () => {
      const data = {
        session_id: 'session-2025-03-15-143045',
      };

      render(<DeploymentTab data={data} />);

      const sessionField = screen.getByText('session-2025-03-15-143045').closest('div');
      expect(sessionField).toBeInTheDocument();
    });

    it('fields are not copyable when missing', () => {
      const data = {
        device_name: null,
      };

      render(<DeploymentTab data={data} />);

      // All fields should show N/A
      expect(screen.getAllByText('N/A').length).toBeGreaterThan(0);
    });
  });

  describe('Complete Data Scenarios', () => {
    it('renders all fields when all data provided', () => {
      const data = {
        device_name: 'mothbox-backyard',
        firmware_version: '5.2.1',
        session_id: 'session-2025-03-15-143045',
        installation_type: 'production',
        pi_model: 'Raspberry Pi 5 Model B Rev 1.0',
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('mothbox-backyard')).toBeInTheDocument();
      expect(screen.getByText('5.2.1')).toBeInTheDocument();
      expect(screen.getByText('session-2025-03-15-143045')).toBeInTheDocument();
      expect(screen.getByText('production')).toBeInTheDocument();
      expect(screen.getByText('Raspberry Pi 5 Model B Rev 1.0')).toBeInTheDocument();
    });

    it('renders only available fields with N/A for missing', () => {
      const data = {
        device_name: 'mothbox-test',
        pi_model: 'Raspberry Pi 4',
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('mothbox-test')).toBeInTheDocument();
      expect(screen.getByText('Raspberry Pi 4')).toBeInTheDocument();
      expect(screen.getAllByText('N/A')).toHaveLength(3); // firmware, session, installation
    });
  });

  describe('Empty State', () => {
    it('shows empty state message for completely null data', () => {
      render(<DeploymentTab data={null} />);

      expect(screen.getByText('No deployment data available')).toBeInTheDocument();
    });

    it('does not show empty state when at least one field has data', () => {
      const data = {
        device_name: 'mothbox-001',
      };

      render(<DeploymentTab data={data} />);

      expect(screen.queryByText('No deployment data available')).not.toBeInTheDocument();
      expect(screen.getByText('mothbox-001')).toBeInTheDocument();
    });
  });
});
