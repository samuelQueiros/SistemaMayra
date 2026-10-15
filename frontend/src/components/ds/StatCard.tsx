import type { ReactNode } from 'react'
import { Card } from './Card'

type Tone = 'violeta' | 'ceu' | 'sol'

interface StatCardProps {
  icon: ReactNode
  tone?: Tone
  value: ReactNode
  label: ReactNode
}

// Cartão de indicador do painel: ícone em fundo pastel, número em destaque e
// uma onda decorativa (só enfeite, sem dados) no rodapé.
export function StatCard({ icon, tone = 'violeta', value, label }: StatCardProps) {
  return (
    <Card className="stat-card">
      <div className="stat">
        <span className={`stat-icon stat-icon-${tone}`} aria-hidden="true">
          {icon}
        </span>
        <div>
          <span className="stat-value">{value}</span>
          <span className="stat-label">{label}</span>
        </div>
      </div>
      <svg className={`stat-wave stat-wave-${tone}`} viewBox="0 0 400 56" preserveAspectRatio="none" aria-hidden="true" focusable="false">
        <path d="M0 44 C 70 44, 110 30, 170 32 S 270 50, 320 30 S 380 6, 400 10 L 400 56 L 0 56 Z" fill="currentColor" />
        <path d="M0 50 C 90 50, 140 40, 200 42 S 300 54, 350 38 S 390 24, 400 26 L 400 56 L 0 56 Z" fill="currentColor" />
      </svg>
    </Card>
  )
}
