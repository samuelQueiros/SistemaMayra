import { describe, expect, it } from 'vitest'
import { idadeParaExibicao, nomeParaExibicao } from './exibicao'

describe('nomeParaExibicao', () => {
  it('mostra nomes em caixa alta como nome, com partículas minúsculas', () => {
    expect(nomeParaExibicao('ANA DE SOUZA')).toBe('Ana de Souza')
    expect(nomeParaExibicao('JOÃO PEDRO DOS SANTOS-LIMA')).toBe('João Pedro dos Santos-Lima')
  })

  it('não mexe em nomes já digitados com maiúsculas e minúsculas', () => {
    expect(nomeParaExibicao('Ana Souza')).toBe('Ana Souza')
    expect(nomeParaExibicao('maria McDonald')).toBe('maria McDonald')
  })
})

describe('idadeParaExibicao', () => {
  const hoje = new Date(2026, 9, 14)
  it('anos, e meses só para crianças pequenas', () => {
    expect(idadeParaExibicao('2018-03-15', hoje)).toBe('8 anos')
    expect(idadeParaExibicao('2025-07-02', hoje)).toBe('1 ano e 3 meses')
    expect(idadeParaExibicao('2026-02-20', hoje)).toBe('7 meses')
  })

  it('data vazia ou futura não mostra idade', () => {
    expect(idadeParaExibicao('', hoje)).toBe('')
    expect(idadeParaExibicao('2027-01-01', hoje)).toBe('')
  })
})
