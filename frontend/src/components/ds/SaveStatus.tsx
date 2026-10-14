import { CircleAlert, CircleCheck, CircleDashed, LoaderCircle } from 'lucide-react'
import { Badge } from './Badge'

// Etiqueta "Ainda não salvo" / "Salvo às HH:MM" a partir da mensagem de
// status do autosave. Texto + ícone: o estado nunca fica só na cor.
export function SaveStatus({ status, salvo }: { status: string; salvo: boolean }) {
  const hora = /às (\d{2}:\d{2})/.exec(status)?.[1]
  if (status.startsWith('Salvando')) return <Badge tone="info" icon={<LoaderCircle aria-hidden="true" />}>Salvando…</Badge>
  if (status.startsWith('Alterações ainda não salvas'))
    return (
      <span title={status}>
        <Badge tone="danger" icon={<CircleAlert aria-hidden="true" />}>Não foi possível salvar</Badge>
      </span>
    )
  if (hora) return <Badge tone="success" icon={<CircleCheck aria-hidden="true" />}>Salvo às {hora}</Badge>
  if (salvo) return <Badge tone="success" icon={<CircleCheck aria-hidden="true" />}>Salvo</Badge>
  return <Badge tone="warning" icon={<CircleDashed aria-hidden="true" />}>Ainda não salvo</Badge>
}
