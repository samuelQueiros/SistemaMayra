// Documento final (HTML completo) do relatório de um modelo de protocolo —
// o mesmo formato que gerarDocumentoLaudoHTML() do protocolo fixo produz:
// capa, cabeçalho do paciente, faixa do título, seções, "Sobre a
// profissional" e assinatura. Esse HTML vai para a pré-visualização, para
// POST /api/documents/{pdf,docx} e para Report.generated_text (PDF/Word do
// Histórico). Use só as classes que laudo_documento.py entende.

import type { Psychologist } from '../api/types'
import { CSS_LAUDO } from './css'
import { graficoDaEscala } from './grafico'
import { gerarCapa, prepararFoto, urlParaDataUri } from './imagens'
import {
  blocoDeTexto,
  dataBR,
  dataPorExtenso,
  esc,
  idadeCronologica,
  pontuarEscala,
  respostaEmTexto,
  textoAutomaticoDaSecao,
} from './texto'
import type { Identificacao, ModeloProtocolo, RespostasProtocolo, Secao } from './tipos'

export interface Perfil {
  nome: string
  bio: string
  credenciais: string[]
}

// Nome usado na assinatura do relatório — sempre o nome completo, mesmo que
// a conta (p.name) esteja cadastrada de forma abreviada — igual ao protocolo
// fixo (perfilProfissional() em formulario-novo-paciente.html).
const NOME_ASSINATURA = 'Mayra Vanessa Andrade da Cunha'

// Textos usados quando o perfil não tem bio/credenciais configuradas — os
// mesmos de perfilProfissional() no protocolo fixo, para os dois relatórios
// saírem iguais.
const BIO_PADRAO =
  "Este relatório foi elaborado por Mayra Vanessa Andrade da Cunha, Neuropsicopedagoga Clínica (CBO 2394-40) e Institucional (CBO 2394-45), com formação especializada em Análise do Comportamento Aplicada (ABA) e atuação profissional voltada ao desenvolvimento, aprendizagem e acompanhamento de crianças neurodivergentes. Possui mais de 25 anos de experiência profissional na área educacional e mais de 15 anos de atuação com crianças com Transtorno do Espectro Autista (TEA), integrando experiência educacional, conhecimento técnico e prática clínica neuropsicopedagógica na análise individualizada de cada caso."
const CREDENCIAIS_PADRAO = ['Neuropsicopedagoga Clínica – 2394-40', 'Especialista em Análise do Comportamento Aplicada - ABA', 'Especialista em Educação Inclusiva']

export function perfilDoProfissional(p: Psychologist): Perfil {
  const credenciais = (p.credenciais_assinatura ?? '')
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean)
  return {
    nome: NOME_ASSINATURA,
    bio: (p.bio_profissional ?? '').trim() || BIO_PADRAO,
    credenciais: credenciais.length ? credenciais : CREDENCIAIS_PADRAO,
  }
}

// Texto final de uma seção: o que a psicóloga editou ou, se não mexeu, o
// automático (modelo + respostas).
export function textoDaSecao(secao: Secao, modelo: ModeloProtocolo, r: RespostasProtocolo): string {
  const salvo = r.textos[secao.id]
  if (salvo?.editado) return salvo.valor
  return textoAutomaticoDaSecao(secao, r, { secoes: modelo.secoes })
}

export interface ImagensDoDocumento {
  capa: string | null
  cabecalho: string | null
  rodape: string | null
  fotoCabecalho: string | null
  fotos: Record<string, string[]> // secao -> fotos já preparadas
  graficos: Record<string, string | null> // secao -> gráfico da escala
}

