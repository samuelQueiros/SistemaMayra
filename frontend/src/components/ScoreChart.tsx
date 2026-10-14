import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  PointElement,
  RadialLinearScale,
  Tooltip,
} from 'chart.js'
import type { ChartOptions } from 'chart.js'
import { Bar, Pie, Radar } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  RadialLinearScale,
  PointElement,
  ArcElement,
  Tooltip,
  Legend,
)

// Paleta "Caderno Lilás" (public/identidade/tokens.css). O Chart.js desenha
// em canvas e não entende var(): lê o valor das variáveis na hora.
const VARIAVEIS = ['--violeta-600', '--ceu-500', '--sol-500', '--ok', '--violeta-300', '--ceu-300', '--sol-300', '--violeta-800']
const corDoToken = (nome: string) => getComputedStyle(document.documentElement).getPropertyValue(nome).trim() || undefined

interface ScoreChartProps {
  type: 'bar' | 'radar' | 'pie'
  labels: string[]
  values: number[]
  title: string
}

export default function ScoreChart({ type, labels, values, title }: ScoreChartProps) {
  const data = {
    labels,
    datasets: [
      {
        label: title,
        data: values,
        backgroundColor: type === 'bar' ? corDoToken('--primary') : VARIAVEIS.map(corDoToken),
        borderColor: corDoToken('--primary'),
        borderWidth: type === 'radar' ? 2 : 1,
      },
    ],
  }

  if (type === 'radar') {
    const radarOptions: ChartOptions<'radar'> = {
      responsive: true,
      plugins: { legend: { display: true }, title: { display: true, text: title } },
    }
    return <Radar data={data} options={radarOptions} />
  }

  if (type === 'pie') {
    const pieOptions: ChartOptions<'pie'> = {
      responsive: true,
      plugins: { legend: { display: true }, title: { display: true, text: title } },
    }
    return <Pie data={data} options={pieOptions} />
  }

  // Barras horizontais: com escalas de muitas áreas (ex.: CARS tem 15), um
  // gráfico de barras verticais amontoa e sobrepõe os rótulos do eixo. Deitar
  // as barras dá espaço de sobra para o texto de cada área, sem sobreposição.
  const barOptions: ChartOptions<'bar'> = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      title: { display: true, text: title },
    },
    scales: {
      x: { beginAtZero: true },
    },
  }
  const altura = Math.max(220, labels.length * 34)
  return (
    <div style={{ height: altura }}>
      <Bar data={data} options={barOptions} />
    </div>
  )
}
