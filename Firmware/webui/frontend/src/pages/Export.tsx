import { useState, useEffect } from 'react';
import {
  useExportJobs,
  useCreateExportJob,
  useCancelExportJob,
} from '../hooks/useExportJobs';
import { useExportPresets, useExportPreset } from '../hooks/useExportPresets';
import { useDeployment } from '../hooks/useDeployments';
import useExportPreview from '../hooks/useExportPreview';
import FormatSelector from '../components/export/FormatSelector';
import PresetDropdown from '../components/export/PresetDropdown';
import FilterPanel from '../components/export/FilterPanel';
import type { PhotoFilter } from '../components/export/FilterPanel';
import DeploymentSelector from '../components/export/DeploymentSelector';
import DeploymentEditor from '../components/export/DeploymentEditor';
import FormatOptionsPanel from '../components/export/FormatOptionsPanel';
import FieldSelector from '../components/export/FieldSelector';
import ExportPreview from '../components/export/ExportPreview';
import ExportJobProgress from '../components/export/ExportJobProgress';
import ExportJobList from '../components/export/ExportJobList';
import { ArrowDownTrayIcon } from '@heroicons/react/24/outline';
import type { ExportJob } from '../types';

// Export format types
type ExportFormat = 'darwin_core' | 'inaturalist' | 'json' | 'csv';

// Format options types
interface FormatOptions {
  include_raw_exif?: boolean;
  compression_level?: number;
  include_photos?: boolean;
  include_metadata?: boolean;
  schema_version?: string;
  [key: string]: unknown;
}

// Selected fields mapping (format -> field array)
interface SelectedFieldsMap {
  [format: string]: string[];
}

// Preset types (from hooks)
interface PresetData {
  format?: ExportFormat;
  export_format?: ExportFormat;
  filter?: PhotoFilter;
  options?: FormatOptions;
  selected_fields?: string[];
}

