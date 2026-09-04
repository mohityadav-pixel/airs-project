/**
 * Global city + station selection.
 *
 * Every page reads the same selection, so switching city on the map and then
 * opening Predictions does not silently reset to a different location.
 */
import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'

import { api } from './api'
import type { City, Station } from './types'

const CITY_KEY = 'airs.city'
const STATION_KEY = 'airs.station'

interface SelectionValue {
  citySlug: string | undefined
  stationId: number | undefined
  cities: City[]
  stations: Station[]
  city: City | undefined
  station: Station | undefined
  setCity: (slug: string) => void
  setStation: (id: number | undefined) => void
  isLoading: boolean
}

const SelectionContext = createContext<SelectionValue | null>(null)

export function SelectionProvider({ children }: { children: ReactNode }) {
  const [citySlug, setCitySlug] = useState<string | undefined>(() => {
    try { return localStorage.getItem(CITY_KEY) ?? undefined } catch { return undefined }
  })
  const [stationId, setStationId] = useState<number | undefined>(() => {
    try {
      const raw = localStorage.getItem(STATION_KEY)
      return raw ? Number(raw) : undefined
    } catch { return undefined }
  })

  const citiesQuery = useQuery({ queryKey: ['cities'], queryFn: api.cities,
    staleTime: 60 * 60 * 1000 })
  const stationsQuery = useQuery({
    queryKey: ['stations', citySlug], queryFn: () => api.stations(citySlug),
    enabled: citiesQuery.isSuccess, staleTime: 60 * 60 * 1000 })

  const cities = citiesQuery.data ?? []
  const stations = useMemo(() => stationsQuery.data ?? [], [stationsQuery.data])

  // Default to the first configured city once we know what exists.
  useEffect(() => {
    if (!citySlug && cities.length) setCitySlug(cities[0].slug)
  }, [cities, citySlug])

  // A station from another city must not survive a city switch.
  useEffect(() => {
    if (stationId && stations.length && !stations.some((s) => s.id === stationId)) {
      setStationId(undefined)
    }
  }, [stations, stationId])

  const value = useMemo<SelectionValue>(() => ({
    citySlug, stationId, cities, stations,
    city: cities.find((c) => c.slug === citySlug),
    station: stations.find((s) => s.id === stationId),
    setCity: (slug) => {
      setCitySlug(slug); setStationId(undefined)
      try {
        localStorage.setItem(CITY_KEY, slug); localStorage.removeItem(STATION_KEY)
      } catch { /* ignore */ }
    },
    setStation: (id) => {
      setStationId(id)
      try {
        if (id) localStorage.setItem(STATION_KEY, String(id))
        else localStorage.removeItem(STATION_KEY)
      } catch { /* ignore */ }
    },
    isLoading: citiesQuery.isLoading || stationsQuery.isLoading,
  }), [citySlug, stationId, cities, stations, citiesQuery.isLoading,
       stationsQuery.isLoading])

  return <SelectionContext.Provider value={value}>{children}</SelectionContext.Provider>
}

export function useSelection() {
  const ctx = useContext(SelectionContext)
  if (!ctx) throw new Error('useSelection must be used inside SelectionProvider')
  return ctx
}
