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
  af_state?: string
  lux?: number
  colour_temperature?: number
}

export interface ActionResult {
  success: boolean
  type?: 'success' | 'error' | 'warning'
  title?: string
  message?: string
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
}

export interface PresetData {
  name: string
  description?: string
  settings: CameraSettings
  is_builtin?: boolean
}
