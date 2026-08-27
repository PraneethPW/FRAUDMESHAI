import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import App from './App'
import { RiskBadge } from './components/UI'
import { errorMessage } from './lib/api'
import { useAuth } from './store/auth'

function renderApp(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>)
}

describe('FraudMesh application boundaries', () => {
  it('redirects unauthenticated console access to sign in', async () => {
    useAuth.getState().clearSession()
    renderApp('/app')
    expect(await screen.findByRole('heading', { name: 'Welcome back.' }, { timeout: 15_000 })).toBeInTheDocument()
  })

  it('renders accessible risk context', () => {
    render(<RiskBadge level="CRITICAL" />)
    expect(screen.getByText('CRITICAL')).toBeInTheDocument()
  })

  it('returns useful API failure language', () => {
    expect(errorMessage(new Error('Dataset invalid'))).toBe('Dataset invalid')
  })
})
