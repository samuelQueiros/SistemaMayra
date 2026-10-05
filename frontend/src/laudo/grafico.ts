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
  try {
    const itens = escala.itens.filter((i) => respostas?.[i.id] !== undefined)
    if (!itens.length) return null
    const canvas = document.createElement('canvas')
    const altura = Math.max(300, 90 + itens.length * 56)
    canvas.width = 1000
    canvas.height = altura
    const maximo = Math.max(...escala.opcoes.map((o) => o.valor))
    const grafico = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: itens.map((i) => quebrarRotulo(i.rotulo)),
        datasets: [
          {
            data: itens.map((i) => escala.opcoes[respostas![i.id]]?.valor ?? 0),
            backgroundColor: '#8e7cc3',
            borderRadius: 4,
            barThickness: 26,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: false,
        animation: false,
        devicePixelRatio: 1,
        plugins: {
          title: { display: true, text: titulo, color: '#262626', font: { size: 28, weight: 'bold' }, padding: { top: 10, bottom: 18 } },
          legend: { display: false },
        },
        scales: {
          x: { min: Math.min(0, ...escala.opcoes.map((o) => o.valor)), max: maximo, ticks: { font: { size: 20 }, stepSize: 1 } },
          y: { ticks: { font: { size: 21 }, color: '#262626' } },
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
