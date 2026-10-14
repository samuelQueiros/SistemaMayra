import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { SidebarNav } from './SidebarNav'

const ITENS = [
  {
    to: '/pacientes',
    label: 'Pacientes',
    alwaysOpen: true,
    children: [
      { to: '/pacientes', label: 'Todos os pacientes' },
      { to: '/atendimento/novo', label: 'Novo atendimento' },
    ],
  },
  { to: '/configuracoes', label: 'Configurações', children: [{ to: '/configuracoes/capa', label: 'Capa dos relatórios' }] },
  { to: '/logs', label: 'Registro de atividades' },
]

const renderizar = (url: string) =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <SidebarNav items={ITENS} />
    </MemoryRouter>,
  )

describe('SidebarNav', () => {
  it('Pacientes mostra as subopções o tempo todo, mesmo fora das páginas de pacientes', () => {
    renderizar('/logs')
    expect(screen.getByRole('link', { name: 'Todos os pacientes' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Novo atendimento' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Pacientes' })).not.toBeInTheDocument()
  })

  it('Configurações continua recolhível e Registro de atividades é um item próprio', () => {
    renderizar('/pacientes')
    expect(screen.getByRole('link', { name: 'Registro de atividades' })).toHaveAttribute('href', '/logs')
    expect(screen.queryByRole('link', { name: 'Capa dos relatórios' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Configurações' }))
    expect(screen.getByRole('link', { name: 'Capa dos relatórios' })).toBeVisible()
  })

  it('a subopção atual fica destacada', () => {
    renderizar('/atendimento/novo')
    expect(screen.getByRole('link', { name: 'Novo atendimento' })).toHaveAttribute('aria-current', 'page')
  })
})