function htmlDaSecao(secao: Secao, modelo: ModeloProtocolo, r: RespostasProtocolo, imagens: ImagensDoDocumento): string {
  const { relatorio } = secao
  const partes: string[] = [`<div class="faixa-topico">${esc(secao.titulo.toLocaleUpperCase('pt-BR'))}</div>`]

  if (secao.tipo === 'perguntas' && relatorio.formato !== 'so_texto') {
    const linhas = (secao.perguntas ?? [])
      .map((p) => [p.rotulo, respostaEmTexto(p, r)] as const)
      .filter(([, resposta]) => resposta)
    if (linhas.length && relatorio.formato === 'tabela') {
      partes.push(
        '<table class="tabela simples"><tr><th>Pergunta</th><th>Resposta</th></tr>' +
          linhas.map(([p, resp]) => `<tr><td>${esc(p)}</td><td>${esc(resp)}</td></tr>`).join('') +
          '</table>',
      )
    } else if (linhas.length) {
      partes.push(
        '<ul class="bullets">' +
          linhas.map(([p, resp]) => `<li><strong>${esc(p)}:</strong> ${esc(resp)}</li>`).join('') +
          '</ul>',
      )
    }
  }

  if (secao.tipo === 'escala' && secao.escala) {
    const escala = secao.escala
    const respostas = r.escalas[secao.id] ?? {}
    const resultado = pontuarEscala(escala, respostas)
    if (relatorio.formato !== 'so_texto' && resultado.respondidos) {
      const linhas = escala.itens
        .filter((i) => respostas[i.id] !== undefined)
        .map((i) => {
          const opcao = escala.opcoes[respostas[i.id]]
          return `<tr><td>${esc(i.rotulo)}</td><td>${esc(opcao?.rotulo ?? '')}</td><td>${esc(opcao?.valor ?? '')}</td></tr>`
        })
      partes.push(
        '<table class="tabela simples compacta"><tr><th>Item</th><th>Resposta</th><th>Pontos</th></tr>' +
          linhas.join('') +
          `<tr><th colspan="2">Total</th><th>${esc(resultado.pontuacao)} de ${esc(resultado.maxima)}</th></tr></table>`,
      )
      if (resultado.faixa) {
        partes.push(`<p class="centro"><strong>Classificação: ${esc(resultado.faixa.rotulo)}</strong></p>`)
      }
    }
    const grafico = imagens.graficos[secao.id]
    if (grafico) partes.push(`<div class="grafico"><img src="${grafico}" data-mm="160" style="width:160mm"></div>`)
  }

  const texto = textoDaSecao(secao, modelo, r)
  if (texto.trim()) partes.push(blocoDeTexto(texto))

  // As fotos não entram no meio do texto: vão todas para a galeria final.

  // Só o título, sem nada embaixo: a seção não entra.
  return partes.length > 1 ? partes.join('') : ''
}

// Partes comuns a todo relatório montado no navegador (modelos de
// protocolo e relatório por IA a partir de PDFs).

export function htmlCabecalhoPaciente(id: Identificacao, fotoCabecalho: string | null): string {
  const linhas = [
    ['Paciente', id.nome],
    ['D/N', dataBR(id.data_nascimento)],
    ['Idade cronológica', idadeCronologica(id.data_nascimento, id.data_relatorio)],
    ['Responsável', id.responsavel],
  ].filter(([, v]) => v)
  const caixa = '<div class="cab-box">' + linhas.map(([k, v]) => `<p>${esc(k)}: ${esc(v)}</p>`).join('') + '</div>'
  // Sem foto, o quadro fica centralizado na página.
  return fotoCabecalho
    ? '<table class="cab-paciente"><tr><td class="cab-foto">' +
        `<img src="${fotoCabecalho}" data-mm="42" style="width:42mm;height:52mm">` +
        `</td><td class="cab-espaco"></td><td class="cab-info">${caixa}</td></tr></table>`
    : `<table class="cab-paciente"><tr><td class="cab-info">${caixa}</td></tr></table>`
}

// Galeria "Registros dos atendimentos": todas as fotos numa página própria,
// depois da assinatura (modelo do relatório).
export function htmlGaleria(fotos: string[]): string {
  if (!fotos.length) return ''
  return (
    '<div class="quebra"></div><h2>REGISTROS DOS ATENDIMENTOS</h2><div class="galeria">' +
    fotos.map((src) => `<img src="${src}" data-mm="78" style="width:78mm;height:58.5mm">`).join('') +
    '</div>'
  )
}

export function htmlFaixaTitulo(titulo: string): string {
  return `<div class="faixa centro">${esc(titulo).replace(/\r?\n/g, '<br>')}</div>`
}

// "Sobre a profissional", local/data e assinatura, na sequência do texto
// (sem página em branco antes).
export function htmlFechamento(id: Identificacao, perfil: Perfil): string {
  const partes: string[] = []
  if (perfil.bio) {
    partes.push(
      `<div class="fechamento-texto"><h3><mark class="cinza">SOBRE A PROFISSIONAL RESPONSÁVEL</mark></h3><p>${esc(perfil.bio)}</p></div>`,
    )
  }
  // Atenciosamente, local/data e assinatura numa página só.
  const local = id.cidade.trim() ? `${id.cidade.trim()}, ` : ''
  partes.push(
    '<div class="bloco-assinatura">' +
      '<p class="direita" style="margin-top:6mm"><strong>Atenciosamente,</strong></p>' +
      `<p class="direita" style="margin-top:4mm"><strong>${esc(local + dataPorExtenso(id.data_relatorio))}.</strong></p>` +
      '<div class="linha-assinatura"></div>' +
      `<p class="centro compacto assinatura-nome">${esc(perfil.nome)}</p>` +
      perfil.credenciais
        .map((t) => `<p class="centro compacto"><mark class="cinza"><strong><span style="font-size:8.5pt">${esc(t)}</span></strong></mark></p>`)
        .join('') +
      '</div>',
  )
  return partes.join('')
}

