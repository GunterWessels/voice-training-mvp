import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import AdminUserTable from '../components/AdminUserTable'
import AdminUploadFlow from '../components/AdminUploadFlow'

const mockUsers = [
  { id: '1', email: 'rep@bsci.com', first_name: 'Sam', last_name: 'Lee', role: 'rep', cohort_id: null },
]

describe('AdminUserTable', () => {
  it('renders user rows', () => {
    render(
      <AdminUserTable
        users={mockUsers}
        onAdd={jest.fn()}
        onUpdate={jest.fn()}
        onDelete={jest.fn()}
        onInvite={jest.fn()}
      />
    )
    expect(screen.getByText('rep@bsci.com')).toBeInTheDocument()
    expect(screen.getByText('Sam Lee')).toBeInTheDocument()
  })

  it('shows empty state when no users', () => {
    render(
      <AdminUserTable
        users={[]}
        onAdd={jest.fn()}
        onUpdate={jest.fn()}
        onDelete={jest.fn()}
        onInvite={jest.fn()}
      />
    )
    expect(screen.getByText(/no users/i)).toBeInTheDocument()
  })

  it('opens add modal on button click', () => {
    render(
      <AdminUserTable
        users={[]}
        onAdd={jest.fn()}
        onUpdate={jest.fn()}
        onDelete={jest.fn()}
        onInvite={jest.fn()}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /add user/i }))
    expect(screen.getByLabelText(/work email/i)).toBeInTheDocument()
  })

  it('calls onDelete when delete confirmed', async () => {
    const onDelete = jest.fn().mockResolvedValue(undefined)
    render(
      <AdminUserTable
        users={mockUsers}
        onAdd={jest.fn()}
        onUpdate={jest.fn()}
        onDelete={onDelete}
        onInvite={jest.fn()}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /delete/i }))
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }))
    expect(onDelete).toHaveBeenCalledWith('1')
  })
})

describe('AdminUploadFlow', () => {
  it('renders Upload List button', () => {
    render(<AdminUploadFlow authHeader={{}} onImportComplete={jest.fn()} />)
    expect(screen.getByRole('button', { name: /upload list/i })).toBeInTheDocument()
  })
})
