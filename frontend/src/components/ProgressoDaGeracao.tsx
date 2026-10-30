/**
 * Barra e mensagens de andamento do Laudo por IA, a partir do andamento consultado a cada 2 s. Anda
 * devagar até o teto da etapa para nunca parecer travada.
 */
import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { ProgressBar } from './ds'

export interface Progresso {
  /** Quanto já foi feito (0-100). */
  alvo: number
  /** Até onde chega quando a etapa em curso terminar. */
  teto: number
}

interface ProgressoDaGeracaoProps extends Progresso {
  mensagem: ReactNode
  detalhes?: ReactNode
}

const INTERVALO_MS = 500
// Fração do caminho até o teto andada a cada intervalo: a barra desacelera
// perto do fim da etapa e nunca chega nele sem o servidor confirmar.
const PASSO = 0.015

function tempoDecorrido(segundos: number): string {
  const minutos = Math.floor(segundos / 60)
  const resto = segundos % 60
  return minutos ? `${minutos} min ${String(resto).padStart(2, '0')} s` : `${resto} s`
}

// Barra de progresso das gerações com IA: avança com o andamento do servidor
// e, entre um aviso e outro, segue andando devagar até o fim da etapa atual —
// para a psicóloga não achar que travou.
export function ProgressoDaGeracao({ alvo, teto, mensagem, detalhes }: ProgressoDaGeracaoProps) {
  const [exibido, setExibido] = useState(alvo)
  const [segundos, setSegundos] = useState(0)
  const limites = useRef({ alvo, teto })
  useEffect(() => {
    limites.current = { alvo, teto: Math.max(teto, alvo) }
  }, [alvo, teto])

  useEffect(() => {
    const inicio = Date.now()
    const timer = setInterval(() => {
      const { alvo: a, teto: t } = limites.current
      setExibido((atual) => {
        const base = Math.max(atual, a)
        return Math.min(base + (t - base) * PASSO, 99)
      })
      setSegundos(Math.floor((Date.now() - inicio) / 1000))
    }, INTERVALO_MS)
    return () => clearInterval(timer)
  }, [])

  const valor = Math.max(exibido, alvo)
  return (
    <div className="geracao-progresso" role="status" aria-live="polite">
      <ProgressBar value={valor} animada label={mensagem} caption={`${Math.floor(valor)}%`} />
      {detalhes}
      <p className="geracao-progresso-rodape">
        Tempo decorrido: {tempoDecorrido(segundos)}. Pode levar alguns minutos; deixe esta página aberta.
      </p>
    </div>
  )
}
