'use client'

import { useEffect, useRef, useState } from 'react'
import type { Viewer as CesiumViewer } from 'cesium'
import { projectToMap, routes, routePoints, travelLandmarks, type RoutePoint } from './globe-data'
import 'cesium/Build/Cesium/Widgets/widgets.css'

export type GlobeMode = 'globe' | 'map'
export type { RoutePoint }

type GlobeProps = {
  mode?: GlobeMode
  connectDots?: boolean
  smooth?: boolean
  showCities?: boolean
  resetViewToken?: number
}

function MapView({ connectDots, smooth }: { connectDots: boolean; smooth: boolean }) {
  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl border border-slate-800 bg-[#123247]">
      <div className="absolute inset-0 bg-[url('/earth-texture.png')] bg-cover bg-center opacity-90" />
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 via-transparent to-slate-950/35" />
      <div className="absolute inset-0">
        {connectDots && routes.map((route) => {
          const start = projectToMap(route.from[0], route.from[1])
          const end = projectToMap(route.to[0], route.to[1])
          const dx = parseFloat(end.left) - parseFloat(start.left)
          const dy = parseFloat(end.top) - parseFloat(start.top)
          return <span key={route.label} className="absolute h-0.5 origin-left bg-cyan-200 shadow-[0_0_8px_rgba(103,232,249,0.9)]" style={{ left: start.left, top: start.top, width: `${Math.hypot(dx, dy)}%`, transform: `rotate(${Math.atan2(dy, dx) * 57.3}deg)` }} />
        })}
        {routePoints.map((point, index) => <span key={`${point.lat}-${point.lng}-${index}`} className={`absolute -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-100 shadow-[0_0_10px_rgba(103,232,249,0.95)] ${smooth ? 'size-1.5 opacity-80' : 'size-2.5'}`} style={projectToMap(point.lat, point.lng)} />)}
      </div>
      <div className="absolute bottom-4 left-4 rounded-lg border border-white/20 bg-slate-950/55 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-100">Mercator projection · live routes</div>
    </div>
  )
}

export function DottedGlobe({ mode = 'globe', connectDots = true, smooth = false, showCities = true, resetViewToken = 0 }: GlobeProps) {
  return mode === 'map' ? <MapView connectDots={connectDots} smooth={smooth} /> : <CesiumGlobe connectDots={connectDots} smooth={smooth} showCities={showCities} resetViewToken={resetViewToken} />
}

function CesiumGlobe({ connectDots, smooth, showCities, resetViewToken }: { connectDots: boolean; smooth: boolean; showCities: boolean; resetViewToken: number }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<CesiumViewer | null>(null)
  const [status, setStatus] = useState('Loading Earth data…')

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !resetViewToken) return
    import('cesium').then(({ Cartesian3, Math: CesiumMath }) => {
      viewer.camera.flyTo({ destination: Cartesian3.fromDegrees(78.9629, 22.5937, 12500000), orientation: { heading: 0, pitch: CesiumMath.toRadians(-90), roll: 0 }, duration: 1.2 })
    })
  }, [resetViewToken])

  useEffect(() => {
    let cancelled = false
    async function loadGlobe() {
      ;(globalThis as typeof globalThis & { CESIUM_BASE_URL?: string }).CESIUM_BASE_URL = 'https://cesium.com/downloads/cesiumjs/releases/1.145/Build/Cesium/'
      const [{ Viewer, Ion, createWorldTerrainAsync, createOsmBuildingsAsync, Cartesian3, Cartesian2, Color, HeightReference, VerticalOrigin, ArcType }, tokenResponse] = await Promise.all([import('cesium'), fetch('/api/cesium-token', { cache: 'no-store' }).then((response) => response.json())])
      if (cancelled || !containerRef.current || !tokenResponse.token) { setStatus('Add a valid Cesium ion token to continue'); return }
      Ion.defaultAccessToken = tokenResponse.token
      const viewer = new Viewer(containerRef.current, { baseLayerPicker: false, animation: false, timeline: false, geocoder: false, homeButton: false, navigationHelpButton: false, fullscreenButton: false, sceneModePicker: false, infoBox: false, selectionIndicator: false, skyBox: false, skyAtmosphere: false, shouldAnimate: false })
      viewerRef.current = viewer
      try { viewer.terrainProvider = await createWorldTerrainAsync() } catch { setStatus('Earth loaded · terrain unavailable') }
      viewer.scene.globe.enableLighting = true
      viewer.scene.globe.showGroundAtmosphere = true
      viewer.scene.screenSpaceCameraController.minimumZoomDistance = 35
      viewer.scene.screenSpaceCameraController.maximumZoomDistance = 25000000
      try { viewer.scene.primitives.add(await createOsmBuildingsAsync()) } catch { setStatus('Earth loaded · buildings unavailable') }

      const markerColor = Color.fromCssColorString('#fb923c')
      const cyan = Color.fromCssColorString('#67e8f9')
      const glow = Color.fromCssColorString('#22d3ee')
      travelLandmarks.forEach((landmark) => viewer.entities.add({ name: landmark.city, position: Cartesian3.fromDegrees(landmark.lng, landmark.lat, 140), point: { pixelSize: smooth ? 10 : 14, color: markerColor, outlineColor: Color.WHITE, outlineWidth: 3, heightReference: HeightReference.CLAMP_TO_GROUND }, label: showCities ? { text: landmark.city, font: '600 14px Inter, sans-serif', fillColor: Color.WHITE, outlineColor: Color.fromCssColorString('#06111f'), outlineWidth: 4, showBackground: true, backgroundColor: Color.fromCssColorString('#06111fdd'), backgroundPadding: new Cartesian2(8, 5), pixelOffset: new Cartesian2(0, -22), verticalOrigin: VerticalOrigin.BOTTOM } : undefined }))
      routePoints.forEach((point, index) => viewer.entities.add({ name: `Route point ${index + 1}`, position: Cartesian3.fromDegrees(point.lng, point.lat, 90), point: { pixelSize: smooth ? 7 : 11, color: cyan, outlineColor: Color.WHITE, outlineWidth: 2, heightReference: HeightReference.CLAMP_TO_GROUND } }))
      if (connectDots) routes.forEach((route) => viewer.entities.add({ name: route.label, polyline: { positions: Cartesian3.fromDegreesArrayHeights([route.from[1], route.from[0], 180, route.to[1], route.to[0], 180]), width: smooth ? 3.5 : 5, material: glow, clampToGround: true, arcType: ArcType.GEODESIC } }))
      viewer.camera.setView({ destination: Cartesian3.fromDegrees(78.9629, 22.5937, 12500000), orientation: { heading: 0, pitch: -Math.PI / 2, roll: 0 } })
      viewer.resize()
      setStatus('Earth live · terrain and city detail enabled')
    }
    loadGlobe()
    return () => { cancelled = true; viewerRef.current?.destroy(); viewerRef.current = null }
  }, [connectDots, smooth, showCities])

  return <div className="relative h-full w-full overflow-hidden rounded-xl border border-slate-800 bg-black"><div ref={containerRef} className="h-full w-full" /><div className="pointer-events-none absolute bottom-4 left-4 rounded-lg border border-cyan-300/30 bg-slate-950/80 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-100 shadow-[0_0_20px_rgba(34,211,238,0.18)]">{status}</div></div>
}

export { projectToMap, routes, routePoints, travelLandmarks }
