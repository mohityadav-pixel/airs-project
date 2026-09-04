import { useTheme } from '@/lib/theme'

export function ThemeToggle() {
  const { resolved, toggle } = useTheme()
  return (
    <button type="button" onClick={toggle}
            className="btn-subtle h-9 w-9 p-0"
            aria-label={`Switch to ${resolved === 'dark' ? 'light' : 'dark'} mode`}
            title={`Switch to ${resolved === 'dark' ? 'light' : 'dark'} mode`}>
      {resolved === 'dark' ? (
        <svg viewBox="0 0 24 24" className="h-4.5 w-4.5" width="18" height="18"
             fill="none" stroke="currentColor" strokeWidth="1.8"
             strokeLinecap="round" aria-hidden="true">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none"
             stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
             strokeLinejoin="round" aria-hidden="true">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      )}
    </button>
  )
}
