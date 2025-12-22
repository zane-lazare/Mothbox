import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { ACTION_LIMITS, ACTION_NAMES } from './constants';

const ActionForm = ({ action, onSave, onCancel, isOpen }) => {
  const [formData, setFormData] = useState({
    action_type: '',
    action_name: '',
    offset_minutes: '',
    description: '',
    parameters: [],
  });
  const [errors, setErrors] = useState({});

  // Initialize form data when action prop changes or modal opens
  useEffect(() => {
    if (isOpen) {
      if (action) {
        // Edit mode - populate from action
        setFormData({
          action_type: action.action_type || '',
          action_name: action.action_name || '',
          offset_minutes: action.offset_minutes ?? '',
          description: action.description || '',
          parameters: action.parameters
            ? Object.entries(action.parameters).map(([key, value]) => ({ key, value }))
            : [],
        });
      } else {
        // Create mode - reset to empty
        setFormData({
          action_type: '',
          action_name: '',
          offset_minutes: '',
          description: '',
          parameters: [],
        });
      }
      setErrors({});
    }
  }, [action, isOpen]);

  // Handle Escape key to close modal
  useEffect(() => {
    if (!isOpen) return;
    const handleEscape = (e) => {
      if (e.key === 'Escape') onCancel();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onCancel]);

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));

    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleActionTypeChange = (value) => {
    setFormData(prev => ({
      ...prev,
      action_type: value,
      action_name: '', // Reset action name when type changes
    }));

    if (errors.action_type) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors.action_type;
        return newErrors;
      });
    }
  };

  const handleDescriptionChange = (value) => {
    // Enforce character limit
    const truncated = value.slice(0, ACTION_LIMITS.DESCRIPTION_MAX_LENGTH);
    setFormData(prev => ({
      ...prev,
      description: truncated,
    }));
  };

  const handleAddParameter = () => {
    setFormData(prev => ({
      ...prev,
      parameters: [...prev.parameters, { key: '', value: '' }],
    }));
  };

  const handleRemoveParameter = (index) => {
    setFormData(prev => ({
      ...prev,
      parameters: prev.parameters.filter((_, i) => i !== index),
    }));
  };

  const handleParameterChange = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      parameters: prev.parameters.map((param, i) =>
        i === index ? { ...param, [field]: value } : param
      ),
    }));
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.action_type) {
      newErrors.action_type = 'Action type is required';
    }

    if (!formData.action_name) {
      newErrors.action_name = 'Action name is required';
    }

    if (formData.offset_minutes === '' || formData.offset_minutes === null) {
      newErrors.offset_minutes = 'Offset is required';
    } else {
      const offset = Number(formData.offset_minutes);
      if (offset < ACTION_LIMITS.MIN_OFFSET_MINUTES || offset > ACTION_LIMITS.MAX_OFFSET_MINUTES) {
        newErrors.offset_minutes = `Offset must be between ${ACTION_LIMITS.MIN_OFFSET_MINUTES} and ${ACTION_LIMITS.MAX_OFFSET_MINUTES} minutes`;
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (!validate()) {
      return;
    }

    // Convert parameters array to object, excluding empty rows
    // Warn about duplicate keys (last value wins)
    const parametersObj = formData.parameters.reduce((acc, param) => {
      if (param.key && param.value) {
        if (acc[param.key]) {
          console.warn(`Duplicate parameter key: ${param.key}`);
        }
        acc[param.key] = param.value;
      }
      return acc;
    }, {});

    const actionData = {
      action_type: formData.action_type,
      action_name: formData.action_name,
      offset_minutes: Number(formData.offset_minutes),
      description: formData.description || undefined,
      parameters: parametersObj,
    };

    onSave(actionData);
  };

  if (!isOpen) {
    return null;
  }

  const availableActionNames = formData.action_type
    ? ACTION_NAMES[formData.action_type] || []
    : [];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="action-form-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
    >
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4">
        <div className="p-6">
          <h2 id="action-form-title" className="text-2xl font-bold mb-6 text-gray-900 dark:text-white">
            {action ? 'Edit Action' : 'Create Action'}
          </h2>

          <div className="space-y-4">
            {/* Action Type */}
            <div>
              <label
                htmlFor="action_type"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Action Type
              </label>
              <select
                id="action_type"
                value={formData.action_type}
                onChange={(e) => handleActionTypeChange(e.target.value)}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select action type</option>
                <option value="gpio">GPIO</option>
                <option value="camera">Camera</option>
                <option value="gps_sync">GPS Sync</option>
                <option value="service">Service</option>
              </select>
              {errors.action_type && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.action_type}
                </p>
              )}
            </div>

            {/* Action Name */}
            <div>
              <label
                htmlFor="action_name"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Action Name
              </label>
              <select
                id="action_name"
                value={formData.action_name}
                onChange={(e) => handleInputChange('action_name', e.target.value)}
                disabled={!formData.action_type}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="">Select action name</option>
                {availableActionNames.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
              {errors.action_name && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.action_name}
                </p>
              )}
            </div>

            {/* Offset */}
            <div>
              <label
                htmlFor="offset_minutes"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Offset (minutes)
              </label>
              <input
                id="offset_minutes"
                type="number"
                min={ACTION_LIMITS.MIN_OFFSET_MINUTES}
                max={ACTION_LIMITS.MAX_OFFSET_MINUTES}
                value={formData.offset_minutes}
                onChange={(e) => handleInputChange('offset_minutes', e.target.value)}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder={`${ACTION_LIMITS.MIN_OFFSET_MINUTES}-${ACTION_LIMITS.MAX_OFFSET_MINUTES}`}
              />
              {errors.offset_minutes && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.offset_minutes}
                </p>
              )}
            </div>

            {/* Description */}
            <div>
              <label
                htmlFor="description"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Description (optional)
              </label>
              <textarea
                id="description"
                value={formData.description}
                onChange={(e) => handleDescriptionChange(e.target.value)}
                rows={3}
                maxLength={ACTION_LIMITS.DESCRIPTION_MAX_LENGTH}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600
                         bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Optional description"
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 text-right">
                {formData.description.length} / {ACTION_LIMITS.DESCRIPTION_MAX_LENGTH}
              </p>
            </div>

            {/* Parameters */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Parameters (optional)
                </label>
                <button
                  type="button"
                  onClick={handleAddParameter}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md
                           hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600
                           focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Add Parameter
                </button>
              </div>
              {formData.parameters.length > 0 && (
                <div className="space-y-2">
                  {formData.parameters.map((param, index) => (
                    <div key={index} className="flex gap-2">
                      <input
                        type="text"
                        value={param.key}
                        onChange={(e) =>
                          handleParameterChange(index, 'key', e.target.value)
                        }
                        placeholder="Key"
                        className="flex-1 rounded-md border border-gray-300 dark:border-gray-600
                                 bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                                 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <input
                        type="text"
                        value={param.value}
                        onChange={(e) =>
                          handleParameterChange(index, 'value', e.target.value)
                        }
                        placeholder="Value"
                        className="flex-1 rounded-md border border-gray-300 dark:border-gray-600
                                 bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white
                                 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <button
                        type="button"
                        onClick={() => handleRemoveParameter(index)}
                        className="px-3 py-2 text-sm bg-red-600 text-white rounded-md
                                 hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600
                                 focus:outline-none focus:ring-2 focus:ring-red-500"
                        aria-label="Remove"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Buttons */}
          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md
                       hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200
                       dark:hover:bg-gray-600 focus:outline-none focus:ring-2
                       focus:ring-gray-500"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-4 py-2 bg-blue-600 text-white rounded-md
                       hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

ActionForm.propTypes = {
  action: PropTypes.shape({
    action_type: PropTypes.string,
    action_name: PropTypes.string,
    offset_minutes: PropTypes.number,
    description: PropTypes.string,
    parameters: PropTypes.object
  }),
  onSave: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
  isOpen: PropTypes.bool.isRequired
};

export default ActionForm;
