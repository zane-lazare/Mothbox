import PropTypes from 'prop-types';
import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationCircleIcon,
  ArrowDownTrayIcon,
  XMarkIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

const ExportJobProgress = ({ job, onCancel, onRetry }) => {
  if (!job) return null;

  const getPhaseLabel = (phase) => {
    const labels = {
      initializing: 'Initializing',
      collecting: 'Collecting Photos',
      exporting: 'Exporting Data',
      finalizing: 'Finalizing Export',
      completed: 'Completed',
    };
    return labels[phase] || phase;
  };

  const handleDownload = () => {
    const downloadUrl = `/api/export/jobs/${job.id}/download`;
    window.open(downloadUrl, '_blank');
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel(job.id);
    }
  };

  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    }
  };

  // Pending state
  if (job.status === 'pending') {
    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
            <div>
              <h3 className="text-lg font-medium text-gray-900">Export Job Queued</h3>
              <p className="text-sm text-gray-500">Waiting to start...</p>
            </div>
          </div>
          <button
            onClick={handleCancel}
            disabled={!onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <XMarkIcon className="w-4 h-4 inline mr-1" />
            Cancel
          </button>
        </div>
      </div>
    );
  }

  // Running state
  if (job.status === 'running') {
    const { current = 0, total = 0, percent = 0, phase = 'exporting' } = job.progress || {};

    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-medium text-gray-900">Export in Progress</h3>
            <button
              onClick={handleCancel}
              disabled={!onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <XMarkIcon className="w-4 h-4 inline mr-1" />
              Cancel
            </button>
          </div>
          <p className="text-sm text-gray-500">
            {getPhaseLabel(phase)} - Processing {current} of {total} photos
          </p>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-gray-700">{percent}%</span>
          </div>
          <div
            className="w-full bg-gray-200 rounded-full h-4 overflow-hidden"
            role="progressbar"
            aria-valuenow={percent}
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <div
              className="bg-blue-600 h-4 rounded-full transition-all duration-300"
              style={{ width: `${percent}%` }}
            ></div>
          </div>
        </div>
      </div>
    );
  }

  // Completed state
  if (job.status === 'completed') {
    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <CheckCircleIcon className="w-6 h-6 text-green-500" />
            <div>
              <h3 className="text-lg font-medium text-gray-900">Export Completed</h3>
              <p className="text-sm text-gray-500">
                Your export is ready to download
              </p>
            </div>
          </div>
          <button
            onClick={handleDownload}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
          >
            <ArrowDownTrayIcon className="w-4 h-4 inline mr-1" />
            Download
          </button>
        </div>
      </div>
    );
  }

  // Failed state
  if (job.status === 'failed') {
    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <XCircleIcon className="w-6 h-6 text-red-500" />
            <div>
              <h3 className="text-lg font-medium text-gray-900">Export Failed</h3>
              <p className="text-sm text-red-600">{job.error || 'An error occurred during export'}</p>
            </div>
          </div>
          <button
            onClick={handleRetry}
            disabled={!onRetry}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowPathIcon className="w-4 h-4 inline mr-1" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Cancelled state
  if (job.status === 'cancelled') {
    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center space-x-3">
          <ExclamationCircleIcon className="w-6 h-6 text-yellow-500" />
          <div>
            <h3 className="text-lg font-medium text-gray-900">Export Cancelled</h3>
            <p className="text-sm text-gray-500">This export was cancelled</p>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

ExportJobProgress.propTypes = {
  job: PropTypes.shape({
    id: PropTypes.string.isRequired,
    status: PropTypes.oneOf(['pending', 'running', 'completed', 'failed', 'cancelled', 'expired']).isRequired,
    progress: PropTypes.shape({
      current: PropTypes.number,
      total: PropTypes.number,
      percent: PropTypes.number,
      phase: PropTypes.string,
    }),
    error: PropTypes.string,
    result: PropTypes.shape({
      file_path: PropTypes.string,
    }),
  }),
  onCancel: PropTypes.func,
  onRetry: PropTypes.func,
};

export default ExportJobProgress;
