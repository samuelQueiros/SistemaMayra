import { describe, expect, it } from 'vitest'
import { montarDocumento } from './documento'
import { respostasVazias } from './modelo'
import { blocoDeTexto, idadeCronologica, pontuarEscala, textoAutomaticoDaSecao } from './texto'
import type { ModeloProtocolo, RespostasProtocolo } from './tipos'

const MODELO: ModeloProtocolo = {
  rule_type: 'protocolo',
  name: 'Teste',
  titulo_relatorio: 'PARECER\nDE TESTE',
  secoes: [
    {
      id: 'anamnese',
      titulo: 'Anamnese',
      tipo: 'perguntas',
      perguntas: [
        { id: 'queixa', rotulo: 'Queixa', tipo: 'texto_longo' },
        {
          id: 'parto',
          rotulo: 'Parto',
          tipo: 'multipla_escolha',
          opcoes: [{ rotulo: 'Normal', texto_relatorio: 'Nasceu de parto normal.' }, { rotulo: 'Cesárea' }],
        },
        { id: 'terapia', rotulo: 'Faz terapia?', tipo: 'sim_nao', detalhar_quando_sim: true, opcoes: [{ rotulo: 'Sim' }, { rotulo: 'Não' }] },
        { id: 'interna', rotulo: 'Pergunta sem resposta', tipo: 'texto_curto' },
      ],
      relatorio: { mostrar: true, formato: 'lista', texto_padrao: '{O} paciente {nome}, {idade}, tem queixa de {q:queixa}.' },
    },
    {
      id: 'snap',
      titulo: 'Escala',
      tipo: 'escala',
      escala: {
        itens: [
          { id: 'i1', rotulo: 'Item 1' },
          { id: 'i2', rotulo: 'Item 2' },
        ],
        opcoes: [
          { rotulo: 'Nunca', valor: 0 },
          { rotulo: 'Sempre', valor: 2 },
        ],
        faixas: [
          { min: 0, max: 1, rotulo: 'Sem indícios' },
          { min: 2, max: 4, rotulo: 'Significativo', texto_relatorio: 'Há indícios.' },
        ],
        grafico: 'barras',
      },
      relatorio: { mostrar: true, formato: 'lista', texto_padrao: 'Total {pontuacao} de {pontuacao_maxima}: {classificacao}. {trechos}' },
    },
    { id: 'interna', titulo: 'Uso interno', tipo: 'texto', relatorio: { mostrar: false, formato: 'so_texto', texto_padrao: 'Não aparece' } },
  ],
}

function respostas(): RespostasProtocolo {
  const r = respostasVazias({ nome: 'Ana Souza', data_nascimento: '2018-03-15', sexo: 'Feminino', data_relatorio: '2026-10-05', cidade: 'Gama – DF' })
  r.respostas = { queixa: 'desatenção', parto: 'Normal', terapia: 'Sim' }
  r.detalhes = { terapia: 'fonoaudiologia' }
  r.escalas = { snap: { i1: 1, i2: 1 } }
  return r
}

const ctx = { secoes: MODELO.secoes }

describe('texto do relatório', () => {
  it('troca variáveis de paciente, gênero e respostas e acrescenta os trechos das opções', () => {
    expect(textoAutomaticoDaSecao(MODELO.secoes[0], respostas(), ctx)).toBe(
      'A paciente Ana Souza, 08 anos e 06 meses, tem queixa de desatenção.\nNasceu de parto normal.',
    )
  })

  it('pontua a escala, acha a faixa e põe os trechos onde está {trechos}', () => {
    expect(pontuarEscala(MODELO.secoes[1].escala!, { i1: 1, i2: 1 })).toMatchObject({ pontuacao: 4, maxima: 4, respondidos: 2 })
    expect(textoAutomaticoDaSecao(MODELO.secoes[1], respostas(), ctx)).toBe('Total 4 de 4: Significativo. Há indícios.')
  })

  it('sem itens respondidos não há classificação', () => {
    expect(pontuarEscala(MODELO.secoes[1].escala!, {}).faixa).toBeNull()
  })

  it('mantém variáveis desconhecidas para a psicóloga ver o erro', () => {
    const secao = { ...MODELO.secoes[0], relatorio: { ...MODELO.secoes[0].relatorio, texto_padrao: 'X {inexistente} {q:nada}' } }
    expect(textoAutomaticoDaSecao(secao, respostas(), ctx)).toContain('{inexistente} {q:nada}')
  })

  it('marcação igual à do protocolo fixo', () => {
    expect(blocoDeTexto('Texto **forte** e ==cinza==\n• um\n• dois')).toBe(
      '<p class="recuo">Texto <strong>forte</strong> e <mark class="cinza"><strong>cinza</strong></mark></p><ul class="bullets"><li>um</li><li>dois</li></ul>',
    )
    expect(blocoDeTexto('<script>')).toContain('&lt;script&gt;')
  })

  it('idade cronológica no formato do cabeçalho', () => {
    expect(idadeCronologica('2018-03-15', '2026-10-05')).toBe('08 anos e 06 meses')
    expect(idadeCronologica('2026-09-01', '2026-10-05')).toBe('01 mês')
  })
})

describe('documento do relatório', () => {
  const perfil = { nome: 'Mayra', bio: 'Bio da profissional.', credenciais: ['Neuropsicopedagoga'] }
  const imagens = { capa: 'data:image/jpeg;base64,AA', cabecalho: null, rodape: null, fotoCabecalho: null, fotos: {}, graficos: {} }

  it('monta capa, cabeçalho, título, seções e assinatura com as classes do Word', () => {
    const html = montarDocumento(MODELO, respostas(), perfil, imagens)
    expect(html).toContain('<div class="capa"><img src="data:image/jpeg;base64,AA"')
    expect(html).toContain('<p>Paciente: Ana Souza</p>')
    expect(html).toContain('<div class="faixa centro">PARECER<br>DE TESTE</div>')
    expect(html).toContain('<div class="faixa-topico">ANAMNESE</div>')
    expect(html).toContain('<li><strong>Faz terapia?:</strong> Sim, fonoaudiologia</li>')
    expect(html).not.toContain('Pergunta sem resposta')
    expect(html).toContain('<th colspan="2">Total</th><th>4 de 4</th>')
    expect(html).toContain('Classificação: Significativo')
    expect(html).not.toContain('Uso interno')
    expect(html).toContain('Gama – DF, 5 de outubro de 2026.')
    expect(html).toContain('<p class="centro compacto assinatura-nome">Mayra</p>')
  })

  it('usa o texto editado pela psicóloga em vez do automático', () => {
    const r = respostas()
    r.textos = { anamnese: { valor: 'Texto escrito à mão.', editado: true } }
    const html = montarDocumento(MODELO, r, perfil, imagens)
    expect(html).toContain('Texto escrito à mão.')
    expect(html).not.toContain('tem queixa de')
  })

  it('no formato tabela, as respostas saem em tabela', () => {
    const modelo = { ...MODELO, secoes: [{ ...MODELO.secoes[0], relatorio: { ...MODELO.secoes[0].relatorio, formato: 'tabela' as const } }] }
    const html = montarDocumento(modelo, respostas(), perfil, imagens)
    expect(html).toContain('<table class="tabela simples"><tr><th>Pergunta</th><th>Resposta</th></tr>')
  })
})
