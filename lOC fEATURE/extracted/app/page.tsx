'use client'

import { useState } from 'react'
import { AlertCircle, ArrowUpRight, Crosshair, Eye, EyeOff, Filter, Globe2, List, LocateFixed, Map, Plus, Trash2, Upload, X, ZoomIn } from 'lucide-react'
import { DottedGlobe, routes, type GlobeMode } from '@/components/dotted-globe'

interface Location {
  id: string
  city: string
  lat: number
  lng: number
  timestamp?: string
  notes?: string
}

export default function Page() {
  const [globeMode, setGlobeMode] = useState<GlobeMode>('globe')
  const [resetViewToken, setResetViewToken] = useState(0)
  const [connectDots, setConnectDots] = useState(true)
  const [showCities, setShowCities] = useState(true)
  const [locations, setLocations] = useState<Location[]>(
    routes.flatMap(r => [
      { id: `${r.from[0]}-${r.from[1]}`, city: `Location ${r.from[0].toFixed(1)}°N`, lat: r.from[0], lng: r.from[1], timestamp: '2025-01-15 14:32' },
      { id: `${r.to[0]}-${r.to[1]}`, city: `Location ${r.to[0].toFixed(1)}°N`, lat: r.to[0], lng: r.to[1], timestamp: '2025-01-20 09:18' }
    ])
  )
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null)
  const [showLocationsPanel, setShowLocationsPanel] = useState(true)
  const [filterCluster, setFilterCluster] = useState(false)

  const addLocation = () => {
    const newLocation: Location = {
      id: `${Math.random()}`,
      city: 'New location',
      lat: 20 + Math.random() * 40,
      lng: -100 + Math.random() * 150,
      timestamp: new Date().toLocaleString()
    }
    setLocations([...locations, newLocation])
  }

  const removeLocation = (id: string) => {
    setLocations(locations.filter(l => l.id !== id))
    if (selectedLocation === id) setSelectedLocation(null)
  }

  const clusterLocations = () => {
    // Group nearby locations
    const grouped: Record<string, Location[]> = {}
    locations.forEach(loc => {
      const key = `${Math.round(loc.lat / 5) * 5},${Math.round(loc.lng / 5) * 5}`
      grouped[key] = [...(grouped[key] || []), loc]
    })
    return Object.values(grouped).filter(g => g.length > 1)
  }

  const clusters = filterCluster ? clusterLocations() : []

  return (
    <main className="h-[100dvh] max-h-[100dvh] bg-[#f4f8f8] text-slate-900 overflow-hidden flex flex-col">
      {/* Header */}
      <header className="relative z-30 shrink-0 border-b border-slate-200 bg-white/90 backdrop-blur-sm px-6 py-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-lg bg-cyan-500/20 border border-cyan-500/40">
            <Crosshair size={20} className="text-cyan-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">INVESTIGATOR ATLAS</h1>
            <p className="text-xs text-slate-500">Travel pattern analysis & location intelligence</p>
          </div>
        </div>
        <div className="hidden sm:flex items-center gap-3 text-xs">
          <div className="px-3 py-1.5 rounded-full border border-slate-700 bg-white border border-slate-200 shadow-sm flex items-center gap-2">
            <div className="size-1.5 rounded-full bg-green-400" />
            <span className="text-slate-600">Live · {locations.length} locations tracked</span>
          </div>
        </div>
      </header>

      {/* Main workspace */}
      <div className="min-h-0 flex-1 overflow-hidden flex gap-4 p-4">
        {/* Globe viewport */}
        <div className="min-h-0 flex-1 flex flex-col gap-3 min-w-0">
          <div className="relative min-h-0 flex-1 rounded-xl border border-slate-200 bg-white overflow-hidden shadow-xl">
            <DottedGlobe mode={globeMode} connectDots={connectDots} showCities={showCities} resetViewToken={resetViewToken} />

            {/* Control panel overlay */}
            <div className="absolute top-4 left-4 right-4 z-20 flex flex-col gap-2">
              {/* Mode & Route toggles */}
              <div className="flex flex-wrap gap-2">
                <div className="flex gap-1 rounded-lg border border-slate-200 bg-white/95 backdrop-blur-sm p-1">
                  <button
                    onClick={() => setGlobeMode('globe')}
                    className={`px-3 py-1.5 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${
                      globeMode === 'globe'
                        ? 'bg-[#0f8f7a] text-white border border-[#0f8f7a]'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <Globe2 size={13} /> 3D Globe
                  </button>
                  <button
                    onClick={() => setGlobeMode('map')}
                    className={`px-3 py-1.5 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${
                      globeMode === 'map'
                        ? 'bg-[#0f8f7a] text-white border border-[#0f8f7a]'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <Map size={13} /> 2D Map
                  </button>
                </div>

                <button
                  onClick={() => setConnectDots(!connectDots)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 border ${
                    connectDots
                      ? 'bg-amber-50 border-amber-300 text-amber-700 shadow-sm'
                      : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                >
                  <ArrowUpRight size={13} /> {connectDots ? 'Routes' : 'Points'}
                </button>

                <button
                  onClick={() => setShowCities(!showCities)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 border ${
                    showCities
                      ? 'bg-sky-50 border-sky-300 text-sky-700 shadow-sm'
                      : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                >
                  {showCities ? <Eye size={13} /> : <EyeOff size={13} />} Cities
                </button>
                <button
                  onClick={() => setResetViewToken((value) => value + 1)}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 border bg-white border-slate-200 text-slate-700 shadow-sm hover:border-teal-400 hover:text-teal-700"
                  title="Center the globe on India and the Tropic of Cancer"
                >
                  <LocateFixed size={13} /> Align India
                </button>
              </div>
            </div>

            {/* Zoom hint */}
            <div className="absolute bottom-4 left-4 z-10 px-3 py-2 rounded-lg border border-slate-200 bg-white/95 backdrop-blur-sm text-xs text-slate-500 flex items-center gap-2">
              <ZoomIn size={12} /> Scroll to zoom · Drag to rotate
            </div>
          </div>

          {/* Stats bar */}
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-slate-200 bg-white/90 p-3">
              <p className="text-xs text-slate-500 uppercase tracking-wide">Total locations</p>
              <p className="text-2xl font-bold text-cyan-400 mt-1">{locations.length}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white/90 p-3">
              <p className="text-xs text-slate-500 uppercase tracking-wide">Active routes</p>
              <p className="text-2xl font-bold text-amber-400 mt-1">{connectDots ? routes.length : 0}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white/90 p-3">
              <p className="text-xs text-slate-500 uppercase tracking-wide">Clusters found</p>
              <p className="text-2xl font-bold text-red-400 mt-1">{clusters.length}</p>
            </div>
          </div>
        </div>

        {/* Right sidebar - Locations panel */}
        {showLocationsPanel && (
          <div className="min-h-0 w-80 flex flex-col gap-3 min-w-0">
            <div className="rounded-xl border border-slate-200 bg-white/90 backdrop-blur-sm overflow-hidden flex flex-col h-full">
              {/* Panel header */}
              <div className="border-b border-slate-200/60 px-4 py-3 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <List size={16} className="text-cyan-400 flex-shrink-0" />
                  <h2 className="text-sm font-bold truncate">Location Log</h2>
                </div>
                <button
                  onClick={() => setShowLocationsPanel(false)}
                  className="p-1 hover:bg-slate-100 rounded-lg transition flex-shrink-0"
                  aria-label="Close"
                >
                  <X size={16} className="text-slate-500" />
                </button>
              </div>

              {/* Toolbar */}
              <div className="border-b border-slate-200/60 px-4 py-2 flex gap-2 flex-wrap">
                <button
                  onClick={addLocation}
                  className="px-3 py-1.5 rounded-lg bg-teal-50 border border-teal-200 text-teal-700 hover:bg-teal-100 transition text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                >
                  <Plus size={13} /> Add
                </button>
                <button
                  onClick={() => setFilterCluster(!filterCluster)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 border ${
                    filterCluster
                      ? 'bg-red-50 border-red-200 text-red-700 shadow-sm'
                      : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                >
                  <Filter size={13} /> Clusters
                </button>
              </div>

              {/* Locations list */}
              <div className="flex-1 overflow-y-auto">
                {filterCluster ? (
                  // Clustered view
                  <div className="divide-y divide-slate-800/60">
                    {clusters.map((cluster, idx) => (
                      <div key={idx} className="p-3 border-b border-slate-200/40">
                        <div className="px-2 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 mb-2">
                          <p className="text-xs font-bold text-red-400">Cluster {idx + 1}</p>
                          <p className="text-xs text-red-300/60 mt-0.5">{cluster.length} locations within region</p>
                        </div>
                        <div className="space-y-1.5">
                          {cluster.map(loc => (
                            <div
                              key={loc.id}
                              className={`p-2 rounded-lg cursor-pointer transition border ${
                                selectedLocation === loc.id
                                  ? 'bg-cyan-500/20 border-cyan-500/40'
                                  : 'bg-slate-800/30 border-slate-700/40 hover:bg-slate-50'
                              }`}
                              onClick={() => setSelectedLocation(loc.id)}
                            >
                              <p className="text-xs font-semibold text-cyan-300">{loc.city}</p>
                              <p className="text-[11px] text-slate-500 mt-0.5">{loc.lat.toFixed(2)}°N, {loc.lng.toFixed(2)}°E</p>
                              {loc.timestamp && <p className="text-[10px] text-slate-500 mt-1">{loc.timestamp}</p>}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  // Full list
                  <div className="divide-y divide-slate-800/60">
                    {locations.map(loc => (
                      <div
                        key={loc.id}
                        className={`p-3 cursor-pointer transition border-b border-slate-200/40 hover:bg-slate-800/30 ${
                          selectedLocation === loc.id ? 'bg-cyan-500/20' : ''
                        }`}
                        onClick={() => setSelectedLocation(loc.id)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-semibold text-cyan-300 truncate">{loc.city}</p>
                            <p className="text-[11px] text-slate-500 mt-1">{loc.lat.toFixed(2)}°N, {loc.lng.toFixed(2)}°E</p>
                            {loc.timestamp && <p className="text-[10px] text-slate-500 mt-1">{loc.timestamp}</p>}
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              removeLocation(loc.id)
                            }}
                            className="p-1 hover:bg-red-500/20 rounded-lg transition flex-shrink-0"
                            aria-label="Remove"
                          >
                            <Trash2 size={13} className="text-red-400" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Import hint */}
              <div className="border-t border-slate-200/60 px-4 py-2 text-[10px] text-slate-500 flex items-center gap-2">
                <AlertCircle size={12} /> Future: Import CSV/JSON with lat/lng data
              </div>
            </div>
          </div>
        )}

        {/* Collapsed sidebar toggle */}
        {!showLocationsPanel && (
          <button
            onClick={() => setShowLocationsPanel(true)}
            className="w-12 rounded-xl border border-slate-200 bg-white/90 hover:bg-slate-900 transition flex items-center justify-center"
            aria-label="Open locations panel"
          >
            <List size={18} className="text-cyan-400" />
          </button>
        )}
      </div>
    </main>
  )
}
