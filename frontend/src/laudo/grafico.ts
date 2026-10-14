// Gráfico de uma escala do modelo de protocolo, desenhado com Chart.js num
// canvas fora da tela e devolvido como imagem (data: URI) para o relatório.

import { BarController, BarElement, CategoryScale, Chart, LinearScale, Title } from 'chart.js'
import type { Plugin } from 'chart.js'
import type { Escala } from './tipos'

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Title)

const fundoBranco: Plugin<'bar'> = {
  id: 'fundoBranco',
  beforeDraw(chart) {
    const { ctx, width, height } = chart
    ctx.save()
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, width, height)
    ctx.restore()
  },
}

const quebrarRotulo = (texto: string, max = 30): string[] => {
  const linhas: string[] = []
  let atual = ''
  for (const palavra of texto.split(/\s+/)) {
    if ((atual + ' ' + palavra).trim().length > max && atual) {
      linhas.push(atual)
      atual = palavra
    } else {
      atual = (atual + ' ' + palavra).trim()
    }
  }
  if (atual) linhas.push(atual)
  return linhas
}

export function graficoDaEscala(titulo: string, escala: Escala, respostas: Record<string, number> | undefined): string | null {
  const itens = escala.itens.filter((i) => respostas?.[i.id] !== undefined)
  const valores = escala.opcoes.map((o) => o.valor)
  return graficoDeBarras(
    titulo,
    itens.map((i) => i.rotulo),
    itens.map((i) => escala.opcoes[respostas![i.id]]?.valor ?? 0),
    Math.max(...valores),
    Math.min(0, ...valores),
  )
}

// Gráfico de barras horizontais genérico (rótulos x valores).
export function graficoDeBarras(titulo: string, rotulos: string[], valores: number[], maximo?: number | null, minimo = 0): string | null {
  try {
    if (!rotulos.length) return null
    const canvas = document.createElement('canvas')
    const altura = Math.max(300, 90 + rotulos.length * 56)
    canvas.width = 1000
    canvas.height = altura
    const maiorValor = Math.max(...valores, 0)
    const grafico = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: rotulos.map((r) => quebrarRotulo(r)),
        datasets: [{ data: valores, backgroundColor: '#7561ae', borderRadius: 4, barThickness: 26 }],
      },
      options: {
        indexAxis: 'y',
        responsive: false,
        animation: false,
        devicePixelRatio: 1,
        plugins: {
          title: { display: true, text: titulo, color: '#2b2740', font: { size: 28, weight: 'bold' }, padding: { top: 10, bottom: 18 } },
          legend: { display: false },
        },
        scales: {
          x: { min: Math.min(minimo, ...valores), max: maximo && maximo >= maiorValor ? maximo : undefined, ticks: { font: { size: 20 } } },
          y: { ticks: { font: { size: 21 }, color: '#2b2740' } },
        },
      },
      plugins: [fundoBranco],
    })
    const uri = canvas.toDataURL('image/png')
    grafico.destroy()
    return uri
  } catch {
    // Sem canvas (ex.: testes em jsdom): o relatório sai sem o gráfico.
    return null
  }
}
