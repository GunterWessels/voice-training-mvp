import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

jest.mock('@/lib/supabase', () => ({
  createClient: () => ({
    auth: {
      signInWithOtp: jest.fn(),
      onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })),
    }
  })
}))

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}))

describe('Auth flows', () => {
  it('renders login page with email input', async () => {
    const { default: LoginPage } = await import('../app/auth/login/page')
    render(<LoginPage />)
    expect(screen.getByRole('textbox', { name: /email/i })).toBeInTheDocument()
  })

  it('renders cohort join page with name input', async () => {
    const { default: JoinPage } = await import('../app/join/[token]/page')
    render(<JoinPage params={{ token: 'test-token' }} />)
    expect(screen.getByRole('textbox', { name: /name/i })).toBeInTheDocument()
  })
})
