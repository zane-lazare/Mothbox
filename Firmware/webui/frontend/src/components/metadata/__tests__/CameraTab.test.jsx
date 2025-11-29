import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CameraTab from '../CameraTab';

describe('CameraTab', () => {
  describe('Camera Information Section', () => {
    it('renders camera make', () => {
      const data = {
        camera: {
          make: 'Arducam',
        },
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Camera Make')).toBeInTheDocument();
      expect(screen.getByText('Arducam')).toBeInTheDocument();
    });

    it('renders camera model', () => {
      const data = {
        camera: {
          model: 'OwlSight 64MP',
        },
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Camera Model')).toBeInTheDocument();
      expect(screen.getByText('OwlSight 64MP')).toBeInTheDocument();
    });

    it('renders sensor', () => {
      const data = {
        camera: {
          sensor: 'ov64a40',
        },
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Sensor')).toBeInTheDocument();
      expect(screen.getByText('ov64a40')).toBeInTheDocument();
    });

    it('renders lens model', () => {
      const data = {
        camera: {
          lens: '6mm Wide Angle',
        },
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Lens Model')).toBeInTheDocument();
      expect(screen.getByText('6mm Wide Angle')).toBeInTheDocument();
    });

    it('renders all camera fields with complete data', () => {
      const data = {
        camera: {
          make: 'Arducam',
          model: 'OwlSight 64MP',
          sensor: 'ov64a40',
          lens: '6mm Wide Angle',
        },
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Arducam')).toBeInTheDocument();
      expect(screen.getByText('OwlSight 64MP')).toBeInTheDocument();
      expect(screen.getByText('ov64a40')).toBeInTheDocument();
      expect(screen.getByText('6mm Wide Angle')).toBeInTheDocument();
    });
  });

  describe('Camera Settings Section', () => {
    it('renders ISO (gain)', () => {
      const data = {
        capture: {
          iso: 400,
        },
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Gain (ISO)')).toBeInTheDocument();
      expect(screen.getByText('ISO 400')).toBeInTheDocument();
    });

    it('renders aperture', () => {
      const data = {
        capture: {
          f_number: 2.8,
        },
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Aperture')).toBeInTheDocument();
      expect(screen.getByText('f/2.8')).toBeInTheDocument();
    });

    it('renders exposure time', () => {
      const data = {
        capture: {
          exposure_time: '1/500',
        },
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Exposure Time')).toBeInTheDocument();
      expect(screen.getByText('1/500')).toBeInTheDocument();
    });

    it('renders focal length', () => {
      const data = {
        capture: {
          focal_length: '6.0mm',
        },
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Focal Length')).toBeInTheDocument();
      expect(screen.getByText('6.0mm')).toBeInTheDocument();
    });

    it('renders all capture settings', () => {
      const data = {
        capture: {
          iso: 800,
          f_number: 4.0,
          exposure_time: '1/125',
          focal_length: '6mm',
        },
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('ISO 800')).toBeInTheDocument();
      expect(screen.getByText('f/4')).toBeInTheDocument();
      expect(screen.getByText('1/125')).toBeInTheDocument();
      expect(screen.getByText('6mm')).toBeInTheDocument();
    });
  });

  describe('Null Data Handling', () => {
    it('shows empty state message when data is null', () => {
      render(<CameraTab data={null} />);

      expect(screen.getByText('No camera information available')).toBeInTheDocument();
    });

    it('shows empty state message when data is undefined', () => {
      render(<CameraTab />);

      expect(screen.getByText('No camera information available')).toBeInTheDocument();
    });

    it('shows empty state message when data is empty object', () => {
      render(<CameraTab data={{}} />);

      expect(screen.getByText('No camera information available')).toBeInTheDocument();
    });

    it('handles missing camera object', () => {
      const data = {
        capture: {
          iso: 400,
        },
      };

      render(<CameraTab data={data} />);

      // Should still render with N/A for camera fields
      expect(screen.getByText('Camera Make')).toBeInTheDocument();
      const naElements = screen.getAllByText('N/A');
      expect(naElements.length).toBeGreaterThan(0);
    });

    it('handles missing capture object', () => {
      const data = {
        camera: {
          make: 'Arducam',
        },
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Arducam')).toBeInTheDocument();
      // Capture fields should show N/A
      expect(screen.getByText('Gain (ISO)')).toBeInTheDocument();
    });

    it('renders N/A for missing fields', () => {
      const data = {
        camera: {
          make: 'Arducam',
        },
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Arducam')).toBeInTheDocument();
      // Other camera fields should show N/A
      const naElements = screen.getAllByText('N/A');
      expect(naElements.length).toBeGreaterThan(0);
    });
  });

  describe('Copyable Fields', () => {
    it('makes ISO copyable when present', () => {
      const data = {
        capture: {
          iso: 800,
        },
      };

      render(<CameraTab data={data} />);

      const copyButtons = screen.getAllByRole('button');
      expect(copyButtons.length).toBeGreaterThan(0);
    });

    it('makes aperture copyable when present', () => {
      const data = {
        capture: {
          f_number: 4.0,
        },
      };

      render(<CameraTab data={data} />);

      const copyButtons = screen.getAllByRole('button');
      expect(copyButtons.length).toBeGreaterThan(0);
    });

    it('makes exposure time copyable when present', () => {
      const data = {
        capture: {
          exposure_time: '1/250',
        },
      };

      render(<CameraTab data={data} />);

      const copyButtons = screen.getAllByRole('button');
      expect(copyButtons.length).toBeGreaterThan(0);
    });

    it('makes focal length copyable when present', () => {
      const data = {
        capture: {
          focal_length: '6mm',
        },
      };

      render(<CameraTab data={data} />);

      const copyButtons = screen.getAllByRole('button');
      expect(copyButtons.length).toBeGreaterThan(0);
    });
  });

  describe('Full Data Rendering', () => {
    it('renders all fields when full data is provided', () => {
      const data = {
        camera: {
          make: 'Arducam',
          model: 'OwlSight 64MP',
          sensor: 'ov64a40',
          lens: '6mm Wide Angle',
        },
        capture: {
          iso: 400,
          f_number: 2.8,
          exposure_time: '1/500',
          focal_length: '6.0mm',
        },
      };

      render(<CameraTab data={data} />);

      // Camera info section
      expect(screen.getByText('Camera Information')).toBeInTheDocument();
      expect(screen.getByText('Arducam')).toBeInTheDocument();
      expect(screen.getByText('OwlSight 64MP')).toBeInTheDocument();
      expect(screen.getByText('ov64a40')).toBeInTheDocument();
      expect(screen.getByText('6mm Wide Angle')).toBeInTheDocument();

      // Camera settings section
      expect(screen.getByText('Camera Settings')).toBeInTheDocument();
      expect(screen.getByText('ISO 400')).toBeInTheDocument();
      expect(screen.getByText('f/2.8')).toBeInTheDocument();
      expect(screen.getByText('1/500')).toBeInTheDocument();
      expect(screen.getByText('6.0mm')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles empty string values', () => {
      const data = {
        camera: {
          make: '',
          model: '',
        },
        capture: {
          exposure_time: '',
          focal_length: '',
        },
      };

      render(<CameraTab data={data} />);

      // Empty strings should show N/A
      const naElements = screen.getAllByText('N/A');
      expect(naElements.length).toBeGreaterThan(0);
    });

    it('handles zero values as N/A (invalid camera values)', () => {
      const data = {
        capture: {
          iso: 0,
          f_number: 0,
        },
      };

      render(<CameraTab data={data} />);

      // Zero values should show N/A since ISO=0 and f/0 are not valid
      const naElements = screen.getAllByText('N/A');
      expect(naElements.length).toBeGreaterThan(0);
    });
  });
});
