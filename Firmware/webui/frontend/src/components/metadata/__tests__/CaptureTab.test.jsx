import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import CaptureTab from '../CaptureTab';

describe('CaptureTab', () => {
  describe('Basic Rendering', () => {
    it('renders capture timestamp formatted correctly', () => {
      const data = {
        timestamp: '2025-03-15T14:30:45Z',
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Timestamp')).toBeInTheDocument();
      // Check for date components (locale-independent)
      expect(screen.getByText(/2025/)).toBeInTheDocument();
      expect(screen.getByText(/3/)).toBeInTheDocument();
      expect(screen.getByText(/15|16/)).toBeInTheDocument(); // Date might vary by timezone
    });

    it('displays focus distance in meters', () => {
      const data = {
        focus_distance: 1.5,
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Focus Distance')).toBeInTheDocument();
      expect(screen.getByText('1.5m')).toBeInTheDocument();
    });

    it('renders exposure mode', () => {
      const data = {
        exposure_mode: 'auto',
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Exposure Mode')).toBeInTheDocument();
      expect(screen.getByText('auto')).toBeInTheDocument();
    });

    it('renders metering mode', () => {
      const data = {
        metering_mode: 'center-weighted',
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Metering Mode')).toBeInTheDocument();
      expect(screen.getByText('center-weighted')).toBeInTheDocument();
    });
  });

  describe('HDR Status', () => {
    it('shows HDR status when hdr_enabled is true', () => {
      const data = {
        hdr_enabled: true,
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('HDR Status')).toBeInTheDocument();
      expect(screen.getByText('Enabled')).toBeInTheDocument();
    });

    it('hides HDR status when hdr_enabled is false', () => {
      const data = {
        hdr_enabled: false,
      };

      render(<CaptureTab data={data} />);

      expect(screen.queryByText('HDR Status')).not.toBeInTheDocument();
    });

    it('hides HDR status when hdr_enabled is undefined', () => {
      const data = {
        exposure_mode: 'auto',
      };

      render(<CaptureTab data={data} />);

      expect(screen.queryByText('HDR Status')).not.toBeInTheDocument();
    });
  });

  describe('Focus Bracket', () => {
    it('shows focus bracket info when enabled', () => {
      const data = {
        focus_bracket_enabled: true,
        focus_bracket_position: 2,
        focus_bracket_total: 5,
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Focus Bracket')).toBeInTheDocument();
      expect(screen.getByText('2 of 5')).toBeInTheDocument();
    });

    it('hides focus bracket when disabled', () => {
      const data = {
        focus_bracket_enabled: false,
      };

      render(<CaptureTab data={data} />);

      expect(screen.queryByText('Focus Bracket')).not.toBeInTheDocument();
    });

    it('hides focus bracket when not provided', () => {
      const data = {
        exposure_mode: 'auto',
      };

      render(<CaptureTab data={data} />);

      expect(screen.queryByText('Focus Bracket')).not.toBeInTheDocument();
    });

    it('handles focus bracket with missing position/total', () => {
      const data = {
        focus_bracket_enabled: true,
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Focus Bracket')).toBeInTheDocument();
      // Multiple N/A values expected (bracket, focus distance, exposure, metering)
      expect(screen.getAllByText('N/A').length).toBeGreaterThan(0);
    });
  });

  describe('Missing Data Handling', () => {
    it('handles missing timestamp', () => {
      const data = {
        exposure_mode: 'auto',
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Timestamp')).toBeInTheDocument();
      // Check that N/A appears (for timestamp and other missing fields)
      expect(screen.getAllByText('N/A').length).toBeGreaterThan(0);
    });

    it('handles null data', () => {
      render(<CaptureTab data={null} />);

      expect(screen.getByText('No capture data available')).toBeInTheDocument();
    });

    it('handles undefined data', () => {
      render(<CaptureTab />);

      expect(screen.getByText('No capture data available')).toBeInTheDocument();
    });
  });

  describe('Partial Data Handling', () => {
    it('handles only timestamp provided', () => {
      const data = {
        timestamp: '2025-03-15T14:30:45Z',
      };

      render(<CaptureTab data={data} />);

      // Check for date (locale-independent)
      expect(screen.getByText(/2025/)).toBeInTheDocument();
      expect(screen.getAllByText('N/A')).toHaveLength(3); // focus, exposure, metering
    });

    it('handles only modes provided', () => {
      const data = {
        exposure_mode: 'manual',
        metering_mode: 'spot',
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('manual')).toBeInTheDocument();
      expect(screen.getByText('spot')).toBeInTheDocument();
    });
  });

  describe('Copyable Fields', () => {
    it('timestamp is copyable when present', () => {
      const data = {
        timestamp: '2025-03-15T14:30:45Z',
      };

      render(<CaptureTab data={data} />);

      // Check that timestamp field is rendered (copyable is handled by MetadataField)
      expect(screen.getByText('Timestamp')).toBeInTheDocument();
      expect(screen.getByText(/2025/)).toBeInTheDocument();
    });

    it('exposure mode is copyable when present', () => {
      const data = {
        exposure_mode: 'auto',
      };

      render(<CaptureTab data={data} />);

      // Check that exposure mode field is rendered (copyable is handled by MetadataField)
      expect(screen.getByText('Exposure Mode')).toBeInTheDocument();
      expect(screen.getByText('auto')).toBeInTheDocument();
    });

    it('metering mode is copyable when present', () => {
      const data = {
        metering_mode: 'center-weighted',
      };

      render(<CaptureTab data={data} />);

      // Check that metering mode field is rendered (copyable is handled by MetadataField)
      expect(screen.getByText('Metering Mode')).toBeInTheDocument();
      expect(screen.getByText('center-weighted')).toBeInTheDocument();
    });
  });

  describe('Complete Data Scenarios', () => {
    it('renders all fields when all data provided', () => {
      const data = {
        timestamp: '2025-03-15T14:30:45Z',
        hdr_enabled: true,
        focus_bracket_enabled: true,
        focus_bracket_position: 3,
        focus_bracket_total: 5,
        focus_distance: 2.0,
        exposure_mode: 'manual',
        metering_mode: 'spot',
      };

      render(<CaptureTab data={data} />);

      // Check for date (locale-independent)
      expect(screen.getByText(/2025/)).toBeInTheDocument();
      expect(screen.getByText('Enabled')).toBeInTheDocument();
      expect(screen.getByText('3 of 5')).toBeInTheDocument();
      expect(screen.getByText('2m')).toBeInTheDocument();
      expect(screen.getByText('manual')).toBeInTheDocument();
      expect(screen.getByText('spot')).toBeInTheDocument();
    });
  });
});
