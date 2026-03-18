import { render, act } from '@testing-library/react'
import '@testing-library/jest-dom'
import CelebrationLayer from '../components/CelebrationLayer'

jest.mock('canvas-confetti', () => jest.fn())
import confetti from 'canvas-confetti'
const mockConfetti = confetti as jest.MockedFunction<typeof confetti>

beforeEach(() => mockConfetti.mockClear())

it('renders message overlay when celebrations enabled', () => {
  const { getByTestId } = render(
    <CelebrationLayer trigger="first_session" cohortCelebrationsEnabled={true} />
  )
  expect(getByTestId('celebration-message')).toBeInTheDocument()
})

it('invokes canvas-confetti for confetti-type trigger', async () => {
  await act(async () => {
    render(<CelebrationLayer trigger="first_session" cohortCelebrationsEnabled={true} />)
  })
  expect(mockConfetti).toHaveBeenCalledWith(
    expect.objectContaining({ particleCount: 120, spread: 70 })
  )
})

it('does not render or fire confetti when celebrations disabled', () => {
  const { queryByTestId } = render(
    <CelebrationLayer trigger="first_session" cohortCelebrationsEnabled={false} />
  )
  expect(queryByTestId('celebration-message')).not.toBeInTheDocument()
  expect(mockConfetti).not.toHaveBeenCalled()
})
