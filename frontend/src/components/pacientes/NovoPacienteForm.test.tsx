import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import * as api from '../../api/patients'
import { NovoPacienteForm } from './NovoPacienteForm'

vi.mock('../../api/patients', () => ({ createPatient: vi.fn(), uploadPatientPhoto: vi.fn() }))

it('cadastra dados básicos e tenta reenviar só as fotos pendentes sem duplicar o paciente', async () => {
  const paciente = { id: 'p1', name: 'Ana', birth_date: '2020-01-01', sex: null, school_info: 'Escola A', notes: 'Observação' }
  vi.mocked(api.createPatient).mockResolvedValue(paciente)
  vi.mocked(api.uploadPatientPhoto).mockResolvedValueOnce({ id: 'foto1' } as never).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ id: 'foto2' } as never)
  const onCriado = vi.fn()
  render(<NovoPacienteForm onCriado={onCriado} />)
  fireEvent.change(screen.getByLabelText(/Nome do paciente/), { target: { value: 'Ana' } })
  fireEvent.change(screen.getByLabelText(/Data de nascimento/), { target: { value: '2020-01-01' } })
  fireEvent.change(screen.getByLabelText(/Escola/), { target: { value: 'Escola A' } })
  fireEvent.change(screen.getByLabelText(/Informações básicas/), { target: { value: 'Observação' } })
  const fotos = [new File(['1'], 'a.png', { type: 'image/png' }), new File(['2'], 'b.png', { type: 'image/png' })]
  fireEvent.change(screen.getByLabelText(/Fotos do paciente/), { target: { files: fotos } })
  fireEvent.click(screen.getByRole('button', { name: 'Cadastrar paciente' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Enviar fotos pendentes' })).toBeEnabled())
  expect(onCriado).not.toHaveBeenCalled()
  expect(api.createPatient).toHaveBeenCalledWith(expect.objectContaining({ school_info: 'Escola A', notes: 'Observação' }))
  fireEvent.click(screen.getByRole('button', { name: 'Enviar fotos pendentes' }))
  await waitFor(() => expect(onCriado).toHaveBeenCalledWith(paciente))
  expect(api.createPatient).toHaveBeenCalledTimes(1)
  expect(api.uploadPatientPhoto).toHaveBeenCalledTimes(3)
  expect(api.uploadPatientPhoto).toHaveBeenLastCalledWith('p1', fotos[1])
})
