import { BrowserRouter as Router, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import 'leaflet/dist/leaflet.css'
import ErrorBoundary from './components/ErrorBoundary'
import Dashboard from './pages/Dashboard'
import Gallery from './pages/Gallery'
import MapPage from './pages/MapPage'
import Settings from './pages/Settings'
import Camera from './pages/Camera'
import GPIO from './pages/GPIO'
import Scheduler from './pages/Scheduler'
import { FilterProvider } from './contexts/FilterContext'

const queryClient = new QueryClient()

// Layout wrapper component that conditionally applies standard layout
function AppLayout() {
  const location = useLocation()

  // Full-screen pages that bypass standard layout
  const isFullScreenPage = location.pathname === '/gallery/map'

  if (isFullScreenPage) {
    return (
      <Routes>
        <Route path="/gallery/map" element={<MapPage />} />
      </Routes>
    )
  }

  // Standard layout with navigation and padding
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Navigation */}
      <nav className="bg-white shadow-lg">
        <div className="px-4">
          <div className="flex justify-between h-16">
            <div className="flex space-x-8">
              <div className="flex items-center">
                <h1 className="text-xl font-bold text-gray-800">Mothbox</h1>
              </div>
              <div className="flex space-x-4">
                <NavLink
                  to="/"
                  className={({ isActive }) =>
                    `inline-flex items-center px-3 py-2 text-sm font-medium ${
                      isActive
                        ? 'text-blue-600 border-b-2 border-blue-600'
                        : 'text-gray-600 hover:text-gray-900'
                    }`
                  }
                >
                  Dashboard
                </NavLink>
                <NavLink
                  to="/gallery"
                  className={({ isActive }) =>
                    `inline-flex items-center px-3 py-2 text-sm font-medium ${
                      isActive
                        ? 'text-blue-600 border-b-2 border-blue-600'
                        : 'text-gray-600 hover:text-gray-900'
                    }`
                  }
                >
                  Gallery
                </NavLink>
                <NavLink
                  to="/camera"
                  className={({ isActive }) =>
                    `inline-flex items-center px-3 py-2 text-sm font-medium ${
                      isActive
                        ? 'text-blue-600 border-b-2 border-blue-600'
                        : 'text-gray-600 hover:text-gray-900'
                    }`
                  }
                >
                  Camera
                </NavLink>
                <NavLink
                  to="/gpio"
                  className={({ isActive }) =>
                    `inline-flex items-center px-3 py-2 text-sm font-medium ${
                      isActive
                        ? 'text-blue-600 border-b-2 border-blue-600'
                        : 'text-gray-600 hover:text-gray-900'
                    }`
                  }
                >
                  GPIO
                </NavLink>
                <NavLink
                  to="/scheduler"
                  className={({ isActive }) =>
                    `inline-flex items-center px-3 py-2 text-sm font-medium ${
                      isActive
                        ? 'text-blue-600 border-b-2 border-blue-600'
                        : 'text-gray-600 hover:text-gray-900'
                    }`
                  }
                >
                  Scheduler
                </NavLink>
                <NavLink
                  to="/settings"
                  className={({ isActive }) =>
                    `inline-flex items-center px-3 py-2 text-sm font-medium ${
                      isActive
                        ? 'text-blue-600 border-b-2 border-blue-600'
                        : 'text-gray-600 hover:text-gray-900'
                    }`
                  }
                >
                  Settings
                </NavLink>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="py-6 px-4 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/gallery" element={<Gallery />} />
          <Route path="/camera" element={<Camera />} />
          <Route path="/gpio" element={<GPIO />} />
          <Route path="/scheduler" element={<Scheduler />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              duration: 3000,
              iconTheme: {
                primary: '#10b981',
                secondary: '#fff',
              },
            },
            error: {
              duration: 5000,
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff',
              },
            },
          }}
        />
        <FilterProvider>
          <Router>
            <AppLayout />
          </Router>
        </FilterProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
