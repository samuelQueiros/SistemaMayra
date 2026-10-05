import { describe, expect, it } from 'vitest'
import { montarDocumentoRelatorioIA } from './relatorioIA'
import type { RelatorioPorPdfs } from './relatorioIA'

const RELATORIO: RelatorioPorPdfs = {
  formularios: [
    { arquivo: 'mae.pdf', titulo: 'Anamnese Familiar', respondente: 'Mãe', data: '01/10/2026' },
    { arquivo: 'escola.pdf', titulo: 'Questionário Escolar', respondente: null, data: null },
  ],
  metodologia: 'Foram analisados **dois** formulários.',
  areas: [
    {
      titulo: 'Atenção E Comportamento',
      texto: 'Mãe e escola relatam desatenção.\n• Esquece materiais',
      fontes: ['Anamnese Familiar', 'Questionário Escolar'],
      grafico: { titulo: 'SNAP-IV', rotulos: ['Desatenção', 'Hiperatividade'], valores: [7, 3], maximo: 9, regua: 'Itens marcados como Bastante ou Demais.' },
    },
    { titulo: 'Comunicação', texto: 'Sem queixas.', fontes: ['Anamnese Familiar'], grafico: null },
    { titulo: '', texto: '', fontes: [], grafico: null },
  ],
  consideracoes_finais: 'Síntese final.',
  sugestoes_intervencao: '• Rotina visual\n• Pausas curtas',
}

const identificacao = { nome: 'Ana', data_nascimento: '2018-03-15', sexo: 'Feminino', responsavel: 'Mãe', cidade: 'Gama – DF', data_relatorio: '2026-10-05' }
const perfil = { nome: 'Mayra', bio: 'Bio.', credenciais: ['Neuropsicopedagoga'] }

describe('documento do relatório por IA', () => {
  it('monta metodologia, áreas com fontes e gráfico, considerações, sugestões e assinatura', () => {
    const html = montarDocumentoRelatorioIA(RELATORIO, identificacao, 'RELATÓRIO\nTESTE', perfil, {
      capa: 'data:image/jpeg;base64,AA',
      cabecalho: null,
      rodape: null,
      graficos: ['data:image/png;base64,GG', null, null],
    })
    expect(html).toContain('<div class="capa">')
    expect(html).toContain('<p>Paciente: Ana</p>')
    expect(html).toContain('<div class="faixa centro">RELATÓRIO<br>TESTE</div>')
    expect(html).toContain('<div class="faixa-topico">METODOLOGIA</div><p class="recuo">Foram analisados <strong>dois</strong> formulários.</p>')
    expect(html).toContain('<li><strong>Anamnese Familiar</strong> — Mãe — 01/10/2026</li><li><strong>Questionário Escolar</strong></li>')
    expect(html).toContain('<div class="faixa-topico">ATENÇÃO E COMPORTAMENTO</div>')
    expect(html).toContain('<ul class="bullets"><li>Esquece materiais</li></ul>')
    expect(html).toContain('<div class="grafico"><img src="data:image/png;base64,GG"')
    expect(html).toContain('Itens marcados como Bastante ou Demais.')
    expect(html).toContain('<strong>Fontes:</strong> Anamnese Familiar; Questionário Escolar')
    expect(html).toContain('<div class="faixa-topico">COMUNICAÇÃO</div>')
    expect(html.match(/faixa-topico/g)).toHaveLength(4) // metodologia + 2 áreas; a vazia não entra
    expect(html).toContain('<h3><mark class="cinza">Considerações Finais</mark></h3><p class="recuo">Síntese final.</p>')
    expect(html).toContain('<li>Pausas curtas</li>')
    expect(html).toContain('Gama – DF, 5 de outubro de 2026.')
    expect(html).toContain('assinatura-nome">Mayra</p>')
  })

  it('sem imagem de gráfico (ou sem dados), não põe gráfico nem a régua', () => {
    const html = montarDocumentoRelatorioIA(RELATORIO, identificacao, '', perfil, { capa: null, cabecalho: null, rodape: null, graficos: [null, null, null] })
    expect(html).not.toContain('class="grafico"')
    expect(html).not.toContain('Itens marcados como')
    expect(html).toContain('RELATÓRIO DE AVALIAÇÃO<br>ANÁLISE DOS FORMULÁRIOS')
  })
})
