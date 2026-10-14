// Imagens do relatório: capa (arte + nome do paciente), imagens fixas
// (cabeçalho/rodapé), fotos e gráficos. Tudo vira data: URI — o gerador de
// PDF do backend só aceita imagens embutidas (ver
// laudo_documento._buscador_somente_data_uri). A capa é a mesma lógica de
// gerarCapaRelatorio() do protocolo fixo.

import { fetchCapaUrl } from '../api/auth'
import type { Psychologist } from '../api/types'
import type { CapaConfig } from './tipos'

export const CAPA_ARTE_URL = '/capa-relatorio.jpg'
const CAPA_FONTE_URL = '/fonts/Fredoka.ttf'
const CAPA_LARGURA_PX = 2480
const CAPA_ALTURA_PX = 3508
export const CAPA_CONFIG_SISTEMA: CapaConfig = {
  escreverNome: true,
  faixa: { x: 0.285, y: 0.4287, largura: 0.466, altura: 0.039 },
  corNome: '#ffffff',
}

export function carregarImagem(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

export async function urlParaDataUri(url: string): Promise<string> {
  const blob = await (await fetch(url)).blob()
  return arquivoParaDataUri(blob)
}

export function arquivoParaDataUri(arquivo: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const leitor = new FileReader()
    leitor.onload = () => resolve(String(leitor.result))
    leitor.onerror = reject
    leitor.readAsDataURL(arquivo)
  })
}

// Desenha a arte preenchendo a folha A4 inteira (recorta ao centro se a
// proporção for outra, nunca estica).
export function desenharArteA4(ctx: CanvasRenderingContext2D, arte: HTMLImageElement, largura: number, altura: number) {
  const escala = Math.max(largura / arte.naturalWidth, altura / arte.naturalHeight)
  const w = arte.naturalWidth * escala
  const h = arte.naturalHeight * escala
  ctx.drawImage(arte, (largura - w) / 2, (altura - h) / 2, w, h)
}

// Reduz a imagem enviada para uma folha A4 (capa só deste relatório).
export async function prepararCapaA4(arquivo: File): Promise<{ src: string; foraDoA4: boolean }> {
  const arte = await carregarImagem(await arquivoParaDataUri(arquivo))
  const canvas = document.createElement('canvas')
  canvas.width = CAPA_LARGURA_PX
  canvas.height = CAPA_ALTURA_PX
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.imageSmoothingQuality = 'high'
  desenharArteA4(ctx, arte, canvas.width, canvas.height)
  const a4 = 210 / 297
  const foraDoA4 = Math.abs(arte.naturalWidth / arte.naturalHeight - a4) / a4 > 0.03
  return { src: canvas.toDataURL('image/jpeg', 0.88), foraDoA4 }
}

let fonteDaCapa: Promise<string> | null = null
function carregarFonteDaCapa(): Promise<string> {
  if (!fonteDaCapa) {
    fonteDaCapa = (async () => {
      try {
        const f = new FontFace('FredokaCapa', `url(${CAPA_FONTE_URL})`, { weight: '300 700' })
        await f.load()
        document.fonts.add(f)
        return '"FredokaCapa",'
      } catch {
        return ''
      }
    })()
  }
  return fonteDaCapa
}

// Maior fonte em que o nome cabe na faixa: uma linha se der; senão, duas
// linhas equilibradas.
function ajustarNomeNaFaixa(ctx: CanvasRenderingContext2D, nome: string, larguraMax: number, alturaMax: number, familia: string) {
  const fonte = (t: number) => `600 ${t}px ${familia}Arial,Helvetica,sans-serif`
  const largura = (texto: string, t: number) => {
    ctx.font = fonte(t)
    return ctx.measureText(texto).width
  }
  for (let t = Math.round(alturaMax * 0.72); t >= Math.round(alturaMax * 0.5); t -= 2) {
    if (largura(nome, t) <= larguraMax) return { tamanho: t, linhas: [nome], fonte: fonte(t) }
  }
  const palavras = nome.split(' ')
  let melhor = [nome]
  if (palavras.length > 1) {
    let menor = Infinity
    for (let i = 1; i < palavras.length; i++) {
      const linhas = [palavras.slice(0, i).join(' '), palavras.slice(i).join(' ')]
      const maior = Math.max(largura(linhas[0], 100), largura(linhas[1], 100))
      if (maior < menor) {
        menor = maior
        melhor = linhas
      }
    }
  }
  let t = Math.floor(alturaMax / (melhor.length * 1.08))
  while (t > 12 && Math.max(...melhor.map((l) => largura(l, t))) > larguraMax) t -= 1
  return { tamanho: t, linhas: melhor, fonte: fonte(t) }
}

