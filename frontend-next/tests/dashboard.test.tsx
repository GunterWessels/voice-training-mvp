import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'

// Mobile layout tests — verify components render at 375px without crash
// Note: JSDOM has no layout engine; these tests confirm render stability,
// not actual Tailwind responsive behaviour.

jest.mock('next/navigation', () => ({ useRouter: () => ({ push: jest.fn() }) }))

// Supabase client requires env vars that aren't present in the test environment
jest.mock('../lib/supabase', () => ({
  createClient: () => ({
    auth: {
      getUser: jest.fn().mockResolvedValue({ data: { user: null } }),
      getSession: jest.fn().mockResolvedValue({ data: { session: null } }),
    },
  }),
}))

// Silence fetch calls — tests verify render, not data loading
global.fetch = jest.fn().mockResolvedValue({ ok: false }) as jest.Mock

describe('Dashboard mobile layout', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'innerWidth', { value: 375, configurable: true })
  })

  it('rep dashboard renders certification progress and stats at 375px', async () => {
    const { default: Dashboard } = await import('../app/dashboard/page')
    render(<Dashboard />)
    expect(screen.getByText('Certification Progress')).toBeInTheDocument()
    expect(screen.getByText('Sessions')).toBeInTheDocument()
    expect(screen.getByText('No sessions yet')).toBeInTheDocument()
  })

  it('manager dashboard renders cohort table at 375px', async () => {
    const { default: ManagerPage } = await import('../app/manager/page')
    render(<ManagerPage />)
    expect(screen.getByText('Cohort Overview')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /export csv/i })).toBeInTheDocument()
    expect(screen.getByText('No reps enrolled yet.')).toBeInTheDocument()
  })

  it('admin dashboard renders three tabs and shows KPIs when Metrics tab clicked', async () => {
    const { default: AdminPage } = await import('../app/admin/page')
    render(<AdminPage />)

    // All three tab buttons must be present
    expect(screen.getByRole('button', { name: 'Users' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sessions' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Metrics' })).toBeInTheDocument()

    // KPI content is hidden until Metrics tab is active
    expect(screen.queryByText('Platform Metrics')).not.toBeInTheDocument()

    // Click Metrics tab — KPI cards should appear
    fireEvent.click(screen.getByRole('button', { name: 'Metrics' }))
    expect(screen.getByText('Platform Metrics')).toBeInTheDocument()
    expect(screen.getByText('Cost (USD)')).toBeInTheDocument()
    expect(screen.getByText('Flagged Sessions')).toBeInTheDocument()
  })
})
