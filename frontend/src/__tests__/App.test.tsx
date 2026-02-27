import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'
import { describe, it, expect } from 'vitest'

describe('App', () => {
  it('renders without crashing', () => {
    localStorage.removeItem('token')
    const { container } = render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )
    expect(container).toBeTruthy()
  })
})
