import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders title', () => {
    render(<App />)
    expect(screen.getByText(/Multimodal News Intelligence Agent/i)).toBeTruthy()
    expect(screen.getByText(/Quick Brief/i)).toBeTruthy()
    expect(screen.getByText(/In-Depth/i)).toBeTruthy()
  })
})