// Documento HTML completo: estilos, moldura, capa, cabeçalho/rodapé de
// página e o corpo.
export function htmlDocumento(
  nomePaciente: string,
  imagens: { capa: string | null; cabecalho: string | null; rodape: string | null },
  corpo: string,
): string {
  const titulo = `Relatório - ${nomePaciente || 'Paciente'}`
  return (
    `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>${esc(titulo)}</title><style>${CSS_LAUDO}</style></head><body>` +
    '<div class="moldura"></div>' +
    (imagens.capa ? `<div class="capa"><img src="${imagens.capa}" data-mm="210" alt="Capa do relatório"></div>` : '') +
    (imagens.cabecalho ? `<div class="cabecalho-pagina"><img src="${imagens.cabecalho}" data-mm="19" alt=""></div>` : '') +
    (imagens.rodape ? `<div class="rodape-pagina"><img src="${imagens.rodape}" data-mm="99" alt=""></div>` : '') +
    `<main class="documento">${corpo}</main></body></html>`
  )
}

// Monta o HTML completo a partir de imagens já prontas (função pura —
// testável sem canvas).
export function montarDocumento(
  modelo: ModeloProtocolo,
  r: RespostasProtocolo,
  perfil: Perfil,
  imagens: ImagensDoDocumento,
): string {
  const id = r.identificacao
  const partes = [htmlCabecalhoPaciente(id, imagens.fotoCabecalho), htmlFaixaTitulo(modelo.titulo_relatorio)]
  for (const secao of modelo.secoes) {
    if (!secao.relatorio.mostrar) continue
    partes.push(htmlDaSecao(secao, modelo, r, imagens))
  }
  partes.push(htmlFechamento(id, perfil))
  partes.push(htmlGaleria(modelo.secoes.flatMap((secao) => imagens.fotos[secao.id] ?? [])))
  return htmlDocumento(id.nome, imagens, partes.join(''))
}

let imagensFixas: Promise<{ cabecalho: string | null; rodape: string | null }> | null = null
export function carregarImagensFixas() {
  if (!imagensFixas) {
    imagensFixas = Promise.all([
      urlParaDataUri('/laudo/cabecalho.jpg').catch(() => null),
      urlParaDataUri('/laudo/rodape.jpg').catch(() => null),
    ]).then(([cabecalho, rodape]) => ({ cabecalho, rodape }))
  }
  return imagensFixas
}

// Documento completo, com capa, gráficos e fotos (precisa de navegador).
export async function gerarDocumento(modelo: ModeloProtocolo, r: RespostasProtocolo, profissional: Psychologist): Promise<string> {
  const [fixas, capa] = await Promise.all([carregarImagensFixas(), gerarCapa(r.identificacao.nome, profissional, r.capa)])
  const fotos: Record<string, string[]> = {}
  const graficos: Record<string, string | null> = {}
  let primeiraFoto: string | null = null
  for (const secao of modelo.secoes) {
    if (secao.tipo === 'fotos') {
      const originais = (r.fotos[secao.id] ?? []).map((f) => f.src)
      primeiraFoto ??= originais[0] ?? null
      fotos[secao.id] = (await Promise.all(originais.map((src) => prepararFoto(src, 4 / 3)))).filter((s): s is string => !!s)
    }
    if (secao.tipo === 'escala' && secao.escala && secao.escala.grafico === 'barras' && secao.relatorio.mostrar) {
      graficos[secao.id] = graficoDaEscala(secao.titulo, secao.escala, r.escalas[secao.id])
    }
  }
  const fotoCabecalho = primeiraFoto ? await prepararFoto(primeiraFoto, 42 / 52) : null
  return montarDocumento(modelo, r, perfilDoProfissional(profissional), {
    capa,
    cabecalho: fixas.cabecalho,
    rodape: fixas.rodape,
    fotoCabecalho,
    fotos,
    graficos,
  })
}
