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

// Paleta da marca (Neuropp Mayra Vanessa) — ver frontend/src/styles/tokens/colors.css.
const CORES = ['#7561ae', '#d9709f', '#8fb4d6', '#f5a623', '#3fa35b', '#b3a5e2', '#e7a8c8', '#dce9f5']

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
        backgroundColor: type === 'bar' ? '#7561ae' : CORES,
        borderColor: '#7561ae',
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
