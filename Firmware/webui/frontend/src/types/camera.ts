/**
 * Camera and settings types
 */

export interface CameraSettings {
  resolution: string
  exposure_mode: 'auto' | 'manual'
  iso: number
  shutter_speed: number
  aperture?: number
  white_balance: string
  focus_mode: 'auto' | 'manual' | 'continuous'
  focus_strategy: string
  hdr_enabled: boolean
  focus_bracketing_enabled: boolean
  [key: string]: string | number | boolean | undefined
}

export interface CameraPreset {
  name: string
  description?: string
  settings: CameraSettings
  is_builtin: boolean
  workflow?: 'photo' | 'liveview' | 'both'
}

export interface LiveViewSettings {
  target_fps: number
  jpeg_quality: number
  stream_mode: 'simplejpeg' | 'mjpeg_hardware'
  resolution: [number, number]
}

export interface CameraMetadata {
  exposure_time?: number
  analogue_gain?: number
  digital_gain?: number
  colour_gains?: [number, number]
  lens_position?: number
  focus_fo_m?: number
  focus_fom?: number
  af_state?: string
  lux?: number
  colour_temperature?: number
  actual_zoom_center_x?: number
  actual_zoom_center_y?: number
  crop_fraction_x?: number
  crop_fraction_y?: number
  error?: string
  sensor_timestamp?: number
  frame_duration?: number
  sensor_black_level?: number
  sensor_temperature?: number
  scaler_crop?: [number, number, number, number]
  ae_locked?: boolean
  awb_locked?: boolean
  saturation?: number
  contrast?: number
  sharpness?: number
  brightness?: number
}

export interface ActionResult {
  success?: boolean
  type: 'success' | 'error' | 'warning'
  title: string
  message: string
  error?: string
}

export interface CalibrationProgress {
  step: string
  progress: number
  total_steps?: number
  message: string
}

export interface LiveControls {
  exposure_time?: number
  analogue_gain?: number
  analogueGain?: number
  lens_position?: number
  lensPosition?: number
  colour_gains?: [number, number]
  colourGainRed?: number
  colourGainBlue?: number
  sharpness?: number
  brightness?: number
  contrast?: number
  saturation?: number
  [key: string]: unknown
}

export interface AfWindow {
  x: number
  y: number
  width: number
  height: number
  active?: boolean
  focusing?: boolean
}

export interface ZoomCenter {
  x: number
  y: number
}

export interface LastCapture {
  timestamp: number
  filename: string
  path: string
  latest_photo?: string
}

export interface PresetData {
  name: string
  display_name?: string
  description?: string
  settings: CameraSettings
  is_builtin?: boolean
  category?: 'built-in' | 'user'
  workflow?: 'photo' | 'liveview' | 'both'
}
