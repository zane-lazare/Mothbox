import { useState } from 'react'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { useBatchTagPhotos, useGpsExifConfig } from '../../hooks/useGpsExif'
import toast from 'react-hot-toast'

const SOURCE_OPTIONS = [
  { value: 'deployment,gps', label: 'Deployment \u2192 GPS fallback' },
  { value: 'gps', label: 'GPS only' },
  { value: 'manual', label: 'Manual coordinates' },
]

export default function GpsTagBanner({ untaggedCount, currentDirectory }) {
  const { data: config } = useGpsExifConfig()
  const batchTag = useBatchTagPhotos()
  const [source, setSource] = useState(null)
  const [manualLat, setManualLat] = useState('')
  const [manualLon, setManualLon] = useState('')

  // Use config default or fallback
  const effectiveSource = source ?? config?.default_sources?.join(',') ?? 'deployment,gps'

  if (!untaggedCount || untaggedCount === 0) return null

  const handleTag = () => {
    const sources = effectiveSource.split(',')
    const payload = {
      coordinate_sources: sources,
    }
    if (currentDirectory) {
      payload.directory = currentDirectory
    }
    if (sources.includes('manual')) {
      const lat = parseFloat(manualLat)
      const lon = parseFloat(manualLon)
      if (isNaN(lat) || isNaN(lon)) {
        toast.error('Please enter valid latitude and longitude')
        return
      }
      payload.manual_coords = { lat, lon }
    }
    batchTag.mutate(payload, {
      onSuccess: (res) => {
        const data = res.data
        toast.success(`Tagged ${data.tagged} of ${data.total} photos`)
      },
      onError: () => toast.error('Tagging failed'),
    })
  }

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ExclamationTriangleIcon className="h-5 w-5 text-amber-600" />
          <span className="text-sm font-medium text-amber-900">
            {untaggedCount} photo{untaggedCount !== 1 ? 's' : ''} without GPS coordinates
          </span>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={effectiveSource}
            onChange={(e) => setSource(e.target.value)}
            className="text-sm border border-amber-300 rounded px-2 py-1 bg-white"
          >
            {SOURCE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <button
            onClick={handleTag}
            disabled={batchTag.isPending}
            className="px-3 py-1 text-sm bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50"
          >
            {batchTag.isPending ? 'Tagging...' : 'Tag Now'}
          </button>
        </div>
      </div>
      {effectiveSource.split(',').includes('manual') && (
        <div className="mt-2 flex items-center gap-2">
          <input
            type="number"
            step="any"
            placeholder="Latitude"
            value={manualLat}
            onChange={(e) => setManualLat(e.target.value)}
            className="text-sm border rounded px-2 py-1 w-32"
          />
          <input
            type="number"
            step="any"
            placeholder="Longitude"
            value={manualLon}
            onChange={(e) => setManualLon(e.target.value)}
            className="text-sm border rounded px-2 py-1 w-32"
          />
        </div>
      )}
    </div>
  )
}
