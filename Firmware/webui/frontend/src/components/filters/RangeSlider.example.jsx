/**
 * RangeSlider Usage Examples
 *
 * This file demonstrates various use cases for the RangeSlider component.
 * These examples can be used in Storybook or as reference for implementation.
 */

import { useState } from 'react';
import RangeSlider from './RangeSlider';

// Basic Usage
export function BasicExample() {
  const [value, setValue] = useState({ min: 25, max: 75 });

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold mb-2">Basic Range Slider</h3>
      <RangeSlider
        min={0}
        max={100}
        value={value}
        onChange={setValue}
        label="Basic Range"
      />
      <p className="mt-2 text-sm text-gray-600">
        Selected: {value.min} - {value.max}
      </p>
    </div>
  );
}

// ISO Range with Custom Formatting
export function ISOExample() {
  const [isoRange, setIsoRange] = useState({ min: 100, max: 1600 });

  const formatISO = (val) => `ISO ${val}`;

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold mb-2">ISO Range Filter</h3>
      <RangeSlider
        min={100}
        max={6400}
        value={isoRange}
        onChange={setIsoRange}
        step={100}
        label="ISO"
        formatValue={formatISO}
      />
      <p className="mt-2 text-sm text-gray-600">
        Selected: {formatISO(isoRange.min)} - {formatISO(isoRange.max)}
      </p>
    </div>
  );
}

// Exposure Time with Fractional Steps
export function ExposureExample() {
  const [exposure, setExposure] = useState({ min: 0.5, max: 5.0 });

  const formatExposure = (val) => `${val.toFixed(1)}s`;

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold mb-2">Exposure Time Filter</h3>
      <RangeSlider
        min={0}
        max={10}
        value={exposure}
        onChange={setExposure}
        step={0.1}
        label="Exposure Time"
        formatValue={formatExposure}
      />
      <p className="mt-2 text-sm text-gray-600">
        Selected: {formatExposure(exposure.min)} - {formatExposure(exposure.max)}
      </p>
    </div>
  );
}

// Focal Length Range
export function FocalLengthExample() {
  const [focalLength, setFocalLength] = useState({ min: 24, max: 200 });

  const formatFocalLength = (val) => `${val}mm`;

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold mb-2">Focal Length Filter</h3>
      <RangeSlider
        min={10}
        max={600}
        value={focalLength}
        onChange={setFocalLength}
        step={1}
        label="Focal Length"
        formatValue={formatFocalLength}
      />
      <p className="mt-2 text-sm text-gray-600">
        Selected: {formatFocalLength(focalLength.min)} - {formatFocalLength(focalLength.max)}
      </p>
    </div>
  );
}

// Without Input Fields
export function NoInputsExample() {
  const [value, setValue] = useState({ min: 30, max: 70 });

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold mb-2">Slider Only (No Inputs)</h3>
      <RangeSlider
        min={0}
        max={100}
        value={value}
        onChange={setValue}
        label="Value Range"
        showInputs={false}
      />
      <p className="mt-2 text-sm text-gray-600">
        Selected: {value.min} - {value.max}
      </p>
    </div>
  );
}

// Disabled State
export function DisabledExample() {
  const [value] = useState({ min: 40, max: 60 });

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold mb-2">Disabled Slider</h3>
      <RangeSlider
        min={0}
        max={100}
        value={value}
        onChange={() => {}}
        label="Disabled Range"
        disabled
      />
      <p className="mt-2 text-sm text-gray-600">
        This slider is disabled and cannot be interacted with.
      </p>
    </div>
  );
}

// Large Step Size
export function LargeStepExample() {
  const [value, setValue] = useState({ min: 25, max: 75 });

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold mb-2">Large Step Size (25)</h3>
      <RangeSlider
        min={0}
        max={100}
        value={value}
        onChange={setValue}
        step={25}
        label="Increments"
      />
      <p className="mt-2 text-sm text-gray-600">
        Values snap to multiples of 25: {value.min} - {value.max}
      </p>
    </div>
  );
}

// Complete Gallery Filter Example
export function GalleryFilterExample() {
  const [isoRange, setIsoRange] = useState({ min: 100, max: 3200 });
  const [exposureRange, setExposureRange] = useState({ min: 0.1, max: 2.0 });
  const [apertureRange, setApertureRange] = useState({ min: 2.8, max: 11 });

  return (
    <div className="p-4 space-y-6 max-w-md">
      <h3 className="text-xl font-bold mb-4">Camera Settings Filter</h3>

      <div>
        <label className="block text-sm font-medium mb-1">ISO Range</label>
        <RangeSlider
          min={100}
          max={6400}
          value={isoRange}
          onChange={setIsoRange}
          step={100}
          label="ISO"
          formatValue={(val) => `ISO ${val}`}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Exposure Time (seconds)</label>
        <RangeSlider
          min={0}
          max={10}
          value={exposureRange}
          onChange={setExposureRange}
          step={0.1}
          label="Exposure Time"
          formatValue={(val) => `${val.toFixed(1)}s`}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Aperture (f-stop)</label>
        <RangeSlider
          min={1.4}
          max={22}
          value={apertureRange}
          onChange={setApertureRange}
          step={0.1}
          label="Aperture"
          formatValue={(val) => `f/${val.toFixed(1)}`}
        />
      </div>

      <div className="mt-4 p-3 bg-gray-100 dark:bg-gray-800 rounded">
        <h4 className="font-medium mb-2">Selected Filters:</h4>
        <ul className="text-sm space-y-1">
          <li>ISO: {isoRange.min} - {isoRange.max}</li>
          <li>Exposure: {exposureRange.min.toFixed(1)}s - {exposureRange.max.toFixed(1)}s</li>
          <li>Aperture: f/{apertureRange.min.toFixed(1)} - f/{apertureRange.max.toFixed(1)}</li>
        </ul>
      </div>
    </div>
  );
}