const Export = () => {
  // Form state
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat | ''>('');
  const [filter, setFilter] = useState<PhotoFilter>({});
  const [options, setOptions] = useState<FormatOptions>({});
  const [selectedFields, setSelectedFields] = useState<SelectedFieldsMap>({});
  const [selectedDeploymentDir, setSelectedDeploymentDir] = useState<string | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  // TODO: Implement SavePresetModal component to use this state
  const [showDeploymentEditor, setShowDeploymentEditor] = useState<boolean>(false);

  // Export jobs
  const { data: jobsData } = useExportJobs();
  const jobs: ExportJob[] = jobsData?.jobs || [];

  // Export presets
  const { data: presetsData } = useExportPresets();
  const presets = presetsData?.presets || [];
  const { data: presetDetails } = useExportPreset(selectedPreset);

  // Deployment data (fetched when directory is selected)
  const { data: deploymentData } = useDeployment(selectedDeploymentDir);

  // Mutations
  const createJobMutation = useCreateExportJob();
  const cancelJobMutation = useCancelExportJob();

  // Find current running/pending job
  const currentJob = jobs.find(
    (job: ExportJob) => job.status === 'running' || job.status === 'pending'
  );

  // Get photo count from preview
  const { data: previewData } = useExportPreview({
    format: selectedFormat as 'json' | 'csv' | 'darwin_core' | 'inaturalist',
    filter,
    selectedFields: selectedFields[selectedFormat] || [],
  });

  const photoCount = previewData?.metadata?.total_photos || 0;

  // Handle preset selection (applies preset data to form)
  const handlePresetSelect = (preset: PresetData) => {
    if (preset) {
      setSelectedFormat(preset.format || preset.export_format || '');
      setFilter(preset.filter || {});
      setOptions(preset.options || {});

      // Initialize selected fields for this format if provided
      if (preset.selected_fields) {
        setSelectedFields({
          ...selectedFields,
          [preset.format || preset.export_format || '']: preset.selected_fields,
        });
      }
    }
  };

  // Handle preset dropdown change
  const handlePresetChange = (presetName: string | null) => {
    setSelectedPreset(presetName);
  };

  // Apply preset when details load
  useEffect(() => {
    if (presetDetails) {
      handlePresetSelect(presetDetails);
    }
  }, [presetDetails]); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle save preset modal
  const handleSavePreset = () => {
    setShowSavePresetModal(true);
  };

  // Handle format change
  const handleFormatChange = (format: ExportFormat) => {
    setSelectedFormat(format);

    // Reset options when format changes
    setOptions({});
  };

  // Handle filter change
  const handleFilterChange = (newFilter: PhotoFilter) => {
    setFilter(newFilter);
  };

  // Handle options change
  const handleOptionsChange = (newOptions: FormatOptions) => {
    setOptions(newOptions);
  };

  // Handle field selection change
  const handleFieldsChange = (format: ExportFormat, fields: string[]) => {
    setSelectedFields({
      ...selectedFields,
      [format]: fields,
    });
  };

  // Handle deployment save (from editor)
  const handleDeploymentSave = (savedDeployment: { directory: string }) => {
    setSelectedDeploymentDir(savedDeployment.directory);
    setShowDeploymentEditor(false);
  };

  // Handle export submission
  const handleStartExport = () => {
    const jobRequest: {
      format: ExportFormat;
      filter: PhotoFilter;
      options: FormatOptions;
      selected_fields?: string[];
      deployment?: string;
    } = {
      format: selectedFormat as ExportFormat,
      filter,
      options,
    };

    // Add selected fields if using custom format (JSON/CSV)
    if (selectedFormat === 'json' || selectedFormat === 'csv') {
      if (selectedFields[selectedFormat]?.length > 0) {
        jobRequest.selected_fields = selectedFields[selectedFormat];
      }
    }

    // Add deployment if selected
    if (selectedDeploymentDir) {
      jobRequest.deployment = selectedDeploymentDir;
    }

    createJobMutation.mutate(jobRequest);
  };

  // Handle job cancel
  const handleCancelJob = (jobId: string) => {
    cancelJobMutation.mutate(jobId);
  };

  // Handle job retry
  const handleRetryJob = () => {
    handleStartExport();
  };

  // Check if export button should be enabled
  const isExportEnabled = selectedFormat && photoCount > 0 && !currentJob;

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Export Photos</h1>

      {/* Main Layout - Two Column on Desktop */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8">
        {/* Left Column - Form (~40%) */}
        <div className="md:col-span-2 space-y-6">
          {/* Format Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Export Format</h2>
            <FormatSelector
              value={selectedFormat}
              onChange={handleFormatChange}
            />
          </div>

          {/* Preset Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Start</h2>
            <PresetDropdown
              value={selectedPreset}
              onChange={handlePresetChange}
              presets={presets}
              onSavePreset={handleSavePreset}
            />
          </div>

          {/* Photo Filters */}
          <FilterPanel
            filter={filter}
            onChange={handleFilterChange}
            photoCount={photoCount}
          />

          {/* Deployment Info */}
          <div className="bg-white rounded-lg shadow p-6 space-y-4">
            <h2 className="text-lg font-medium text-gray-900 mb-2">
              Deployment <span className="text-sm font-normal text-gray-500">(Optional)</span>
            </h2>

            <DeploymentSelector
              value={selectedDeploymentDir}
              onChange={setSelectedDeploymentDir}
              onCreateNew={() => setShowDeploymentEditor(true)}
              onEdit={() => setShowDeploymentEditor(true)}
              disabled={currentJob !== undefined}
              allowNone={true}
              noneLabel="None - use photo EXIF data"
            />

            {!selectedDeploymentDir && photoCount > 0 && (
              <div className="text-sm text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-3">
                <p className="font-medium">Using photo EXIF data</p>
                <p className="mt-1 text-xs">
                  GPS coordinates will be extracted from individual photo metadata.
                  {previewData?.metadata && 'photos_with_gps' in previewData.metadata && (
                    <span className="block mt-1">
                      GPS coverage: {(previewData.metadata as { photos_with_gps: number }).photos_with_gps} of {photoCount} photos ({Math.round(((previewData.metadata as { photos_with_gps: number }).photos_with_gps / photoCount) * 100)}%)
                    </span>
                  )}
                </p>
              </div>
            )}

            {showDeploymentEditor && (
              <DeploymentEditor
                deployment={deploymentData}
                directory={selectedDeploymentDir || filter?.deployment || ''}
                filter={filter}
                onSave={handleDeploymentSave}
                onCancel={() => setShowDeploymentEditor(false)}
              />
            )}
          </div>

          {/* Format Options */}
          {selectedFormat && (
            <FormatOptionsPanel
              format={selectedFormat}
              options={options}
              onChange={handleOptionsChange}
            />
          )}

          {/* Field Selection (for JSON/CSV) */}
          {(selectedFormat === 'json' || selectedFormat === 'csv') && (
            <FieldSelector
              format={selectedFormat}
              selectedFields={selectedFields}
              onChange={handleFieldsChange}
            />
          )}

          {/* Start Export Button */}
          <div className="bg-white rounded-lg shadow p-6">
            <button
              onClick={handleStartExport}
              disabled={!isExportEnabled || createJobMutation.isPending}
              className={`w-full flex items-center justify-center px-6 py-3 text-base font-medium rounded-md ${
                isExportEnabled && !createJobMutation.isPending
                  ? 'text-white bg-blue-600 hover:bg-blue-700'
                  : 'text-gray-400 bg-gray-100 cursor-not-allowed'
              }`}
            >
              <ArrowDownTrayIcon className="w-5 h-5 mr-2" />
              {createJobMutation.isPending
                ? 'Creating Export...'
                : `Start Export (${photoCount} ${photoCount === 1 ? 'photo' : 'photos'})`}
            </button>
            {!selectedFormat && (
              <p className="mt-2 text-sm text-gray-500 text-center">
                Select a format to continue
              </p>
            )}
            {selectedFormat && photoCount === 0 && (
              <p className="mt-2 text-sm text-yellow-600 text-center">
                No photos match the current filters
              </p>
            )}
            {currentJob && (
              <p className="mt-2 text-sm text-blue-600 text-center">
                Export in progress - wait for it to complete
              </p>
            )}
          </div>
        </div>

        {/* Right Column - Preview (~60%) */}
        <div className="md:col-span-3">
          <div className="bg-white rounded-lg shadow p-6 sticky top-4">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Preview</h2>
            <ExportPreview
              format={selectedFormat}
              filter={filter}
              options={options}
              deployment={deploymentData}
              selectedFields={selectedFields[selectedFormat] || []}
            />
          </div>
        </div>
      </div>

      {/* Current Job Progress */}
      {currentJob && (
        <ExportJobProgress
          job={currentJob}
          onCancel={handleCancelJob}
          onRetry={handleRetryJob}
        />
      )}

      {/* Job History */}
      <ExportJobList />
    </div>
  );
};

export default Export;
