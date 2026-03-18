import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import ArcProgress from '../components/ArcProgress'
import CofGates from '../components/CofGates'

describe('ArcProgress', () => {
  it('renders 6 dots', () => {
    render(<ArcProgress currentStage={1} totalStages={6} />)
    expect(screen.getAllByRole('presentation')).toHaveLength(6)
  })

  it('marks stage 3 as active when currentStage=3', () => {
    render(<ArcProgress currentStage={3} totalStages={6} />)
    const dots = screen.getAllByRole('presentation')
    expect(dots[2]).toHaveClass('animate-pulse')
  })
})

describe('CofGates', () => {
  it('shows 3 gate indicators', () => {
    render(<CofGates clinical={true} operational={false} financial={true} />)
    expect(screen.getByText(/clinical/i)).toBeInTheDocument()
    expect(screen.getByText(/operational/i)).toBeInTheDocument()
    expect(screen.getByText(/financial/i)).toBeInTheDocument()
  })

  it('applies passed class to passed gates', () => {
    const { container } = render(<CofGates clinical={true} operational={false} financial={false} />)
    expect(container.querySelector('[data-gate="clinical"]')).toHaveClass('text-green-500')
    expect(container.querySelector('[data-gate="operational"]')).not.toHaveClass('text-green-500')
  })
})
