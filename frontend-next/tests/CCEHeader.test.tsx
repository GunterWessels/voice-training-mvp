import { render, screen } from '@testing-library/react'
import CCEHeader from '@/components/CCEHeader'

describe('CCEHeader', () => {
  it('renders BOSTON SCIENTIFIC text', () => {
    render(<CCEHeader />)
    expect(screen.getByText('BOSTON SCIENTIFIC')).toBeInTheDocument()
  })

  it('renders subtitle text', () => {
    render(<CCEHeader />)
    expect(screen.getByText('Continuing Clinical Excellence')).toBeInTheDocument()
  })

  it('renders avatar when userInitials provided', () => {
    render(<CCEHeader userInitials="SC" />)
    expect(screen.getByText('SC')).toBeInTheDocument()
  })

  it('does not render avatar when userInitials omitted', () => {
    render(<CCEHeader />)
    expect(screen.queryByTestId('cce-avatar')).not.toBeInTheDocument()
  })
})
