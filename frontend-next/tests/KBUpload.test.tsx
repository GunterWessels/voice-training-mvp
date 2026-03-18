import { render, screen } from '@testing-library/react'
import { KBUploadTab } from '@/components/admin/KBUploadTab'

describe('KBUploadTab', () => {
  it('renders drop zone', () => {
    render(<KBUploadTab productId="tria_stents" />)
    expect(screen.getByText(/drop any file/i)).toBeInTheDocument()
  })
  it('shows manual entry form', () => {
    render(<KBUploadTab productId="tria_stents" />)
    expect(screen.getByLabelText(/domain/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/fda-cleared/i)).toBeInTheDocument()
  })
})
