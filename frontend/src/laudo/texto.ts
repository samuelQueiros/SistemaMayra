// Texto do relatório dos modelos de protocolo: variáveis, trechos por opção
// e faixa, pontuação de escala e marcação (**negrito**, ==cinza==,
// !!amarelo!!, linhas com ✔/•). A marcação e as formas de gênero são cópia
// das do protocolo fixo (formulario-novo-paciente.html — marcacao(),
// blocoDeTexto(), formasGenero()), para o relatório sair igual.

import type { Escala, FaixaEscala, Identificacao, Pergunta, Resposta, RespostasProtocolo, Secao } from './tipos'

export const MESES_EXTENSO = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]

export function esc(s: unknown): string {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function marcacao(s: string): string {
  return esc(s)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/==(.+?)==/g, '<mark class="cinza"><strong>$1</strong></mark>')
    .replace(/!!(.+?)!!/g, '<mark class="amarelo"><strong>$1</strong></mark>')
}

export function blocoDeTexto(texto: string): string {
  let html = ''
  let lista: { tipo: string; itens: string[] } | null = null
  const fecharLista = () => {
    if (lista) html += `<ul class="${lista.tipo}">${lista.itens.join('')}</ul>`
    lista = null
  }
  for (const bruta of String(texto || '').split(/\r?\n/)) {
    const linha = bruta.trim()
    if (!linha) {
      fecharLista()
      continue
    }
    const m = linha.match(/^(✔|✓|•)\s*(.*)$/)
    if (m) {
      const tipo = m[1] === '•' ? 'bullets' : 'checks'
      if (!lista || lista.tipo !== tipo) {
        fecharLista()
        lista = { tipo, itens: [] }
      }
      lista.itens.push(`<li>${marcacao(m[2])}</li>`)
      continue
    }
    fecharLista()
    html += `<p class="recuo">${marcacao(linha)}</p>`
  }
  fecharLista()
  return html
}

export type FormasGenero = Record<'o' | 'O' | 'do' | 'ao' | 'pelo' | 'ele' | 'Ele' | 'e' | 'r', string>

export function formasGenero(sexo: string): FormasGenero {
  return sexo === 'Feminino'
    ? { o: 'a', O: 'A', do: 'da', ao: 'à', pelo: 'pela', ele: 'ela', Ele: 'Ela', e: 'a', r: 'a' }
    : { o: 'o', O: 'O', do: 'do', ao: 'ao', pelo: 'pelo', ele: 'ele', Ele: 'Ele', e: 'o', r: '' }
}

const doisDigitos = (n: number) => String(n).padStart(2, '0')

export function dataDeISO(iso: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '')
  return m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : null
}

export function dataBR(iso: string): string {
  const d = dataDeISO(iso)
  return d ? `${doisDigitos(d.getDate())}/${doisDigitos(d.getMonth() + 1)}/${d.getFullYear()}` : ''
}

export function dataPorExtenso(iso: string): string {
  const d = dataDeISO(iso) ?? new Date()
  return `${d.getDate()} de ${MESES_EXTENSO[d.getMonth()]} de ${d.getFullYear()}`
}

// "07 anos e 03 meses" — mesmo formato do cabeçalho do protocolo fixo.
export function idadeCronologica(nascimentoISO: string, referenciaISO: string): string {
  const nasc = dataDeISO(nascimentoISO)
  if (!nasc) return ''
  const ref = dataDeISO(referenciaISO) ?? new Date()
  let anos = ref.getFullYear() - nasc.getFullYear()
  let meses = ref.getMonth() - nasc.getMonth()
  if (ref.getDate() < nasc.getDate()) meses--
  if (meses < 0) {
    anos--
    meses += 12
  }
  if (anos < 0) return ''
  const partes: string[] = []
  if (anos > 0) partes.push(doisDigitos(anos) + (anos === 1 ? ' ano' : ' anos'))
  if (meses > 0 || !partes.length) partes.push(doisDigitos(meses) + (meses === 1 ? ' mês' : ' meses'))
  return partes.join(' e ')
}

// Resposta de uma pergunta em texto corrido (para listas, tabelas e {q:id}).
export function respostaEmTexto(pergunta: Pergunta, r: RespostasProtocolo): string {
  const valor: Resposta | undefined = r.respostas[pergunta.id]
  if (valor === undefined || valor === '' || (Array.isArray(valor) && !valor.length)) return ''
  if (Array.isArray(valor)) return valor.join(', ')
  if (pergunta.tipo === 'data') return dataBR(valor)
  if (pergunta.tipo === 'sim_nao' && valor === 'Sim' && pergunta.detalhar_quando_sim) {
    const detalhe = (r.detalhes[pergunta.id] || '').trim()
    return detalhe ? `Sim, ${detalhe}` : 'Sim'
  }
  return String(valor).trim()
}

export interface ResultadoEscala {
  pontuacao: number
  maxima: number
  respondidos: number
  faixa: FaixaEscala | null
}

