import { render, screen } from '@testing-library/react'
import { RepHint } from '@/components/RepHint'

it('renders hint text when provided', () => {
  render(<RepHint hint="Try connecting to the financial impact." />)
  expect(screen.getByText(/financial impact/i)).toBeInTheDocument()
})

it('renders nothing when hint is null', () => {
  const { container } = render(<RepHint hint={null} />)
  expect(container.firstChild).toBeNull()
})