let capaDoPerfil: { chave: string; url: string | null } | null = null
async function urlDaCapaDoPerfil(perfil: Psychologist): Promise<string | null> {
  if (!perfil.tem_capa_personalizada) return null
  const chave = perfil.id
  if (capaDoPerfil?.chave === chave) return capaDoPerfil.url
  let url: string | null = null
  try {
    url = await fetchCapaUrl()
  } catch {
    url = null
  }
  capaDoPerfil = { chave, url }
  return url
}

// Capa do relatório: capa só deste relatório → capa padrão da psicóloga
// (Configurações) → arte do sistema. O nome entra se a configuração pedir.
export async function gerarCapa(
  nomePaciente: string,
  perfil: Psychologist,
  capaDoRelatorio: { src: string; config: CapaConfig } | null,
): Promise<string> {
  let arteUrl = CAPA_ARTE_URL
  let config: CapaConfig = perfil.capa_config ?? CAPA_CONFIG_SISTEMA
  if (capaDoRelatorio?.src) {
    arteUrl = capaDoRelatorio.src
    config = capaDoRelatorio.config
  } else {
    const doPerfil = await urlDaCapaDoPerfil(perfil)
    if (doPerfil) {
      arteUrl = doPerfil
      config = perfil.capa_config ?? { ...CAPA_CONFIG_SISTEMA, escreverNome: false }
    }
  }
  const nome = nomePaciente.trim().replace(/\s+/g, ' ').toLocaleUpperCase('pt-BR')
  const [arte, familia] = await Promise.all([carregarImagem(arteUrl), carregarFonteDaCapa()])
  const canvas = document.createElement('canvas')
  canvas.width = CAPA_LARGURA_PX
  canvas.height = CAPA_ALTURA_PX
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.imageSmoothingQuality = 'high'
  desenharArteA4(ctx, arte, canvas.width, canvas.height)
  if (nome && config.escreverNome) {
    const { faixa } = config
    const ajuste = ajustarNomeNaFaixa(ctx, nome, faixa.largura * canvas.width, faixa.altura * canvas.height, familia)
    ctx.font = ajuste.fonte
    ctx.fillStyle = config.corNome || '#fff'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    const centroX = (faixa.x + faixa.largura / 2) * canvas.width
    const centroY = (faixa.y + faixa.altura / 2) * canvas.height
    const entrelinha = ajuste.tamanho * 1.08
    ajuste.linhas.forEach((linha, i) =>
      ctx.fillText(linha, centroX, centroY + (i - (ajuste.linhas.length - 1) / 2) * entrelinha),
    )
  }
  return canvas.toDataURL('image/jpeg', 0.92)
}

// Reduz (e, com `proporcao`, recorta ao centro) a foto para JPEG — mesmo
// tratamento das fotos do protocolo fixo (prepararFoto()).
export async function prepararFoto(src: string, proporcao?: number): Promise<string | null> {
  try {
    const img = await carregarImagem(src)
    let sx = 0
    let sy = 0
    let sw = img.naturalWidth
    let sh = img.naturalHeight
    if (proporcao) {
      if (sw / sh > proporcao) {
        const nw = sh * proporcao
        sx = (sw - nw) / 2
        sw = nw
      } else {
        const nh = sw / proporcao
        sy = (sh - nh) / 2
        sh = nh
      }
    }
    const escala = Math.min(1, 1400 / Math.max(sw, sh))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(sw * escala)
    canvas.height = Math.round(sh * escala)
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.88)
  } catch {
    return null
  }
}
