import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'sonner'
import './index.css'
import './console.css'
import './pages.css'
import './workflow.css'
import App from './App.tsx'
import { useAuth } from './store/auth'

const client = new QueryClient({ defaultOptions: { queries: { staleTime: 4_000, retry: 1 } } })

useAuth.subscribe((state, previous) => { if(state.user?.workspace_id !== previous.user?.workspace_id) client.clear() })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <App />
        <Toaster theme="dark" position="top-right" richColors />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
