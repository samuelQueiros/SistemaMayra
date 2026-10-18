import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { ENCAMINHAMENTOS, textoDaHipotese, todasAsHipoteses } from './hipotesesCid'

const formulario = readFileSync('public/formulario-novo-paciente.html', 'utf-8')

describe('hipóteses e encaminhamentos do Laudo Por IA', () => {
  it('usam as mesmas caixas (id e texto) do formulário padrão', () => {
    for (const h of todasAsHipoteses()) {
      expect(formulario).toContain(`id="${h.id}" value="${textoDaHipotese(h)}"`)
    }
    for (const e of ENCAMINHAMENTOS) {
      expect(formulario).toContain(`class="encaminhamento" id="${e.id}" value="${e.rotulo}"`)
    }
  })

  it('trazem as 28 condições da tabela NeuroPP (mais o TPAC)', () => {
    const condicoes = todasAsHipoteses().filter((h) => h.id !== 'hip_tpac')
    expect(condicoes).toHaveLength(28)
    expect(new Set(condicoes.map((h) => h.cid11)).size).toBe(28)
  })

  it('formatam o CID como no relatório', () => {
    const [tea] = todasAsHipoteses()
    expect(textoDaHipotese(tea.subtipos[0])).toBe('TEA sem deficiência intelectual e linguagem funcional preservada (CID-11 6A02.0 / CID-10 F84.x)')
    expect(textoDaHipotese({ id: 'x', rotulo: 'TPAC' })).toBe('TPAC')
  })
})
