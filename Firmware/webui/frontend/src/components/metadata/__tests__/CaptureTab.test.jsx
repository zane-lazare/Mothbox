import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import CaptureTab from '../CaptureTab';

describe('CaptureTab', () => {
  describe('Capture Details Section', () => {
    it('renders timestamp when provided', () => {
      const data = {
        capture: {
          timestamp: '2025-03-15T14:30:45Z',
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Timestamp')).toBeInTheDocument();
      // The formatTimestamp function formats the date
      expect(screen.getByText(/2025/)).toBeInTheDocument();
    });

    it('renders focal length when provided', () => {
      const data = {
        capture: {
          focal_length: '6mm',
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Focal Length')).toBeInTheDocument();
      expect(screen.getByText('6mm')).toBeInTheDocument();
    });
  });

  describe('Exposure Settings Section', () => {
    it('renders exposure mode', () => {
      const data = {
        capture: {
          exposure_mode: 'Auto',
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Exposure Mode')).toBeInTheDocument();
      expect(screen.getByText('Auto')).toBeInTheDocument();
    });

    it('renders exposure time', () => {
      const data = {
        capture: {
          exposure_time: '1/500',
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Exposure Time')).toBeInTheDocument();
      expect(screen.getByText('1/500')).toBeInTheDocument();
    });

    it('renders ISO (gain)', () => {
      const data = {
        capture: {
          iso: 400,
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Gain (ISO)')).toBeInTheDocument();
      expect(screen.getByText('400')).toBeInTheDocument();
    });

    it('renders metering mode when exposure mode is Auto', () => {
      const data = {
        capture: {
          exposure_mode: 'Auto',
          metering_mode: 'CenterWeighted',
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Metering Mode')).toBeInTheDocument();
      expect(screen.getByText('CenterWeighted')).toBeInTheDocument();
    });

    it('hides metering mode when exposure mode is not Auto', () => {
      const data = {
        capture: {
          exposure_mode: 'Manual',
          metering_mode: 'CenterWeighted',
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.queryByText('Metering Mode')).not.toBeInTheDocument();
    });
  });

  describe('Focus Settings Section', () => {
    it('renders focus mode', () => {
      const data = {
        capture: {
          focus_mode: 'Manual',
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Focus Mode')).toBeInTheDocument();
      expect(screen.getByText('Manual')).toBeInTheDocument();
    });

    it('renders lens position when focus mode is Manual', () => {
      const data = {
        capture: {
          focus_mode: 'Manual',
          lens_position: 2.5,
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Lens Position')).toBeInTheDocument();
      expect(screen.getByText('2.50 diopters')).toBeInTheDocument();
    });

    it('hides lens position when focus mode is not Manual', () => {
      const data = {
        capture: {
          focus_mode: 'Auto Single',
          lens_position: 2.5,
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.queryByText('Lens Position')).not.toBeInTheDocument();
    });

    it('renders AF range and speed for Auto Single mode', () => {
      const data = {
        capture: {
          focus_mode: 'Auto Single',
          af_range: 'Full',
          af_speed: 'Normal',
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('AF Range')).toBeInTheDocument();
      expect(screen.getByText('Full')).toBeInTheDocument();
      expect(screen.getByText('AF Speed')).toBeInTheDocument();
      expect(screen.getByText('Normal')).toBeInTheDocument();
    });

    it('renders AF range and speed for Continuous AF mode', () => {
      const data = {
        capture: {
          focus_mode: 'Continuous AF',
          af_range: 'Macro',
          af_speed: 'Fast',
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('AF Range')).toBeInTheDocument();
      expect(screen.getByText('Macro')).toBeInTheDocument();
      expect(screen.getByText('AF Speed')).toBeInTheDocument();
      expect(screen.getByText('Fast')).toBeInTheDocument();
    });
  });

  describe('Image Processing Section', () => {
    it('renders noise reduction', () => {
      const data = {
        capture: {
          noise_reduction: 'High Quality',
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Noise Reduction')).toBeInTheDocument();
      expect(screen.getByText('High Quality')).toBeInTheDocument();
    });

    it('renders sharpness', () => {
      const data = {
        capture: {
          sharpness: 2,
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Sharpness')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('renders brightness', () => {
      const data = {
        capture: {
          brightness: 0.25,
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Brightness')).toBeInTheDocument();
      expect(screen.getByText('0.25')).toBeInTheDocument();
    });

    it('renders contrast', () => {
      const data = {
        capture: {
          contrast: 1,
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Contrast')).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    it('renders saturation', () => {
      const data = {
        capture: {
          saturation: 1,
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Saturation')).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument();
    });
  });

  describe('Colour & Advanced Section', () => {
    it('renders aperture (f_number)', () => {
      const data = {
        capture: {
          f_number: 'f/2.8',
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Aperture')).toBeInTheDocument();
      expect(screen.getByText('f/2.8')).toBeInTheDocument();
    });

    it('renders white balance (colour balance)', () => {
      const data = {
        capture: {
          white_balance: 'Auto',
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Colour Balance')).toBeInTheDocument();
      expect(screen.getByText('Auto')).toBeInTheDocument();
    });

    it('renders colour gains when provided', () => {
      const data = {
        capture: {
          colour_gain_red: 1.234,
          colour_gain_blue: 2.345,
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Red Gain')).toBeInTheDocument();
      expect(screen.getByText('1.234')).toBeInTheDocument();
      expect(screen.getByText('Blue Gain')).toBeInTheDocument();
      expect(screen.getByText('2.345')).toBeInTheDocument();
    });

    it('renders flash status when fired', () => {
      const data = {
        capture: {
          flash: true,
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Flash')).toBeInTheDocument();
      expect(screen.getByText('Fired')).toBeInTheDocument();
    });

    it('renders flash status when not fired', () => {
      const data = {
        capture: {
          flash: false,
        },
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Flash')).toBeInTheDocument();
      expect(screen.getByText('Did not fire')).toBeInTheDocument();
    });
  });

  describe('Null Data Handling', () => {
    it('handles null data', () => {
      render(<CaptureTab data={null} />);

      expect(screen.getByText('No capture data available')).toBeInTheDocument();
    });

    it('handles undefined data', () => {
      render(<CaptureTab />);

      expect(screen.getByText('No capture data available')).toBeInTheDocument();
    });

    it('handles missing capture object', () => {
      const data = {};

      render(<CaptureTab data={data} />);

      // Should render section headers with N/A values
      expect(screen.getByText('Capture Details')).toBeInTheDocument();
      const naElements = screen.getAllByText('N/A');
      expect(naElements.length).toBeGreaterThan(0);
    });

    it('handles empty capture object', () => {
      const data = {
        capture: {},
      };

      render(<CaptureTab data={data} />);

      expect(screen.getByText('Capture Details')).toBeInTheDocument();
      const naElements = screen.getAllByText('N/A');
      expect(naElements.length).toBeGreaterThan(0);
    });
  });

  describe('Full Data Rendering', () => {
    it('renders all fields when full data is provided', () => {
      const data = {
        capture: {
          timestamp: '2025-03-15T14:30:45Z',
          focal_length: '6mm',
          exposure_mode: 'Auto',
          exposure_time: '1/500',
          iso: 400,
          metering_mode: 'CenterWeighted',
          focus_mode: 'Auto Single',
          af_range: 'Full',
          af_speed: 'Normal',
          noise_reduction: 'High Quality',
          sharpness: 2,
          brightness: 0.0,
          contrast: 1,
          saturation: 1,
          f_number: 'f/2.8',
          white_balance: 'Auto',
          colour_gain_red: 1.5,
          colour_gain_blue: 1.3,
          flash: false,
        },
      };

      render(<CaptureTab data={data} />);

      // Section headers
      expect(screen.getByText('Capture Details')).toBeInTheDocument();
      expect(screen.getByText('Exposure Settings')).toBeInTheDocument();
      expect(screen.getByText('Focus Settings')).toBeInTheDocument();
      expect(screen.getByText('Image Processing')).toBeInTheDocument();
      expect(screen.getByText('Colour & Advanced')).toBeInTheDocument();

      // Some key values
      expect(screen.getByText(/2025/)).toBeInTheDocument();
      expect(screen.getByText('6mm')).toBeInTheDocument();
      // "Auto" appears twice (exposure_mode and white_balance)
      expect(screen.getAllByText('Auto').length).toBe(2);
      expect(screen.getByText('400')).toBeInTheDocument();
      expect(screen.getByText('Did not fire')).toBeInTheDocument();
    });
  });
});
