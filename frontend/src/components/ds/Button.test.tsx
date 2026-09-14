import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Button } from './Button'

describe('Button', () => {
  it('renderiza o texto passado como children', () => {
    render(<Button>Salvar</Button>)

    expect(screen.getByRole('button', { name: 'Salvar' })).toBeInTheDocument()
  })

  it('chama onClick ao ser clicado', () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Clique Aqui</Button>)

    fireEvent.click(screen.getByRole('button', { name: 'Clique Aqui' }))

    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('não chama onClick quando desabilitado', () => {
    const onClick = vi.fn()
    render(
      <Button onClick={onClick} disabled>
        Desabilitado
      </Button>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Desabilitado' }))

    expect(onClick).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Desabilitado' })).toBeDisabled()
  })
})
