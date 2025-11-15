import React from 'react';
import PropTypes from 'prop-types';

/**
 * LoadingSpinner - Simple loading spinner component
 *
 * @param {string} size - Size of the spinner ('sm', 'md', 'lg')
 * @param {string} className - Additional CSS classes
 */
const LoadingSpinner = ({ size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4'
  };

  return (
    <div className={`flex justify-center items-center ${className}`}>
      <div
        className={`
          ${sizeClasses[size]}
          border-blue-500
          border-t-transparent
          rounded-full
          animate-spin
        `}
        role="status"
        aria-label="Loading"
      >
        <span className="sr-only">Loading...</span>
      </div>
    </div>
  );
};

LoadingSpinner.propTypes = {
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  className: PropTypes.string
};

export default LoadingSpinner;
