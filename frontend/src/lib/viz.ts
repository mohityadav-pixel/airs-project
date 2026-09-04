/**
 * Chart colour access.
 *
 * Charts read the same CSS variables the UI does, so a theme change moves
 * everything together and nothing hard-codes a hex. `useVizTokens` re-reads on
 * theme change because Recharts needs real colour strings, not var() refs.
 */
import { useEffect, useState } from 'react'

import { useTheme } from './theme'

const VARS = ['--viz-surface', '--viz-grid', '--viz-axis', '--viz-ink',
  '--viz-1', '--viz-2', '--viz-3', '--viz-4', '--viz-5', '--viz-6',
  '--viz-band'] as const

export interface VizTokens {
  surface: string; grid: string; axis: string; ink: string
  series: string[]; band: string
}

function read(): VizTokens {
  const styles = getComputedStyle(document.documentElement)
  const rgb = (name: string) => {
    const raw = styles.getPropertyValue(name).trim()
    return raw ? `rgb(${raw})` : '#888888'
  }
  const [surface, grid, axis, ink, s1, s2, s3, s4, s5, s6, band] =
    VARS.map((v) => rgb(v))
  return { surface, grid, axis, ink, series: [s1, s2, s3, s4, s5, s6], band }
}

export function useVizTokens(): VizTokens {
  const { resolved } = useTheme()
  const [tokens, setTokens] = useState<VizTokens>(() =>
    typeof window === 'undefined'
      ? { surface: '#fff', grid: '#ddd', axis: '#888', ink: '#111',
          series: ['#2a78d6'], band: '#2a78d6' }
      : read())
  useEffect(() => { setTokens(read()) }, [resolved])
  return tokens
}

/** Fixed slot per entity: the colour follows the source category, never its
 *  rank in the current sort, so filtering never repaints the survivors. */
export const SOURCE_SLOT: Record<string, number> = {
  traffic: 0,
  industrial: 1,
  construction_dust: 2,
  biomass_burning: 3,
  meteorological_accumulation: 4,
  other: 5,
}
