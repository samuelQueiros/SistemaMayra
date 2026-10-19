import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { expect, it, vi } from 'vitest'
import { DadosDaProfissional } from './DadosDaProfissional'
import type { CatalogoDoProtocolo } from '../api/laudoIA'

const op = (lista: string[]) => lista.map((v) => ({ valor: v, rotulo: v }))
const catalogo: CatalogoDoProtocolo = {
  contexto: '',
  campos: [
    { id: 'desfralde', tipo: 'opcao', opcoes: op(['Controle Total', 'Em Processo']) },
    { id: 'desfraldeAno', tipo: 'opcao', opcoes: op(['2 anos', '3 anos']) },
    { id: 'desfraldeMes', tipo: 'opcao', opcoes: op(['0 meses', '6 meses']) },
    { id: 'anoEscolar', tipo: 'opcao', opcoes: op(['1º Ano', '2º Ano']) },
    { id: 'hab_status_0', tipo: 'opcao', opcoes: op(['Satisfatório', 'Em Desenvolvimento']) },
  ],
  habilidadesPorAno: { '1º Ano': ['Leitura De Palavras'], '2º Ano': ['Leitura De Textos Curtos', 'Escrita De Frases'] },
}

function Tela({ aoMudar }: { aoMudar: (v: Record<string, string>) => void }) {
  const [valores, setValores] = useState<Record<string, string>>({})
  return <DadosDaProfissional catalogo={catalogo} valores={valores} onChange={(v) => { setValores(v); aoMudar(v) }} />
}

it('a psicóloga escolhe desfralde, ano escolar e o desempenho em cada habilidade do ano', () => {
  const aoMudar = vi.fn()
  render(<Tela aoMudar={aoMudar} />)
  // A idade só aparece quando a situação tem idade.
  expect(screen.queryByLabelText('Idade do desfralde (anos)')).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Situação'), { target: { value: 'Controle Total' } })
  fireEvent.change(screen.getByLabelText('Idade do desfralde (anos)'), { target: { value: '3 anos' } })
  fireEvent.change(screen.getByLabelText('Idade do desfralde (meses)'), { target: { value: '6 meses' } })
  fireEvent.change(screen.getByLabelText('Ano escolar'), { target: { value: '2º Ano' } })
  expect(screen.getByLabelText('Escrita De Frases')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Leitura De Textos Curtos'), { target: { value: 'Em Desenvolvimento' } })
  expect(aoMudar).toHaveBeenLastCalledWith({
    desfralde: 'Controle Total', desfraldeAno: '3 anos', desfraldeMes: '6 meses', anoEscolar: '2º Ano', hab_status_0: 'Em Desenvolvimento',
  })

  // Outro ano escolar limpa as habilidades; situação sem idade limpa a idade.
  fireEvent.change(screen.getByLabelText('Ano escolar'), { target: { value: '1º Ano' } })
  fireEvent.change(screen.getByLabelText('Situação'), { target: { value: 'Em Processo' } })
  expect(aoMudar).toHaveBeenLastCalledWith({ desfralde: 'Em Processo', anoEscolar: '1º Ano' })
  expect(screen.getByLabelText('Leitura De Palavras')).toBeInTheDocument()
})
