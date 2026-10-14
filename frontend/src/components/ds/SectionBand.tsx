import type { ReactNode } from 'react'

interface SectionBandProps {
  number: number
  title: ReactNode
  /** Ex.: "3 campos obrigatórios". */
  meta?: ReactNode
}

// Faixa de título da seção (sem degradê): quadrado violeta com o número +
// título + quantos campos são obrigatórios.
export function SectionBand({ number, title, meta }: SectionBandProps) {
  return (
    <div className="section-band">
      <span className="section-band-number" aria-hidden="true">
        {number}
      </span>
      <div>
        <h2 className="section-band-title">{title}</h2>
        {meta && <p className="section-band-meta">{meta}</p>}
      </div>
    </div>
  )
}
