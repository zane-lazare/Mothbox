import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CameraTab from '../CameraTab';

describe('CameraTab', () => {
  const mockCameraData = {
    camera: {
      make: 'Arducam',
      model: 'OwlSight 64MP',
      lens_make: 'Arducam',
      lens_model: '6mm Wide Angle'
    },
    iso: 400,
    aperture: 2.8,
    shutter_speed: 0.033333,
    focal_length: 6.0,
    exposure_mode: 'Manual',
    metering_mode: 'CenterWeighted'
  };

  describe('Rendering', () => {
    it('renders all camera fields with complete data', () => {
      render(<CameraTab data={mockCameraData} />);

      // Camera info
      expect(screen.getByText('Camera Make')).toBeInTheDocument();
      expect(screen.getAllByText('Arducam').length).toBeGreaterThan(0); // Both camera and lens make
      expect(screen.getByText('Camera Model')).toBeInTheDocument();
      expect(screen.getByText('OwlSight 64MP')).toBeInTheDocument();

      // Lens info
      expect(screen.getByText('Lens Make')).toBeInTheDocument();
      expect(screen.getByText('Lens Model')).toBeInTheDocument();
      expect(screen.getByText('6mm Wide Angle')).toBeInTheDocument();

      // Technical settings
      expect(screen.getByText('ISO')).toBeInTheDocument();
      expect(screen.getByText('ISO 400')).toBeInTheDocument();
      expect(screen.getByText('Aperture')).toBeInTheDocument();
      expect(screen.getByText('f/2.8')).toBeInTheDocument();
      expect(screen.getByText('Shutter Speed')).toBeInTheDocument();
      expect(screen.getByText('1/30s')).toBeInTheDocument();
      expect(screen.getByText('Focal Length')).toBeInTheDocument();
      expect(screen.getByText('6mm')).toBeInTheDocument(); // Formatter strips .0 from whole numbers
    });

    it('renders N/A for missing camera fields', () => {
      const partialData = {
        camera: {
          make: 'Arducam'
        },
        iso: 400
      };

      render(<CameraTab data={partialData} />);

      expect(screen.getByText('Arducam')).toBeInTheDocument();
      expect(screen.getByText('ISO 400')).toBeInTheDocument();

      // Check for N/A in missing fields
      const naElements = screen.getAllByText('N/A');
      expect(naElements.length).toBeGreaterThan(0);
    });

    it('shows empty state message when data is null', () => {
      render(<CameraTab data={null} />);

      expect(screen.getByText('No camera information available')).toBeInTheDocument();
    });

    it('shows empty state message when data is empty object', () => {
      render(<CameraTab data={{}} />);

      expect(screen.getByText('No camera information available')).toBeInTheDocument();
    });

    it('handles missing camera object', () => {
      const dataWithoutCamera = {
        iso: 400,
        aperture: 2.8
      };

      render(<CameraTab data={dataWithoutCamera} />);

      expect(screen.getByText('ISO 400')).toBeInTheDocument();
      expect(screen.getByText('f/2.8')).toBeInTheDocument();
    });
  });

  describe('Exposure Time Formatting', () => {
    it('formats fast shutter speeds as fractions', () => {
      const data = { shutter_speed: 0.001 }; // 1/1000
      render(<CameraTab data={data} />);

      expect(screen.getByText('1/1000s')).toBeInTheDocument();
    });

    it('formats slow shutter speeds in seconds', () => {
      const data = { shutter_speed: 2.5 };
      render(<CameraTab data={data} />);

      expect(screen.getByText('2.5s')).toBeInTheDocument();
    });

    it('formats one-second exposure correctly', () => {
      const data = { shutter_speed: 1.0 };
      render(<CameraTab data={data} />);

      expect(screen.getByText('1s')).toBeInTheDocument();
    });
  });

  describe('Technical Fields', () => {
    it('formats ISO correctly', () => {
      const data = { iso: 1600 };
      render(<CameraTab data={data} />);

      expect(screen.getByText('ISO 1600')).toBeInTheDocument();
    });

    it('formats aperture with f-stop notation', () => {
      const data = { aperture: 5.6 };
      render(<CameraTab data={data} />);

      expect(screen.getByText('f/5.6')).toBeInTheDocument();
    });

    it('formats focal length with mm unit', () => {
      const data = { focal_length: 24.5 };
      render(<CameraTab data={data} />);

      expect(screen.getByText('24.5mm')).toBeInTheDocument();
    });

    it('renders exposure mode when available', () => {
      const data = { exposure_mode: 'Auto' };
      render(<CameraTab data={data} />);

      expect(screen.getByText('Exposure Mode')).toBeInTheDocument();
      expect(screen.getByText('Auto')).toBeInTheDocument();
    });

    it('renders metering mode when available', () => {
      const data = { metering_mode: 'Spot' };
      render(<CameraTab data={data} />);

      expect(screen.getByText('Metering Mode')).toBeInTheDocument();
      expect(screen.getByText('Spot')).toBeInTheDocument();
    });
  });

  describe('Copyable Fields', () => {
    it('makes ISO copyable', () => {
      render(<CameraTab data={{ iso: 800 }} />);

      const copyButtons = screen.getAllByRole('button');
      expect(copyButtons.length).toBeGreaterThan(0);
    });

    it('makes aperture copyable', () => {
      render(<CameraTab data={{ aperture: 4.0 }} />);

      const copyButtons = screen.getAllByRole('button');
      expect(copyButtons.length).toBeGreaterThan(0);
    });

    it('makes shutter speed copyable', () => {
      render(<CameraTab data={{ shutter_speed: 0.01 }} />);

      const copyButtons = screen.getAllByRole('button');
      expect(copyButtons.length).toBeGreaterThan(0);
    });

    it('makes focal length copyable', () => {
      render(<CameraTab data={{ focal_length: 35 }} />);

      const copyButtons = screen.getAllByRole('button');
      expect(copyButtons.length).toBeGreaterThan(0);
    });
  });

  describe('Partial Data Handling', () => {
    it('handles only camera make and model', () => {
      const data = {
        camera: {
          make: 'Canon',
          model: 'EOS R5'
        }
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Canon')).toBeInTheDocument();
      expect(screen.getByText('EOS R5')).toBeInTheDocument();
    });

    it('handles only technical settings without camera info', () => {
      const data = {
        iso: 200,
        aperture: 1.8,
        shutter_speed: 0.0125,
        focal_length: 50
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('ISO 200')).toBeInTheDocument();
      expect(screen.getByText('f/1.8')).toBeInTheDocument();
      expect(screen.getByText('1/80s')).toBeInTheDocument();
      expect(screen.getByText('50mm')).toBeInTheDocument();
    });

    it('handles mix of present and missing fields', () => {
      const data = {
        camera: {
          make: 'Nikon'
        },
        iso: 3200,
        focal_length: 85
      };

      render(<CameraTab data={data} />);

      expect(screen.getByText('Nikon')).toBeInTheDocument();
      expect(screen.getByText('ISO 3200')).toBeInTheDocument();
      expect(screen.getByText('85mm')).toBeInTheDocument();
    });
  });
});
