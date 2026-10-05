// Construção e manutenção de modelos de protocolo no editor (Configurações)
// e respostas iniciais de um atendimento.

import type { Identificacao, ModeloProtocolo, Pergunta, RespostasProtocolo, Secao, TipoPergunta, TipoSecao } from './tipos'

export function slug(texto: string, prefixo: string): string {
  const base = texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 30)
  return base || prefixo
}

// Identificador único dentro do modelo (o backend exige ids únicos; as
// respostas e as variáveis {q:id} usam o id, então ele não muda depois de
// salvo).
export function idUnico(base: string, usados: Set<string>): string {
  let id = base
  let n = 2
  while (usados.has(id)) id = `${base}_${n++}`.slice(0, 40)
  return id
}

export function idsDoModelo(modelo: ModeloProtocolo): Set<string> {
  const ids = new Set<string>()
  for (const s of modelo.secoes) {
    ids.add(s.id)
    s.perguntas?.forEach((p) => ids.add(p.id))
    s.escala?.itens.forEach((i) => ids.add(i.id))
  }
  return ids
}

export const ROTULOS_TIPO_PERGUNTA: Record<TipoPergunta, string> = {
  texto_curto: 'Texto curto',
  texto_longo: 'Texto longo',
  sim_nao: 'Sim / Não',
  multipla_escolha: 'Múltipla escolha (uma opção)',
  caixas: 'Caixas de seleção (várias opções)',
  data: 'Data',
  numero: 'Número',
}

export const ROTULOS_TIPO_SECAO: Record<TipoSecao, string> = {
  perguntas: 'Perguntas',
  escala: 'Escala pontuada',
  fotos: 'Fotos',
  texto: 'Texto livre',
}

export function novaPergunta(usados: Set<string>, tipo: TipoPergunta = 'texto_curto'): Pergunta {
  return { id: idUnico('pergunta', usados), rotulo: '', tipo, opcoes: opcoesPadrao(tipo), obrigatoria: false }
}

export function opcoesPadrao(tipo: TipoPergunta) {
  if (tipo === 'sim_nao') return [{ rotulo: 'Sim', texto_relatorio: '' }, { rotulo: 'Não', texto_relatorio: '' }]
  if (tipo === 'multipla_escolha' || tipo === 'caixas') return [{ rotulo: 'Opção 1', texto_relatorio: '' }]
  return null
}

export function novaSecao(tipo: TipoSecao, usados: Set<string>): Secao {
  const id = idUnico(`secao_${usados.size + 1}`, usados)
  usados.add(id)
  const base: Secao = {
    id,
    titulo: ROTULOS_TIPO_SECAO[tipo],
    tipo,
    relatorio: { mostrar: true, formato: 'lista', texto_padrao: '' },
  }
  if (tipo === 'perguntas') base.perguntas = [novaPergunta(usados)]
  if (tipo === 'escala') {
    base.titulo = 'Escala'
    base.escala = {
      itens: [{ id: idUnico('item_1', usados), rotulo: '' }],
      opcoes: [
        { rotulo: 'Nunca', valor: 0 },
        { rotulo: 'Às vezes', valor: 1 },
        { rotulo: 'Frequentemente', valor: 2 },
        { rotulo: 'Sempre', valor: 3 },
      ],
      faixas: [],
      grafico: 'barras',
    }
    base.relatorio.formato = 'tabela'
    base.relatorio.texto_padrao = '{O} paciente obteve {pontuacao} pontos de {pontuacao_maxima}, classificação **{classificacao}**.'
  }
  if (tipo === 'texto') base.relatorio.formato = 'so_texto'
  return base
}

export function novoModelo(): ModeloProtocolo {
  const usados = new Set<string>()
  return {
    rule_type: 'protocolo',
    name: '',
    descricao: '',
    titulo_relatorio: 'RELATÓRIO DE AVALIAÇÃO',
    secoes: [novaSecao('perguntas', usados)],
  }
}

const hojeISO = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function respostasVazias(identificacao?: Partial<Identificacao>): RespostasProtocolo {
  return {
    identificacao: {
      nome: '',
      data_nascimento: '',
      sexo: '',
      responsavel: '',
      cidade: '',
      data_relatorio: hojeISO(),
      ...identificacao,
    },
    respostas: {},
    detalhes: {},
    escalas: {},
    textos: {},
    fotos: {},
    capa: null,
  }
}

// Respostas fictícias para a pré-visualização do relatório no editor.
export function respostasDeExemplo(modelo: ModeloProtocolo): RespostasProtocolo {
  const r = respostasVazias({
    nome: 'Paciente De Exemplo',
    data_nascimento: '2018-03-15',
    sexo: 'Feminino',
    responsavel: 'Mãe',
    cidade: 'Cidade',
  })
  for (const secao of modelo.secoes) {
    for (const p of secao.perguntas ?? []) {
      if (p.tipo === 'sim_nao') r.respostas[p.id] = 'Sim'
      else if (p.tipo === 'multipla_escolha') r.respostas[p.id] = p.opcoes?.[0]?.rotulo ?? ''
      else if (p.tipo === 'caixas') r.respostas[p.id] = (p.opcoes ?? []).slice(0, 2).map((o) => o.rotulo)
      else if (p.tipo === 'data') r.respostas[p.id] = '2026-01-10'
      else if (p.tipo === 'numero') r.respostas[p.id] = '3'
      else r.respostas[p.id] = `Resposta de exemplo para "${p.rotulo || 'pergunta'}"`
      if (p.detalhar_quando_sim) r.detalhes[p.id] = 'detalhe de exemplo'
    }
    if (secao.escala) {
      const ultima = secao.escala.opcoes.length - 1
      r.escalas[secao.id] = Object.fromEntries(secao.escala.itens.map((item, i) => [item.id, i % (ultima + 1)]))
    }
  }
  return r
}

// Seção "preenchida" para o progresso: alguma resposta, item, foto ou texto.
export function secaoPreenchida(secao: Secao, r: RespostasProtocolo): boolean {
  if (secao.tipo === 'perguntas') {
    return (secao.perguntas ?? []).some((p) => {
      const v = r.respostas[p.id]
      return Array.isArray(v) ? v.length > 0 : !!String(v ?? '').trim()
    })
  }
  if (secao.tipo === 'escala') return Object.keys(r.escalas[secao.id] ?? {}).length > 0
  if (secao.tipo === 'fotos') return (r.fotos[secao.id] ?? []).length > 0
  return !!r.textos[secao.id]?.valor?.trim()
}

export function essenciaisEmBranco(secao: Secao, r: RespostasProtocolo): Pergunta[] {
  return (secao.perguntas ?? []).filter((p) => {
    if (!p.obrigatoria) return false
    const v = r.respostas[p.id]
    return Array.isArray(v) ? !v.length : !String(v ?? '').trim()
  })
}
