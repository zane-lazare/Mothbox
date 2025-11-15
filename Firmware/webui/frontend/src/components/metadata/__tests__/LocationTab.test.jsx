import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import LocationTab from '../LocationTab';

describe('LocationTab', () => {
  const mockGPSData = {
    lat: 40.7128,
    lon: -74.0060,
    gps_fix_mode: 3,
    alt: 10.5,
    gps_satellites_used: 8,
    gps_hdop: 1.2,
    gps_pdop: 2.1
  };

  describe('Rendering', () => {
    it('renders GPS coordinates in decimal format', () => {
      render(<LocationTab data={mockGPSData} />);

      expect(screen.getByText('Decimal Degrees')).toBeInTheDocument();
      expect(screen.getByText('40.712800°')).toBeInTheDocument();
      expect(screen.getByText('-74.006000°')).toBeInTheDocument(); // Trailing zero is removed by JavaScript
    });

    it('renders GPS coordinates in DMS format', () => {
      render(<LocationTab data={mockGPSData} />);

      // Look for DMS section header
      expect(screen.getByText(/Degrees.*Minutes.*Seconds/i)).toBeInTheDocument();

      // Check for DMS values (latitude: 40°42'46.1" N)
      expect(screen.getByText(/40°42'46\.1" N/)).toBeInTheDocument();

      // Check for DMS values (longitude: 74°00'21.6" W)
      expect(screen.getByText(/74°00'21\.6" W/)).toBeInTheDocument();
    });

    it('renders altitude only for 3D fix', () => {
      const dataWith3DFix = { ...mockGPSData, gps_fix_mode: 3, alt: 152.5 };
      render(<LocationTab data={dataWith3DFix} />);

      expect(screen.getByText('Altitude')).toBeInTheDocument();
      expect(screen.getByText('152.5 m')).toBeInTheDocument();
    });

    it('does not render altitude for 2D fix', () => {
      const dataWith2DFix = { ...mockGPSData, gps_fix_mode: 2, alt: 152.5 };
      render(<LocationTab data={dataWith2DFix} />);

      expect(screen.queryByText('Altitude')).not.toBeInTheDocument();
      expect(screen.queryByText('152.5 m')).not.toBeInTheDocument();
    });

    it('shows no GPS data message when data is null', () => {
      render(<LocationTab data={null} />);

      expect(screen.getByText('No GPS information available')).toBeInTheDocument();
    });

    it('shows no GPS data message when coordinates are missing', () => {
      const dataWithoutCoords = { gps_fix_mode: 1 };
      render(<LocationTab data={dataWithoutCoords} />);

      expect(screen.getByText('No GPS information available')).toBeInTheDocument();
    });

    it('shows no GPS data message when fix mode is 0', () => {
      const dataWithNoFix = { ...mockGPSData, gps_fix_mode: 0 };
      render(<LocationTab data={dataWithNoFix} />);

      expect(screen.getByText('No GPS information available')).toBeInTheDocument();
    });
  });

  describe('Copyable Fields', () => {
    it('makes latitude copyable', () => {
      render(<LocationTab data={mockGPSData} />);

      const copyButtons = screen.getAllByRole('button');
      expect(copyButtons.length).toBeGreaterThan(0);
    });

    it('makes longitude copyable', () => {
      render(<LocationTab data={mockGPSData} />);

      const copyButtons = screen.getAllByRole('button');
      expect(copyButtons.length).toBeGreaterThan(0);
    });

    it('makes altitude copyable when available', () => {
      const dataWith3DFix = { ...mockGPSData, gps_fix_mode: 3, alt: 100 };
      render(<LocationTab data={dataWith3DFix} />);

      const copyButtons = screen.getAllByRole('button');
      expect(copyButtons.length).toBeGreaterThan(0);
    });
  });

  describe('Map Link', () => {
    it('renders map link with correct coordinates', () => {
      render(<LocationTab data={mockGPSData} />);

      const mapLink = screen.getByRole('link', { name: /view on map/i });
      expect(mapLink).toBeInTheDocument();
      expect(mapLink).toHaveAttribute('href', 'https://www.google.com/maps?q=40.7128,-74.006');
      expect(mapLink).toHaveAttribute('target', '_blank');
      expect(mapLink).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('does not render map link when no GPS data', () => {
      render(<LocationTab data={null} />);

      expect(screen.queryByRole('link', { name: /view on map/i })).not.toBeInTheDocument();
    });
  });

  describe('Hemisphere Handling', () => {
    it('handles southern hemisphere latitude', () => {
      const southernData = {
        lat: -33.8688,
        lon: 151.2093,
        gps_fix_mode: 2
      };

      render(<LocationTab data={southernData} />);

      expect(screen.getByText('-33.868800°')).toBeInTheDocument();
      expect(screen.getByText(/33°52'07\.7" S/)).toBeInTheDocument();
    });

    it('handles eastern hemisphere longitude', () => {
      const easternData = {
        lat: 35.6762,
        lon: 139.6503,
        gps_fix_mode: 2
      };

      render(<LocationTab data={easternData} />);

      expect(screen.getByText('139.650300°')).toBeInTheDocument();
      expect(screen.getByText(/139°39'01\.1" E/)).toBeInTheDocument();
    });

    it('handles western hemisphere longitude', () => {
      const westernData = {
        lat: 40.7128,
        lon: -74.0060,
        gps_fix_mode: 2
      };

      render(<LocationTab data={westernData} />);

      expect(screen.getByText('-74.006000°')).toBeInTheDocument(); // Trailing zero removed
      expect(screen.getByText(/74°00'21\.6" W/)).toBeInTheDocument();
    });

    it('handles northern hemisphere latitude', () => {
      const northernData = {
        lat: 51.5074,
        lon: -0.1278,
        gps_fix_mode: 2
      };

      render(<LocationTab data={northernData} />);

      expect(screen.getByText('51.507400°')).toBeInTheDocument();
      expect(screen.getByText(/51°30'26\.6" N/)).toBeInTheDocument();
    });
  });

  describe('GPS Quality Indicators', () => {
    it('renders satellite count when available', () => {
      render(<LocationTab data={mockGPSData} />);

      expect(screen.getByText('Satellites')).toBeInTheDocument();
      expect(screen.getByText('8')).toBeInTheDocument();
    });

    it('renders HDOP when available', () => {
      render(<LocationTab data={mockGPSData} />);

      expect(screen.getByText('HDOP')).toBeInTheDocument();
      expect(screen.getByText('1.2')).toBeInTheDocument();
    });

    it('renders PDOP when available', () => {
      render(<LocationTab data={mockGPSData} />);

      expect(screen.getByText('PDOP')).toBeInTheDocument();
      expect(screen.getByText('2.1')).toBeInTheDocument();
    });

    it('handles missing GPS quality data', () => {
      const minimalData = {
        lat: 40.7128,
        lon: -74.0060,
        gps_fix_mode: 2
      };

      render(<LocationTab data={minimalData} />);

      // Should still render coordinates
      expect(screen.getByText('40.712800°')).toBeInTheDocument();

      // Quality indicators should show N/A or not appear
      expect(screen.queryByText('Satellites')).toBeInTheDocument();
    });
  });

  describe('Partial Data Handling', () => {
    it('handles latitude without longitude', () => {
      const partialData = { lat: 40.7128, gps_fix_mode: 2 };
      render(<LocationTab data={partialData} />);

      expect(screen.getByText('No GPS information available')).toBeInTheDocument();
    });

    it('handles longitude without latitude', () => {
      const partialData = { lon: -74.0060, gps_fix_mode: 2 };
      render(<LocationTab data={partialData} />);

      expect(screen.getByText('No GPS information available')).toBeInTheDocument();
    });

    it('renders both coordinates when both present', () => {
      const completeData = {
        lat: 40.7128,
        lon: -74.0060,
        gps_fix_mode: 2
      };

      render(<LocationTab data={completeData} />);

      expect(screen.getByText('40.712800°')).toBeInTheDocument();
      expect(screen.getByText('-74.006000°')).toBeInTheDocument(); // Trailing zero removed
    });
  });
});
