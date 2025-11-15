import { useState } from 'react'
import PropTypes from 'prop-types'
import * as Tabs from '@radix-ui/react-tabs'
import usePhotoMetadata from '../../hooks/usePhotoMetadata'
import CameraTab from './CameraTab'
import LocationTab from './LocationTab'
import CaptureTab from './CaptureTab'
import TagsTab from './TagsTab'
import DeploymentTab from './DeploymentTab'
import MetadataSkeleton from './MetadataSkeleton'

/**
 * MetadataPanel - Container component for photo metadata display
 *
 * Orchestrates all 5 metadata tabs (Camera, Location, Capture, Tags, Deployment)
 * using Radix UI Tabs for accessible tab navigation. Fetches metadata using the
 * usePhotoMetadata hook and handles loading/error states.
 *
 * Features:
 * - Responsive layout (vertical tabs on mobile, horizontal on desktop)
 * - Fast tab switching (<100ms requirement)
 * - Loading skeleton during data fetch
 * - Error handling with retry suggestions
 * - Full keyboard navigation support
 * - ARIA attributes for accessibility
 *
 * @param {string} photoPath - Full path to the photo file
 * @param {string} [className] - Optional additional CSS classes
 *
 * @example
 * <MetadataPanel photoPath="/var/lib/mothbox/photos/photo.jpg" />
 */
export default function MetadataPanel({ photoPath, className = '' }) {
  // State for active tab (defaults to 'camera')
  const [activeTab, setActiveTab] = useState('camera')

  // Fetch metadata using custom hook
  const { data: metadata, isLoading, isError, refetch } = usePhotoMetadata(photoPath)

  // Loading state - show skeleton
  if (isLoading) {
    return <MetadataSkeleton rows={6} className={className} />
  }

  // Error state - show error message with retry button
  if (isError) {
    return (
      <div className={`p-4 text-center ${className}`}>
        <p className="text-red-600 dark:text-red-400 font-semibold mb-2">
          Failed to load metadata
        </p>
        <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
          Please try again or check if the photo exists.
        </p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  // Success state - render tabs
  return (
    <Tabs.Root
      value={activeTab}
      onValueChange={setActiveTab}
      className={`flex flex-col md:flex-row ${className}`}
    >
      {/* Tab List - vertical on mobile, horizontal on desktop */}
      <Tabs.List
        aria-label="Photo metadata tabs"
        className="flex flex-row md:flex-col border-b md:border-b-0 md:border-r border-gray-200 dark:border-gray-700"
      >
        <Tabs.Trigger
          value="camera"
          className={`
            px-4 py-2 text-sm font-medium transition-all duration-75
            border-b-2 md:border-b-0 md:border-r-2 border-transparent
            hover:bg-gray-50 dark:hover:bg-gray-800
            data-[state=active]:border-blue-600 data-[state=active]:text-blue-600
            data-[state=active]:dark:border-blue-400 data-[state=active]:dark:text-blue-400
            text-gray-700 dark:text-gray-300
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          `}
        >
          Camera
        </Tabs.Trigger>
        <Tabs.Trigger
          value="location"
          className={`
            px-4 py-2 text-sm font-medium transition-all duration-75
            border-b-2 md:border-b-0 md:border-r-2 border-transparent
            hover:bg-gray-50 dark:hover:bg-gray-800
            data-[state=active]:border-blue-600 data-[state=active]:text-blue-600
            data-[state=active]:dark:border-blue-400 data-[state=active]:dark:text-blue-400
            text-gray-700 dark:text-gray-300
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          `}
        >
          Location
        </Tabs.Trigger>
        <Tabs.Trigger
          value="capture"
          className={`
            px-4 py-2 text-sm font-medium transition-all duration-75
            border-b-2 md:border-b-0 md:border-r-2 border-transparent
            hover:bg-gray-50 dark:hover:bg-gray-800
            data-[state=active]:border-blue-600 data-[state=active]:text-blue-600
            data-[state=active]:dark:border-blue-400 data-[state=active]:dark:text-blue-400
            text-gray-700 dark:text-gray-300
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          `}
        >
          Capture
        </Tabs.Trigger>
        <Tabs.Trigger
          value="tags"
          className={`
            px-4 py-2 text-sm font-medium transition-all duration-75
            border-b-2 md:border-b-0 md:border-r-2 border-transparent
            hover:bg-gray-50 dark:hover:bg-gray-800
            data-[state=active]:border-blue-600 data-[state=active]:text-blue-600
            data-[state=active]:dark:border-blue-400 data-[state=active]:dark:text-blue-400
            text-gray-700 dark:text-gray-300
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          `}
        >
          Tags
        </Tabs.Trigger>
        <Tabs.Trigger
          value="deployment"
          className={`
            px-4 py-2 text-sm font-medium transition-all duration-75
            border-b-2 md:border-b-0 md:border-r-2 border-transparent
            hover:bg-gray-50 dark:hover:bg-gray-800
            data-[state=active]:border-blue-600 data-[state=active]:text-blue-600
            data-[state=active]:dark:border-blue-400 data-[state=active]:dark:text-blue-400
            text-gray-700 dark:text-gray-300
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          `}
        >
          Deployment
        </Tabs.Trigger>
      </Tabs.List>

      {/* Tab Content - scrollable area for metadata */}
      <div className="flex-1 overflow-y-auto max-h-[500px]">
        <Tabs.Content value="camera" className="p-4">
          <CameraTab data={metadata?.camera} />
        </Tabs.Content>

        <Tabs.Content value="location" className="p-4">
          <LocationTab data={metadata?.location} />
        </Tabs.Content>

        <Tabs.Content value="capture" className="p-4">
          <CaptureTab data={metadata?.capture} />
        </Tabs.Content>

        <Tabs.Content value="tags" className="p-4">
          <TagsTab data={metadata?.tags} />
        </Tabs.Content>

        <Tabs.Content value="deployment" className="p-4">
          <DeploymentTab data={metadata?.deployment} />
        </Tabs.Content>
      </div>
    </Tabs.Root>
  )
}

MetadataPanel.propTypes = {
  photoPath: PropTypes.string,
  className: PropTypes.string,
}
