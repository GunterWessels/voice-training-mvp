import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import AudioStateDisplay from '../components/AudioStateDisplay'

it('shows listening indicator when state is listening', () => {
  render(<AudioStateDisplay state="listening" />)
  expect(screen.getByText(/listening/i)).toBeInTheDocument()
  expect(screen.getByTestId('audio-state')).toHaveAttribute('data-state', 'listening')
})

it('shows processing indicator when state is processing', () => {
  render(<AudioStateDisplay state="processing" />)
  expect(screen.getByText(/processing/i)).toBeInTheDocument()
  expect(screen.getByTestId('audio-state')).toHaveAttribute('data-state', 'processing')
})

it('shows speaking indicator when state is speaking', () => {
  render(<AudioStateDisplay state="speaking" />)
  expect(screen.getByText(/speaking/i)).toBeInTheDocument()
  expect(screen.getByTestId('audio-state')).toHaveAttribute('data-state', 'speaking')
})

it('shows idle state by default', () => {
  render(<AudioStateDisplay state="idle" />)
  expect(screen.getByTestId('audio-state')).toHaveAttribute('data-state', 'idle')
})
