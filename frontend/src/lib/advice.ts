/** Plain health guidance per US AQI band. General public-health advice only. */
export interface Advice {
  headline: string
  outdoor: string
  exercise: string
  mask: string
  windows: string
  sensitive: string
  purifier: string
}

const TABLE: Record<string, Advice> = {
  good: {
    headline: 'Great day to be outside',
    outdoor: 'Enjoy outdoor activities freely.',
    exercise: 'Any outdoor exercise is fine.',
    mask: 'No mask needed.',
    windows: 'Open the windows and air the house.',
    sensitive: 'No precautions needed.',
    purifier: 'Not needed.',
  },
  moderate: {
    headline: 'Acceptable for most people',
    outdoor: 'Fine for most. Take it easy if you notice irritation.',
    exercise: 'Fine, but sensitive people should shorten long, intense sessions.',
    mask: 'Not needed for most people.',
    windows: 'Ventilate in the afternoon; close near busy roads at rush hour.',
    sensitive: 'Watch for coughing or breathlessness.',
    purifier: 'Optional for sensitive people.',
  },
  usg: {
    headline: 'Sensitive groups should take care',
    outdoor: 'Children, older adults and anyone with asthma or heart disease should cut long outdoor exposure.',
    exercise: 'Move intense workouts indoors or to the cleanest hours.',
    mask: 'N95 / FFP2 advised for sensitive people outdoors.',
    windows: 'Keep windows closed at peak hours.',
    sensitive: 'Keep inhalers and medicines handy.',
    purifier: 'Run one in the bedroom.',
  },
  unhealthy: {
    headline: 'Unhealthy for everyone',
    outdoor: 'Limit time outside; everyone may feel effects.',
    exercise: 'Avoid outdoor exercise. Train indoors.',
    mask: 'Wear a well-fitted N95 / FFP2 outdoors.',
    windows: 'Keep windows and doors closed.',
    sensitive: 'Stay indoors as much as possible.',
    purifier: 'Run it continuously.',
  },
  very_unhealthy: {
    headline: 'Health alert',
    outdoor: 'Avoid going outside unless necessary.',
    exercise: 'No outdoor exercise.',
    mask: 'N95 / FFP2 is essential outdoors.',
    windows: 'Seal the house; avoid indoor smoke too.',
    sensitive: 'Stay indoors and follow your clinician’s plan.',
    purifier: 'Essential — run on high.',
  },
  hazardous: {
    headline: 'Emergency conditions',
    outdoor: 'Stay indoors.',
    exercise: 'None outdoors.',
    mask: 'N95 / FFP2 if you must go out.',
    windows: 'Keep everything shut.',
    sensitive: 'Seek medical help if you feel unwell.',
    purifier: 'Essential — run on high in every room you use.',
  },
}

export function adviceFor(key?: string | null): Advice | null {
  return key ? TABLE[key] ?? null : null
}

/** Vivid card gradient per band; text colour chosen for contrast. */
export const BAND_STYLE: Record<string, { from: string; to: string; text: string
                                          soft: string }> = {
  good: { from: '#34D399', to: '#059669', text: '#ffffff', soft: '#D1FAE5' },
  moderate: { from: '#FDE047', to: '#F59E0B', text: '#3b2a00', soft: '#FEF3C7' },
  usg: { from: '#FDBA74', to: '#EA580C', text: '#ffffff', soft: '#FFEDD5' },
  unhealthy: { from: '#FB7185', to: '#DC2626', text: '#ffffff', soft: '#FFE4E6' },
  very_unhealthy: { from: '#C4B5FD', to: '#7C3AED', text: '#ffffff', soft: '#EDE9FE' },
  hazardous: { from: '#BE123C', to: '#4C0519', text: '#ffffff', soft: '#FFE4E6' },
}

export function bandStyle(key?: string | null) {
  return (key && BAND_STYLE[key]) || { from: '#60A5FA', to: '#4F46E5',
                                       text: '#ffffff', soft: '#E0E7FF' }
}
