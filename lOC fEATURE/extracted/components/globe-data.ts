export type RoutePoint = { lat: number; lng: number }

export function projectToMap(lat: number, lng: number) {
  return { left: `${((lng + 180) / 360) * 100}%`, top: `${((90 - lat) / 180) * 100}%` }
}

export const routes = [
  { from: [40.7, -74], to: [51.5, -0.1], label: 'New York → London' },
  { from: [35.7, 139.7], to: [1.3, 103.8], label: 'Tokyo → Singapore' },
  { from: [-33.9, 151.2], to: [37.8, -122.4], label: 'Sydney → San Francisco' },
  { from: [25.2, 55.3], to: [48.9, 2.4], label: 'Dubai → Paris' },
  { from: [21.23977428159777, 81.61403765197772], to: [21.134691845052814, 81.66864225382541], label: 'Raipur → Destination' },
]

export const routePoints: RoutePoint[] = routes.flatMap((route) => [
  { lat: route.from[0], lng: route.from[1] },
  { lat: route.to[0], lng: route.to[1] },
])

export const travelLandmarks = [
  { city: 'New York', country: 'United States', lat: 40.7, lng: -74 },
  { city: 'London', country: 'United Kingdom', lat: 51.5, lng: -0.1 },
  { city: 'Tokyo', country: 'Japan', lat: 35.7, lng: 139.7 },
  { city: 'Singapore', country: 'Singapore', lat: 1.3, lng: 103.8 },
  { city: 'Sydney', country: 'Australia', lat: -33.9, lng: 151.2 },
  { city: 'San Francisco', country: 'United States', lat: 37.8, lng: -122.4 },
  { city: 'Dubai', country: 'United Arab Emirates', lat: 25.2, lng: 55.3 },
  { city: 'Paris', country: 'France', lat: 48.9, lng: 2.4 },
  { city: 'Raipur', country: 'India', lat: 21.23977428159777, lng: 81.61403765197772 },
  { city: 'Destination', country: 'India', lat: 21.134691845052814, lng: 81.66864225382541 },
]
