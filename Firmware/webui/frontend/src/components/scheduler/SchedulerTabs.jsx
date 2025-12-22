import PropTypes from 'prop-types'

const SchedulerTabs = ({ activeTab, onTabChange }) => {
  return (
    <div className="border-b border-gray-200">
      <nav className="-mb-px flex space-x-6" role="tablist">
        <button
          role="tab"
          aria-selected={activeTab === 'schedules'}
          onClick={() => onTabChange('schedules')}
          className={`py-2 px-1 border-b-2 font-medium text-sm ${
            activeTab === 'schedules'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          Schedules
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'calendar'}
          onClick={() => onTabChange('calendar')}
          className={`py-2 px-1 border-b-2 font-medium text-sm ${
            activeTab === 'calendar'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          Calendar
        </button>
      </nav>
    </div>
  )
}

SchedulerTabs.propTypes = {
  activeTab: PropTypes.oneOf(['schedules', 'calendar']).isRequired,
  onTabChange: PropTypes.func.isRequired,
}

export default SchedulerTabs
