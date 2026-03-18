import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

jest.mock('next/navigation', () => ({ useRouter: () => ({ replace: jest.fn() }) }))
jest.mock('../lib/supabase', () => ({
  createClient: () => ({
    auth: {
      getSession: jest.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: jest.fn().mockReturnValue({
        data: { subscription: { unsubscribe: jest.fn() } },
      }),
      signOut: jest.fn().mockResolvedValue({}),
    },
  }),
}))
global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 403 }) as jest.Mock

describe('Auth callback', () => {
  it('renders verifying state on mount', async () => {
    const { default: CallbackPage } = await import('../app/auth/callback/page')
    render(<CallbackPage />)
    expect(screen.getByText(/verifying/i)).toBeInTheDocument()
  })
})
