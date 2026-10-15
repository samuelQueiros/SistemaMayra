import { readFileSync } from 'node:fs'
import { JSDOM } from 'jsdom'
import { expect, it } from 'vitest'

it('documento mantém data, cidade e encaminhamentos e omite os métodos removidos', async () => {
  const html = readFileSync('public/formulario-novo-paciente.html', 'utf8')
  const dom = new JSDOM(html, { runScripts: 'dangerously', url: 'http://localhost/formulario-novo-paciente.html?modo=catalogo', pretendToBeVisual: true })
  try {
    await new Promise(resolve => dom.window.addEventListener('load', resolve))
    const w = dom.window
    // Sem rasterização de canvas: verificamos a composição real do documento.
    w.gerarCapaRelatorio = async () => 'data:image/png;base64,CAPA'
    for (const nome of ['graficoCARS', 'graficoATA', 'graficoPortage', 'graficoFuncoesExecutivas', 'graficoDominios', 'graficoHabilidadesAcademicas']) {
      w[nome] = () => `data:image/png;base64,${nome}`
    }
    w.graficosSNAP = () => ({ des: 'snap-des', hip: 'snap-hip' })
    w.aplicarDados({ nomePaciente: 'Paciente Teste', dataRelatorio: '2026-10-15', cidade: 'Gama – DF', enc_fonoaudiologia: true, enc_terapia_ocupacional: true, cars_0: '2', ata: '22', tod_0: '1', mchat_0: 'sim' })
    const original = await w.gerarDocumentoLaudoHTML()
    expect(original).toContain('Gama - DF, 15 de outubro de 2026')
    expect(original).toContain('<li>Fonoaudiologia</li>')
    expect(original).toContain('<li>Terapia Ocupacional</li>')
    expect(original).toContain('base64,graficoCARS')
    expect(original).toContain('base64,graficoATA')
    w.aplicarDados({ __metodosExcluidos: ['cars', 'ata', 'snap', 'tod', 'portage', 'mchat'] })
    const excluido = await w.gerarDocumentoLaudoHTML()
    expect(excluido).not.toContain('base64,graficoCARS')
    expect(excluido).not.toContain('base64,graficoATA')
    expect(excluido).not.toContain('base64,graficoPortage')
    expect(excluido).not.toContain('M-CHAT — Modified')
    expect(excluido).not.toContain('Escala CARS')
    expect(excluido).not.toContain('Escala ATA')
    expect(w.coletarDados().__metodosExcluidos).toContain('cars')
    expect(w.coletarDados().cars_0).toBe('2')
    expect(w.escalaAtivaNoTexto('CARS')).toBe(false)
    w.alternarEscalaMetodologia('CARS')
    expect(w.coletarDados().__metodosExcluidos).not.toContain('cars')
    expect(await w.gerarDocumentoLaudoHTML()).toContain('base64,graficoCARS')
  } finally { dom.window.close() }
})
