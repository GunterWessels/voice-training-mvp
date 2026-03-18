import { render } from '@testing-library/react'
import '@testing-library/jest-dom'

// Mobile layout tests — verify components render at 375px without crash
// Note: JSDOM has no layout engine; these tests confirm render stability,
// not actual Tailwind responsive behaviour.

jest.mock('next/navigation', () => ({ useRouter: () => ({ push: jest.fn() }) }))

describe('Dashboard mobile layout', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'innerWidth', { value: 375, configurable: true })
  })

  it('rep dashboard renders at 375px', async () => {
    const { default: Dashboard } = await import('../app/dashboard/page')
    const { container } = render(<Dashboard />)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('manager dashboard renders at 375px', async () => {
    const { default: ManagerPage } = await import('../app/manager/page')
    const { container } = render(<ManagerPage />)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('admin dashboard renders at 375px', async () => {
    const { default: AdminPage } = await import('../app/admin/page')
    const { container } = render(<AdminPage />)
    expect(container.firstChild).toBeInTheDocument()
  })
})
