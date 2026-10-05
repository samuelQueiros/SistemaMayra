import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import * as patients from '../api/patients'
import RelatorioIA from './RelatorioIA'

vi.mock('../api/patients', () => ({
  listPatients: vi.fn(),
  createPatient: vi.fn(),
}))

const renderizar = () =>
  render(
    <MemoryRouter initialEntries={['/relatorio-ia']}>
      <RelatorioIA />
    </MemoryRouter>,
  )

const novo = { id: 'p9', name: 'Bia Lima', birth_date: '2020-01-10', notes: null, sex: 'Feminino', school_info: null }

describe('Relatório Por IA — paciente', () => {
  it('sem pacientes, já mostra o cadastro e, ao cadastrar, seleciona o paciente e abre o envio dos PDFs', async () => {
    vi.mocked(patients.listPatients).mockResolvedValue([])
    vi.mocked(patients.createPatient).mockResolvedValue(novo)
    renderizar()

    expect(await screen.findByText(/Nenhum paciente cadastrado ainda/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Nome Do Paciente/), { target: { value: 'Bia Lima' } })
    fireEvent.change(screen.getByLabelText(/Data De Nascimento/), { target: { value: '2020-01-10' } })
    fireEvent.change(screen.getByLabelText('Sexo'), { target: { value: 'Feminino' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cadastrar Paciente' }))

    expect(await screen.findByText('Arraste os PDFs para cá ou')).toBeInTheDocument()
    expect(patients.createPatient).toHaveBeenCalledWith({ name: 'Bia Lima', birth_date: '2020-01-10', sex: 'Feminino' })
    expect(screen.getByLabelText('Selecione O Paciente')).toHaveValue('p9')
  })

  it('com pacientes, "Novo Paciente" abre o cadastro e Cancelar volta à seleção', async () => {
    vi.mocked(patients.listPatients).mockResolvedValue([novo])
    renderizar()
    fireEvent.click(await screen.findByRole('button', { name: 'Novo Paciente' }))
    expect(screen.getByRole('form', { name: 'Cadastrar novo paciente' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(screen.getByLabelText('Selecione O Paciente')).toBeInTheDocument()
  })

  it('não cadastra sem nome e data de nascimento', async () => {
    vi.mocked(patients.listPatients).mockResolvedValue([])
    vi.mocked(patients.createPatient).mockClear()
    renderizar()
    await screen.findByText(/Nenhum paciente cadastrado ainda/)
    fireEvent.submit(screen.getByRole('form', { name: 'Cadastrar novo paciente' }))
    expect(await screen.findByText('Preencha o nome e a data de nascimento.')).toBeInTheDocument()
    expect(patients.createPatient).not.toHaveBeenCalled()
  })
})
