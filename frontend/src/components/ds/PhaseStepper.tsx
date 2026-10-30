/** Design system: indicador das fases do formulário. */
import { Check } from 'lucide-react'

export type PhaseState = 'done' | 'pending' | 'todo'

interface Phase {
  label: string
  state: PhaseState
}

interface PhaseStepperProps {
  phases: Phase[]
  current: number
  onSelect: (index: number) => void
}

const DESCRICAO: Record<PhaseState, string> = {
  done: 'concluída',
  pending: 'com pendências',
  todo: 'não iniciada',
}

// Indicador de fases: barra fina de progresso + círculos. Atual = violeta
// com o número; concluída = verde com ✓; pendente = amarelo com "!";
// não iniciada = branco com o número cinza. O estado também vai no nome
// acessível (nunca só pela cor).
export function PhaseStepper({ phases, current, onSelect }: PhaseStepperProps) {
  const concluidas = phases.filter((f) => f.state === 'done').length
  return (
    <nav className="stepper" aria-label="Fases do protocolo">
      <div className="stepper-head">
        <span>
          Fase {current + 1} de {phases.length}
        </span>
        <span className="stepper-count">
          {concluidas} de {phases.length} concluídas
        </span>
      </div>
      <div
        className="stepper-bar"
        role="progressbar"
        aria-label="Fases concluídas"
        aria-valuemin={0}
        aria-valuemax={phases.length}
        aria-valuenow={concluidas}
      >
        <div style={{ width: `${(concluidas / Math.max(1, phases.length)) * 100}%` }} />
      </div>
      <ol className="stepper-list">
        {phases.map((fase, i) => {
          const atual = i === current
          return (
            <li key={i}>
              <button
                type="button"
                className="stepper-step"
                data-state={fase.state}
                aria-current={atual ? 'step' : undefined}
                aria-label={`Fase ${i + 1}: ${fase.label} — ${atual ? 'atual, ' : ''}${DESCRICAO[fase.state]}`}
                onClick={() => onSelect(i)}
              >
                <span className="stepper-circle" aria-hidden="true">
                  {!atual && fase.state === 'done' ? <Check /> : !atual && fase.state === 'pending' ? '!' : i + 1}
                </span>
                <span className="stepper-label">{fase.label}</span>
              </button>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
