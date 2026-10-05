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
      { to: '/pacientes', label: 'Todos Os Pacientes' },
      { to: '/atendimento/novo', label: 'Novo Atendimento' },
    ],
  },
  { to: '/configuracoes', label: 'Configurações', children: [{ to: '/configuracoes/capa', label: 'Capa Dos Relatórios' }] },
  { to: '/logs', label: 'Ver Logs' },
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
    expect(screen.getByRole('link', { name: 'Todos Os Pacientes' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Novo Atendimento' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Pacientes' })).not.toBeInTheDocument()
  })

  it('Configurações continua recolhível e Ver Logs é um item próprio', () => {
    renderizar('/pacientes')
    expect(screen.getByRole('link', { name: 'Ver Logs' })).toHaveAttribute('href', '/logs')
    expect(screen.queryByRole('link', { name: 'Capa Dos Relatórios' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Configurações' }))
    expect(screen.getByRole('link', { name: 'Capa Dos Relatórios' })).toBeVisible()
  })

  it('a subopção atual fica destacada', () => {
    renderizar('/atendimento/novo')
    expect(screen.getByRole('link', { name: 'Novo Atendimento' })).toHaveAttribute('aria-current', 'page')
  })
})
