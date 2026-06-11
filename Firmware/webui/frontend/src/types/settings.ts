// Type definitions for Settings page and components

export interface ControlSettings {
  [key: string]: string
}

export interface CameraSettings {
  // Focus Strategy
  AutoCalibration?: string
  AutoCalibrationPeriod?: string
  LensPosition?: string
  AfMode?: string
  AfRange?: string
  AfSpeed?: string

  // Exposure
  AeEnable?: string | boolean
  ExposureTime?: string | number
  AnalogueGain?: string | number
  ExposureValue?: string | number

  // HDR Bracketing
  HDR?: string
  HDR_width?: string

  // Focus Bracketing
  FocusBracket?: string
  FocusBracket_Start?: string
  FocusBracket_End?: string
  FocusBracket_SettleDelay?: string
  FocusBracket_LockColorGains?: string
  FocusBracket_ColorGainRed?: string
  FocusBracket_ColorGainBlue?: string
  FlashDelay_BeforeCapture?: string
  FlashDelay_AfterCapture?: string

  // Image Format
  ImageFileType?: string
  VerticalFlip?: string | number

  // Other settings
  [key: string]: string | number | boolean | undefined
}

export interface WebuiSettings {
  // Resolution & Encoding
  stream_width?: number
  stream_height?: number
  frame_rate?: number
  jpeg_quality?: number
  stream_mode?: string
  sensor_mode?: string

  // Image Quality
  sharpness?: number
  brightness?: number
  contrast?: number
  saturation?: number
  noise_reduction_mode?: number

  // Focus
  af_mode?: number
  af_speed?: number
  af_range?: number

  // Exposure
  ae_enable?: boolean
  ae_metering_mode?: number

  // White Balance
  awb_enable?: boolean
  awb_mode?: number
  colour_gains_red?: number
  colour_gains_blue?: number

  // ISP Features
  use_custom_tuning?: boolean

  // Focus Peaking
  focus_peaking_enabled?: boolean
  focus_peaking_intensity?: number
  focus_peaking_color?: string
  focus_peaking_algorithm?: string

  [key: string]: string | number | boolean | undefined
}

export interface SystemInfo {
  installation_type?: string
  firmware_version?: string
  mothbox_home?: string
  config_dir?: string
  firmware_dir?: string
  gpio_source?: string
  gpio_pins?: {
    Relay_Ch1?: number
    Relay_Ch2?: number
    Relay_Ch3?: number
  }
}

export interface DiagnosticInfo {
  paths?: Record<string, string | boolean>
  controls_content?: {
    raw_lines?: number
    parsed_keys?: string[]
    has_gpio_pins?: boolean
    sample_values?: Record<string, string>
  }
  hardware_config?: Record<string, boolean | string | number>
}

export interface Preset {
  name: string
  display_name: string
  description: string
  workflow: 'photo' | 'liveview' | 'video' | 'both'
  category: 'built-in' | 'user'
  settings: {
    camera?: CameraSettings
    liveview?: WebuiSettings
  }
}

export interface PresetsData {
  presets: Preset[]
}

export interface Preferences {
  default_capture_preset?: string
  default_liveview_preset?: string
  default_preview_preset?: string
}

export type TabId = 'system' | 'controls' | 'camera' | 'diagnostic' | 'stream'

export interface CollapsedCardsState {
  // System Info
  systemInstallation: boolean
  systemGPIO: boolean

  // Diagnostic
  diagnosticPaths: boolean
  diagnosticControls: boolean
  diagnosticHardware: boolean

  // Camera Settings
  cameraPreset: boolean
  cameraFocusStrategy: boolean
  cameraExposure: boolean
  cameraHDR: boolean
  cameraFocusBracket: boolean
  cameraFormat: boolean
  cameraAdvanced: boolean

  // Live View Settings
  streamResolution: boolean
  streamImageQuality: boolean
  streamFocus: boolean
  streamExposure: boolean
  streamWhiteBalance: boolean
  streamISP: boolean
  streamFocusPeaking: boolean
}

export interface ResolutionPreset {
  label: string
  width: number
  height: number
}
