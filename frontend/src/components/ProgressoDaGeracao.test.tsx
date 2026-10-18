import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { ProgressoDaGeracao } from './ProgressoDaGeracao'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

const valor = () => Number(screen.getByRole('progressbar').getAttribute('aria-valuenow'))

it('anda sozinha até o fim da etapa sem passar dele e conta o tempo', () => {
  const { rerender } = render(<ProgressoDaGeracao alvo={10} teto={40} mensagem="Lendo documento 1 de 2…" />)
  expect(valor()).toBe(10)
  act(() => vi.advanceTimersByTime(60_000))
  expect(valor()).toBeGreaterThan(30)
  expect(valor()).toBeLessThan(40)
  expect(screen.getByText(/Tempo decorrido: 1 min 00 s/)).toBeInTheDocument()

  rerender(<ProgressoDaGeracao alvo={70} teto={95} mensagem="Preenchendo o protocolo…" />)
  expect(valor()).toBe(70)
})
