// Relatório por IA a partir de PDFs de respostas de formulários (Google
// Forms): tipos (espelham backend/app/services/ai/schemas.py::
// RelatorioPorPdfs) e montagem do documento no padrão do sistema.

import type { Psychologist } from '../api/types'
import {
  carregarImagensFixas,
  htmlCabecalhoPaciente,
  htmlDocumento,
  htmlFaixaTitulo,
  htmlFechamento,
  perfilDoProfissional,
} from './documento'
import type { Perfil } from './documento'
import { graficoDeBarras } from './grafico'
import { gerarCapa } from './imagens'
import { blocoDeTexto, esc } from './texto'
import type { CapaConfig, Identificacao } from './tipos'

export interface FormularioLido {
  arquivo: string
  titulo: string
  respondente?: string | null
  data?: string | null
}

export interface GraficoDaArea {
  titulo: string
  rotulos: string[]
  valores: number[]
  maximo?: number | null
  regua: string
}

export interface AreaDoRelatorio {
  titulo: string
  texto: string
  fontes: string[]
  grafico?: GraficoDaArea | null
}

export interface RelatorioPorPdfs {
  formularios: FormularioLido[]
  metodologia: string
  areas: AreaDoRelatorio[]
  consideracoes_finais: string
  sugestoes_intervencao: string
}

// Ajustes da tela de revisão guardados junto do laudo (answers_json.extras).
export interface ExtrasRelatorioIA {
  titulo: string
  cidade: string
  data_relatorio: string // AAAA-MM-DD
  responsavel: string
  capa: { src: string; config: CapaConfig } | null
}

export const TITULO_PADRAO = 'RELATÓRIO DE AVALIAÇÃO\nANÁLISE DOS FORMULÁRIOS'

const temGrafico = (g: GraficoDaArea | null | undefined): g is GraficoDaArea =>
  !!g && g.rotulos.length > 0 && g.rotulos.length === g.valores.length

export function montarDocumentoRelatorioIA(
  relatorio: RelatorioPorPdfs,
  identificacao: Identificacao,
  titulo: string,
  perfil: Perfil,
  imagens: { capa: string | null; cabecalho: string | null; rodape: string | null; graficos: (string | null)[] },
): string {
  const partes = [htmlCabecalhoPaciente(identificacao, null), htmlFaixaTitulo(titulo || TITULO_PADRAO)]

  partes.push('<div class="faixa-topico">METODOLOGIA</div>')
  partes.push(blocoDeTexto(relatorio.metodologia))
  if (relatorio.formularios.length) {
    const linha = (f: FormularioLido) =>
      [`<strong>${esc(f.titulo || f.arquivo)}</strong>`, f.respondente && esc(f.respondente), f.data && esc(f.data)].filter(Boolean).join(' — ')
    partes.push('<ul class="bullets">' + relatorio.formularios.map((f) => `<li>${linha(f)}</li>`).join('') + '</ul>')
  }

  relatorio.areas.forEach((area, i) => {
    if (!area.titulo.trim() && !area.texto.trim()) return
    partes.push(`<div class="faixa-topico">${esc(area.titulo.toLocaleUpperCase('pt-BR'))}</div>`)
    partes.push(blocoDeTexto(area.texto))
    const grafico = imagens.graficos[i]
    if (grafico && temGrafico(area.grafico)) {
      partes.push(`<div class="grafico"><img src="${grafico}" data-mm="150" style="width:150mm"></div>`)
      if (area.grafico.regua.trim()) partes.push(`<p class="centro"><span style="font-size:8.5pt">${esc(area.grafico.regua)}</span></p>`)
    }
    if (area.fontes.length) partes.push(`<p><span style="font-size:8.5pt"><strong>Fontes:</strong> ${esc(area.fontes.join('; '))}</span></p>`)
  })

  if (relatorio.consideracoes_finais.trim()) {
    partes.push('<h3><mark class="cinza">Considerações Finais</mark></h3>')
    partes.push(blocoDeTexto(relatorio.consideracoes_finais))
  }
  if (relatorio.sugestoes_intervencao.trim()) {
    partes.push('<h3><mark class="cinza">Sugestões De Intervenção</mark></h3>')
    partes.push(blocoDeTexto(relatorio.sugestoes_intervencao))
  }
  partes.push(htmlFechamento(identificacao, perfil))
  return htmlDocumento(identificacao.nome, imagens, partes.join(''))
}

export async function gerarDocumentoRelatorioIA(
  relatorio: RelatorioPorPdfs,
  identificacao: Identificacao,
  extras: ExtrasRelatorioIA,
  profissional: Psychologist,
): Promise<string> {
  const [fixas, capa] = await Promise.all([carregarImagensFixas(), gerarCapa(identificacao.nome, profissional, extras.capa)])
  const graficos = relatorio.areas.map((a) =>
    temGrafico(a.grafico) ? graficoDeBarras(a.grafico.titulo || a.titulo, a.grafico.rotulos, a.grafico.valores.map(Number), a.grafico.maximo) : null,
  )
  return montarDocumentoRelatorioIA(relatorio, identificacao, extras.titulo, perfilDoProfissional(profissional), {
    capa,
    cabecalho: fixas.cabecalho,
    rodape: fixas.rodape,
    graficos,
  })
}
