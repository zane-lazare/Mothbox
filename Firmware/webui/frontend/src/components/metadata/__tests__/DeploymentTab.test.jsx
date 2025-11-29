import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import DeploymentTab from '../DeploymentTab';

describe('DeploymentTab', () => {
  describe('Device Info Section', () => {
    it('renders Mothbox ID', () => {
      const data = {
        deployment: {
          mothbox_id: 'mothbox-backyard',
        },
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Mothbox ID')).toBeInTheDocument();
      expect(screen.getByText('mothbox-backyard')).toBeInTheDocument();
    });

    it('renders capture type', () => {
      const data = {
        deployment: {
          capture_type: 'instant',
        },
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Capture Type')).toBeInTheDocument();
      expect(screen.getByText('Instant Capture')).toBeInTheDocument();
    });

    it('renders firmware version', () => {
      const data = {
        deployment: {
          firmware_version: '5',
        },
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Firmware Version')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('formats capture type correctly', () => {
      const testCases = [
        { type: 'instant', expected: 'Instant Capture' },
        { type: 'test', expected: 'Test Capture' },
        { type: 'scheduled', expected: 'Scheduled' },
        { type: 'bracket', expected: 'Focus Bracket' },
        { type: 'hdr', expected: 'HDR' },
        { type: 'unknown', expected: 'unknown' },
      ];

      testCases.forEach(({ type, expected }) => {
        const { unmount } = render(
          <DeploymentTab data={{ deployment: { capture_type: type } }} />
        );
        expect(screen.getByText(expected)).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe('Series Info Section', () => {
    it('renders series type', () => {
      const data = {
        deployment: {
          series_type: 'hdr',
        },
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Series Type')).toBeInTheDocument();
      expect(screen.getByText('hdr')).toBeInTheDocument();
    });

    it('renders series count and index', () => {
      const data = {
        deployment: {
          series_type: 'focus_bracket',
          series_count: 5,
          series_index: 2,
        },
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Series Count')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('Series Index')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });

  describe('GPS Location Section', () => {
    it('renders GPS coordinates when available', () => {
      const data = {
        deployment: {},
        location: {
          latitude: 40.7128,
          longitude: -74.006,
        },
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('GPS Location')).toBeInTheDocument();
      // Latitude/Longitude appear twice: once in decimal, once in DMS
      expect(screen.getAllByText('Latitude').length).toBe(2);
      expect(screen.getAllByText('Longitude').length).toBe(2);
    });

    it('renders altitude when available', () => {
      const data = {
        deployment: {},
        location: {
          latitude: 40.7128,
          longitude: -74.006,
          altitude: 10.5,
        },
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Altitude')).toBeInTheDocument();
    });

    it('shows no GPS message when location is not available', () => {
      const data = {
        deployment: {
          mothbox_id: 'mothbox-001',
        },
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('No GPS information available')).toBeInTheDocument();
    });

    it('renders map link when GPS is available', () => {
      const data = {
        deployment: {},
        location: {
          latitude: 40.7128,
          longitude: -74.006,
        },
      };

      render(<DeploymentTab data={data} />);

      const mapLink = screen.getByRole('link', { name: /view on map/i });
      expect(mapLink).toBeInTheDocument();
      expect(mapLink).toHaveAttribute('href', expect.stringContaining('google.com/maps'));
    });

    it('renders GPS quality indicators', () => {
      const data = {
        deployment: {},
        location: {
          latitude: 40.7128,
          longitude: -74.006,
          satellites: 8,
          hdop: 1.2,
        },
      };

      render(<DeploymentTab data={data} />);

      expect(screen.getByText('Satellites')).toBeInTheDocument();
      expect(screen.getByText('8')).toBeInTheDocument();
      expect(screen.getByText('HDOP')).toBeInTheDocument();
      expect(screen.getByText('1.2')).toBeInTheDocument();
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

    it('handles empty deployment object', () => {
      render(<DeploymentTab data={{ deployment: {} }} />);

      expect(screen.getByText('Mothbox ID')).toBeInTheDocument();
      // Multiple N/A values for empty fields
      const naElements = screen.getAllByText('N/A');
      expect(naElements.length).toBeGreaterThan(0);
    });
  });

  describe('Full Data Rendering', () => {
    it('renders all fields when full data is provided', () => {
      const data = {
        deployment: {
          mothbox_id: 'mothbox-forest',
          capture_type: 'scheduled',
          firmware_version: '5',
          series_type: 'single',
        },
        location: {
          latitude: 37.7749,
          longitude: -122.4194,
          altitude: 50,
          satellites: 12,
          hdop: 0.8,
        },
      };

      render(<DeploymentTab data={data} />);

      // Device info
      expect(screen.getByText('mothbox-forest')).toBeInTheDocument();
      expect(screen.getByText('Scheduled')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();

      // GPS location
      expect(screen.getByText('GPS Location')).toBeInTheDocument();
      expect(screen.getByText('12')).toBeInTheDocument(); // satellites
    });
  });
});