export function pontuarEscala(escala: Escala, respostas: Record<string, number> | undefined): ResultadoEscala {
  let pontuacao = 0
  let respondidos = 0
  for (const item of escala.itens) {
    const indice = respostas?.[item.id]
    if (indice === undefined || indice === null) continue
    const opcao = escala.opcoes[indice]
    if (!opcao) continue
    pontuacao += opcao.valor
    respondidos++
  }
  const maiorValor = Math.max(...escala.opcoes.map((o) => o.valor))
  const maxima = maiorValor * escala.itens.length
  const faixa = respondidos ? escala.faixas.find((f) => pontuacao >= f.min && pontuacao <= f.max) ?? null : null
  return { pontuacao, maxima, respondidos, faixa }
}

const formatarNumero = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1).replace('.', ','))

// Trechos que entram no relatório pelas respostas escolhidas: o
// `texto_relatorio` de cada opção marcada e o da faixa da escala.
function trechosDaSecao(secao: Secao, r: RespostasProtocolo): string[] {
  const trechos: string[] = []
  for (const pergunta of secao.perguntas ?? []) {
    const valor = r.respostas[pergunta.id]
    const escolhidas = Array.isArray(valor) ? valor : valor ? [valor] : []
    for (const opcao of pergunta.opcoes ?? []) {
      if (opcao.texto_relatorio?.trim() && escolhidas.includes(opcao.rotulo)) trechos.push(opcao.texto_relatorio.trim())
    }
  }
  if (secao.escala) {
    const { faixa } = pontuarEscala(secao.escala, r.escalas[secao.id])
    if (faixa?.texto_relatorio?.trim()) trechos.push(faixa.texto_relatorio.trim())
  }
  return trechos
}

export interface ContextoTexto {
  secoes: Secao[]
}

// Troca as variáveis do texto. Variáveis desconhecidas ficam como estão,
// para a psicóloga ver o erro na pré-visualização.
export function resolverVariaveis(texto: string, secao: Secao, r: RespostasProtocolo, ctx: ContextoTexto): string {
  const id: Identificacao = r.identificacao
  const g = formasGenero(id.sexo)
  const perguntas = new Map<string, Pergunta>()
  ctx.secoes.forEach((s) => (s.perguntas ?? []).forEach((p) => perguntas.set(p.id, p)))
  const escala = secao.escala ? pontuarEscala(secao.escala, r.escalas[secao.id]) : null

  const simples: Record<string, string> = {
    nome: id.nome,
    idade: idadeCronologica(id.data_nascimento, id.data_relatorio),
    data_nascimento: dataBR(id.data_nascimento),
    responsavel: id.responsavel,
    cidade: id.cidade,
    data: dataPorExtenso(id.data_relatorio),
    pontuacao: escala && escala.respondidos ? formatarNumero(escala.pontuacao) : '',
    pontuacao_maxima: escala ? formatarNumero(escala.maxima) : '',
    classificacao: escala?.faixa?.rotulo ?? '',
    trechos: trechosDaSecao(secao, r).join('\n'),
    ...g,
  }
  return texto.replace(/\{([^{}]+)\}/g, (inteiro, nome: string) => {
    if (nome.startsWith('q:')) {
      const pergunta = perguntas.get(nome.slice(2))
      return pergunta ? respostaEmTexto(pergunta, r) : inteiro
    }
    return nome in simples ? simples[nome] : inteiro
  })
}

// Texto que aparece pré-preenchido em "Texto Do Relatório" de cada seção:
// o texto padrão do modelo com as variáveis trocadas, seguido dos trechos
// das opções/faixa escolhidas (a não ser que o texto padrão já tenha
// {trechos} em algum lugar).
export function textoAutomaticoDaSecao(secao: Secao, r: RespostasProtocolo, ctx: ContextoTexto): string {
  const padrao = secao.relatorio.texto_padrao ?? ''
  const resolvido = resolverVariaveis(padrao, secao, r, ctx).trim()
  if (padrao.includes('{trechos}')) return resolvido
  return [resolvido, ...trechosDaSecao(secao, r)].filter(Boolean).join('\n')
}

// Variáveis oferecidas no editor do modelo (botões que inserem no texto).
export const VARIAVEIS_GERAIS: { variavel: string; descricao: string }[] = [
  { variavel: '{nome}', descricao: 'Nome do paciente' },
  { variavel: '{idade}', descricao: 'Idade (anos e meses)' },
  { variavel: '{data_nascimento}', descricao: 'Data de nascimento' },
  { variavel: '{responsavel}', descricao: 'Responsável' },
  { variavel: '{O}', descricao: 'O/A (início de frase)' },
  { variavel: '{o}', descricao: 'o/a' },
  { variavel: '{ele}', descricao: 'ele/ela' },
  { variavel: '{do}', descricao: 'do/da' },
  { variavel: '{trechos}', descricao: 'Trechos das respostas escolhidas' },
]

export const VARIAVEIS_ESCALA: { variavel: string; descricao: string }[] = [
  { variavel: '{pontuacao}', descricao: 'Pontuação total' },
  { variavel: '{pontuacao_maxima}', descricao: 'Pontuação máxima' },
  { variavel: '{classificacao}', descricao: 'Classificação (faixa)' },
]
