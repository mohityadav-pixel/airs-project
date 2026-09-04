import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

import App from './App'
import { ApiError } from './lib/api'
import { AuthProvider } from './lib/auth'
import { SelectionProvider } from './lib/selection'
import { ThemeProvider } from './lib/theme'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Air quality updates hourly upstream; refetching harder just burns quota.
      staleTime: 3 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // A missing key or an unconfigured provider will not fix itself.
        if (error instanceof ApiError
            && [400, 401, 403, 404, 503].includes(error.status)) return false
        return failureCount < 2
      },
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>
            <SelectionProvider>
              <App />
            </SelectionProvider>
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
