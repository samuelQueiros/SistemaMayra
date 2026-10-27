import { readFileSync } from 'node:fs'
import { loadImage, createCanvas } from 'canvas'
import { JSDOM } from 'jsdom'
import { afterEach, describe, expect, it } from 'vitest'

// Gráficos de verdade (Chart.js + canvas), sem os stubs dos outros testes do
// formulário: se um gráfico some do relatório ou sai em branco — por ordem de
// seções, regra de idade, escala desmarcada ou erro engolido pelo
// graficoPNG — este teste falha.

const HTML = readFileSync('public/formulario-novo-paciente.html', 'utf8')
const CHART_JS = readFileSync('public/vendor/chart.umd.min.js', 'utf8')
const FUNCOES = ['graficoDominios', 'graficoHabilidadesAcademicas', 'graficoHabilidadesGerais', 'graficoFuncoesExecutivas', 'graficoPortage', 'graficoCARS', 'graficoATA', 'graficosSNAP']

let dom
afterEach(() => dom?.window.close())

async function abrirFormulario() {
  dom = new JSDOM(HTML, { runScripts: 'dangerously', url: 'http://localhost/formulario-novo-paciente.html?modo=catalogo', pretendToBeVisual: true })
  await new Promise(resolve => dom.window.addEventListener('load', resolve))
  const w = dom.window
  w.eval(CHART_JS)
  w.gerarCapaRelatorio = async () => null
  // Registra o que cada função de gráfico devolveu, para saber qual sumiu.
  const gerados = []
  for (const nome of FUNCOES) {
    const original = w[nome]
    w[nome] = (...args) => {
      const r = original(...args)
      const srcs = r && typeof r === 'object' ? [r.pontos, r.perc] : [r]
      srcs.forEach((src, i) => gerados.push({ nome: nome === 'graficosSNAP' ? `graficosSNAP.${i ? 'perc' : 'pontos'}` : nome, src }))
      return r
    }
  }
  return { w, gerados }
}

const repetir = (n, f) => Object.fromEntries(Array.from({ length: n }, (_, i) => f(i)))
const pacienteFicticio = nascimento => ({
  nomePaciente: 'Paciente Fictício', sexo: 'Masculino', dataNascimento: nascimento, dataRelatorio: '2026-10-15',
  anoEscolar: 'Educação Infantil', hip_tea: true,
  ...repetir(15, i => [`cars_${i}`, String(1 + (i % 3) * 0.5)]),
  ...repetir(22, i => [`ata_item_${i}`, String(i % 3)]),
  ...repetir(22, i => [`ata_perc_${i}`, String(10 + i)]),
  ...repetir(18, i => [`snap_${i}`, String(i % 4)]),
  ...repetir(23, i => [`mchat_${i}`, i % 2 ? 'sim' : 'nao']),
  ...repetir(10, i => [`hcog_${i}`, ['Sim', 'Às Vezes', 'Não'][i % 3]]),
  ...repetir(10, i => [`hsoc_${i}`, ['Sim', 'Às Vezes', 'Não'][i % 3]]),
  ...repetir(11, i => [`hmot_${i}`, ['Sim', 'Às Vezes', 'Não'][i % 3]]),
  ...repetir(4, i => [`hab_status_${i}`, ['Satisfatório', 'Em Desenvolvimento', 'Insatisfatório', 'Satisfatório'][i]]),
  ...repetir(8, i => [`fe_perc_${i}`, String(20 + i * 8)]),
  ...repetir(8, i => [`fe_manif_${i}`, `Observação ${i}`]),
  dom_atencao: '30', dom_sociais: '20', dom_comportamento: '25', dom_aprendizagem: '15', dom_fe: '10',
  textoPortage: 'Texto do Portage.', textoAtendimentos: 'Texto dos atendimentos.', textoSNAP: 'Texto do SNAP.',
})

async function gerarRelatorio(dados, { comoIA = false } = {}) {
  const { w, gerados } = await abrirFormulario()
  w.aplicarDados(dados)
  w.carregarPortage()
  w.document.querySelectorAll('.portageItem').forEach((el, i) => { el.value = ['1', '0.5', '0'][i % 3] })
  // Total da ATA: na tela é recalculado a cada resposta marcada.
  w.calcularATA()
  if (comoIA) {
    // Demais cálculos de gerarLaudoAutomatico (?laudo=…&modo=gerar).
    w.calcularPortage()
    w.calcularCARS()
    w.atualizarInterpretacoes()
  }
  const html = await w.gerarDocumentoLaudoHTML()
  return { w, html, gerados, doc: new w.DOMParser().parseFromString(html, 'text/html') }
}

