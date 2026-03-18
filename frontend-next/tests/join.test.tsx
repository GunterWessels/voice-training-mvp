import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// Mock next/navigation before importing the component
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace: jest.fn() }) }))

// Intercept React.use so params resolves synchronously in test
jest.mock('react', () => ({
  ...jest.requireActual('react'),
  use: jest.fn().mockReturnValue({ token: 'test-token-123' }),
}))

import JoinPage from '../app/join/[token]/page'

describe('JoinPage POST body', () => {
  it('sends cohort_token (not token) in the request body', async () => {
    const fetchSpy = jest.fn().mockResolvedValue({ ok: true })
    global.fetch = fetchSpy

    render(<JoinPage params={Promise.resolve({ token: 'test-token-123' })} />)

    // Use role queries that work regardless of exact label text
    const nameInput = screen.getByRole('textbox', { name: /name/i })
    const emailInput = screen.getByRole('textbox', { name: /email/i })
    const submitBtn = screen.getByRole('button', { name: /join/i })

    fireEvent.change(nameInput, { target: { value: 'Sarah Chen' } })
    fireEvent.change(emailInput, { target: { value: 'sarah@bsci.com' } })
    fireEvent.click(submitBtn)

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled())

    const body = JSON.parse(fetchSpy.mock.calls[0][1].body)
    // This assertion fails on the existing stub (which sends `token`) and passes after the fix
    expect(body.cohort_token).toBe('test-token-123')
    expect(body.token).toBeUndefined()
  })
})
