import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import * as reports from '../api/reports'
import Logs from './Logs'

vi.mock('../api/patients', () => ({
  listPatients: vi.fn().mockResolvedValue([{ id: 'p1', name: 'Ana Souza', birth_date: '2018-03-15', notes: null, sex: null, school_info: null }]),
}))
vi.mock('../api/reports', () => ({
  listAllLogs: vi.fn().mockResolvedValue([
    {
      id: 'l1',
      field: 'classification_override',
      old_value: null,
      new_value: 'Leve',
      created_at: '2026-10-05T10:00:00',
      psychologist_name: 'Mayra',
      report_id: 'r1',
      report_created_at: '2026-10-01T10:00:00',
      patient_id: 'p1',
      patient_name: 'Ana Souza',
      template_name: 'Avaliação',
    },
  ]),
}))

describe('Registro de atividades', () => {
  it('lista as edições com paciente, relatório e o que mudou, e filtra por paciente', async () => {
    render(
      <MemoryRouter initialEntries={['/logs']}>
        <Logs />
      </MemoryRouter>,
    )
    expect(await screen.findByRole('link', { name: 'Ana Souza' })).toHaveAttribute('href', '/pacientes/p1/historico')
    expect(screen.getByText('Classificação:')).toBeInTheDocument()
    expect(screen.getByText(/"\(vazio\)" → "Leve"/)).toBeInTheDocument()
    expect(reports.listAllLogs).toHaveBeenLastCalledWith(undefined)

    await screen.findByRole('option', { name: 'Ana Souza' })
    fireEvent.change(screen.getByLabelText('Paciente'), { target: { value: 'p1' } })
    await vi.waitFor(() => expect(reports.listAllLogs).toHaveBeenLastCalledWith('p1'))
  })
})