async function pixelsColoridos(src) {
  const img = await loadImage(src)
  const ctx = createCanvas(img.width, img.height).getContext('2d')
  ctx.drawImage(img, 0, 0)
  const { data } = ctx.getImageData(0, 0, img.width, img.height)
  let n = 0
  for (let i = 0; i < data.length; i += 4) if (data[i + 3] && Math.min(data[i], data[i + 1], data[i + 2]) < 235) n++
  return n
}

// Gráficos esperados: um por grupo de habilidades avaliado, mais os das
// escalas que o próprio formulário diz que entram no relatório.
function esperados(w, { semCARS = false } = {}) {
  const lista = ['graficoDominios', 'graficoHabilidadesAcademicas', 'graficoHabilidadesGerais', 'graficoHabilidadesGerais', 'graficoHabilidadesGerais', 'graficoFuncoesExecutivas', 'graficoPortage']
  if (!semCARS) lista.push('graficoCARS')
  lista.push('graficoATA')
  if (w.metodoNoRelatorio('snap')) lista.push('graficosSNAP.pontos', 'graficosSNAP.perc')
  return lista
}

async function conferirGraficos({ w, doc, gerados }, nomesEsperados) {
  const noDocumento = [...doc.querySelectorAll('.documento .grafico img, .documento .graficos-lado img')].map(img => img.getAttribute('src'))
  const presentes = gerados.filter(g => g.src && noDocumento.includes(g.src)).map(g => g.nome)
  expect(presentes).toEqual(nomesEsperados)
  expect(noDocumento).toHaveLength(nomesEsperados.length)
  for (const src of noDocumento) expect(await pixelsColoridos(src)).toBeGreaterThan(2000)
}

// Bloco tabela → gráfico: a imagem vem logo depois da tabela do mesmo bloco.
function graficoLogoAposTabela(doc, textoDoTitulo) {
  const titulo = [...doc.querySelectorAll('.documento h2, .documento h3')].find(h => h.textContent.includes(textoDoTitulo))
  expect(titulo, textoDoTitulo).toBeTruthy()
  const tabela = titulo.nextElementSibling
  expect(tabela.tagName).toBe('TABLE')
  expect(tabela.nextElementSibling.classList.contains('grafico')).toBe(true)
}

describe('gráficos do relatório (protocolo padrão)', () => {
  it('paciente de 8 anos: todos os gráficos, com conteúdo, na ordem do relatório', async () => {
    const r = await gerarRelatorio(pacienteFicticio('2018-05-10'))
    await conferirGraficos(r, esperados(r.w))
    graficoLogoAposTabela(r.doc, 'HABILIDADES ACADÊMICAS')
    graficoLogoAposTabela(r.doc, 'Aplicação das Funções Executivas')
  }, 60000)

  it('menor de 6 anos: SNAP-IV só entra se a regra de idade permitir', async () => {
    const r = await gerarRelatorio(pacienteFicticio('2021-03-01'))
    await conferirGraficos(r, esperados(r.w))
  }, 60000)

  it('até 30 meses: M-CHAT no lugar do SNAP-IV e os demais gráficos mantidos', async () => {
    const r = await gerarRelatorio(pacienteFicticio('2024-06-01'))
    expect(r.w.metodoNoRelatorio('snap')).toBe(false)
    expect(r.html).toContain('M-CHAT — Modified Checklist For Autism In Toddlers')
    await conferirGraficos(r, esperados(r.w))
  }, 60000)

  it('escala desmarcada: só o gráfico dela some', async () => {
    const r = await gerarRelatorio({ ...pacienteFicticio('2018-05-10'), __metodosExcluidos: ['cars'] })
    await conferirGraficos(r, esperados(r.w, { semCARS: true }))
  }, 60000)

  it('relatório por IA (modo gerar): mesmos gráficos do protocolo padrão', async () => {
    const r = await gerarRelatorio(pacienteFicticio('2018-05-10'), { comoIA: true })
    await conferirGraficos(r, esperados(r.w))
  }, 60000)
})
