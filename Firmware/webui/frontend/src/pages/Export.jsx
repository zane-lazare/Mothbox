import { useState } from 'react';
import {
  useExportJobs,
  useCreateExportJob,
  useCancelExportJob,
} from '../hooks/useExportJobs';
import useExportPreview from '../hooks/useExportPreview';
import FormatSelector from '../components/export/FormatSelector';
import PresetDropdown from '../components/export/PresetDropdown';
import FilterPanel from '../components/export/FilterPanel';
import DeploymentSelector from '../components/export/DeploymentSelector';
import DeploymentEditor from '../components/export/DeploymentEditor';
import FormatOptionsPanel from '../components/export/FormatOptionsPanel';
import FieldSelector from '../components/export/FieldSelector';
import ExportPreview from '../components/export/ExportPreview';
import ExportJobProgress from '../components/export/ExportJobProgress';
import ExportJobList from '../components/export/ExportJobList';
import { ArrowDownTrayIcon } from '@heroicons/react/24/outline';

const Export = () => {
  // Form state
  const [selectedFormat, setSelectedFormat] = useState('');
  const [filter, setFilter] = useState({});
  const [options, setOptions] = useState({});
  const [selectedFields, setSelectedFields] = useState({});
  const [deployment, setDeployment] = useState(null);

  // Export jobs
  const { data: jobsData } = useExportJobs();
  const jobs = jobsData?.jobs || [];

  // Mutations
  const createJobMutation = useCreateExportJob();
  const cancelJobMutation = useCancelExportJob();

  // Find current running/pending job
  const currentJob = jobs.find(
    (job) => job.status === 'running' || job.status === 'pending'
  );

  // Get photo count from preview
  const { data: previewData } = useExportPreview({
    format: selectedFormat,
    filter,
    selectedFields: selectedFields[selectedFormat] || [],
  });

  const photoCount = previewData?.metadata?.total_photos || 0;

  // Handle preset selection
  const handlePresetSelect = (preset) => {
    if (preset) {
      setSelectedFormat(preset.format || '');
      setFilter(preset.filter || {});
      setOptions(preset.options || {});

      // Initialize selected fields for this format if provided
      if (preset.selected_fields) {
        setSelectedFields({
          ...selectedFields,
          [preset.format]: preset.selected_fields,
        });
      }
    }
  };

  // Handle format change
  const handleFormatChange = (format) => {
    setSelectedFormat(format);

    // Reset options when format changes
    setOptions({});
  };

  // Handle filter change
  const handleFilterChange = (newFilter) => {
    setFilter(newFilter);
  };

  // Handle options change
  const handleOptionsChange = (newOptions) => {
    setOptions(newOptions);
  };

  // Handle field selection change
  const handleFieldsChange = (fields) => {
    setSelectedFields({
      ...selectedFields,
      [selectedFormat]: fields,
    });
  };

  // Handle deployment change
  const handleDeploymentChange = (newDeployment) => {
    setDeployment(newDeployment);
  };

  // Handle export submission
  const handleStartExport = () => {
    const jobRequest = {
      format: selectedFormat,
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
    if (deployment) {
      jobRequest.deployment = deployment;
    }

    createJobMutation.mutate(jobRequest);
  };

  // Handle job cancel
  const handleCancelJob = (jobId) => {
    cancelJobMutation.mutate(jobId);
  };

  // Handle job retry
  const handleRetryJob = () => {
    handleStartExport();
  };

  // Check if export button should be enabled
  const isExportEnabled = selectedFormat && photoCount > 0;

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
              selectedFormat={selectedFormat}
              onFormatChange={handleFormatChange}
            />
          </div>

          {/* Preset Selection */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Start</h2>
            <PresetDropdown onPresetSelect={handlePresetSelect} />
          </div>

          {/* Photo Filters */}
          <FilterPanel
            filter={filter}
            onChange={handleFilterChange}
            photoCount={photoCount}
          />

          {/* Deployment Info */}
          <div className="space-y-4">
            <DeploymentSelector
              selectedDeployment={deployment}
              onDeploymentChange={handleDeploymentChange}
            />
            {deployment && (
              <DeploymentEditor
                deployment={deployment}
                onUpdate={handleDeploymentChange}
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
              selectedFields={selectedFields[selectedFormat] || []}
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
              deployment={deployment}
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
