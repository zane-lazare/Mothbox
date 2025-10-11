import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import Gallery from './pages/Gallery'
import Settings from './pages/Settings'
import Camera from './pages/Camera'
import GPIO from './pages/GPIO'
import Scheduler from './pages/Scheduler'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-gray-100">
          {/* Navigation */}
          <nav className="bg-white shadow-lg">
            <div className="max-w-7xl mx-auto px-4">
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
          <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
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
      </Router>
    </QueryClientProvider>
  )
}

export default App
