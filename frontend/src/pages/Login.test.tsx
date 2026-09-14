import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { AuthProvider } from '../context/AuthContext'
import Login from './Login'

vi.mock('../api/auth', () => ({
  login: vi.fn().mockRejectedValue(new ApiError(401, 'E-mail ou senha inválidos')),
  me: vi.fn().mockRejectedValue(new ApiError(401, 'Não autenticado')),
  updateProfile: vi.fn(),
}))

function renderLogin() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('Login', () => {
  it('mostra a mensagem de erro do servidor quando as credenciais estão erradas', async () => {
    renderLogin()

    fireEvent.change(screen.getByLabelText(/E-mail/), { target: { value: 'mayra@example.com' } })
    fireEvent.change(screen.getByLabelText(/Senha/), { target: { value: 'senha-errada' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByText('E-mail ou senha inválidos')).toBeInTheDocument()
  })

  it('não mostra erro nenhum antes de tentar entrar', () => {
    renderLogin()

    expect(screen.queryByText('E-mail ou senha inválidos')).not.toBeInTheDocument()
  })

  it('exige e-mail e senha preenchidos antes de habilitar o envio nativo do formulário', async () => {
    renderLogin()

    const botao = screen.getByRole('button', { name: 'Entrar' })
    fireEvent.click(botao)

    // Sem preencher os campos obrigatórios, o próprio HTML impede o
    // envio — a mensagem de erro do servidor não deve aparecer.
    await waitFor(() => {
      expect(screen.queryByText('E-mail ou senha inválidos')).not.toBeInTheDocument()
    })
  })
})
