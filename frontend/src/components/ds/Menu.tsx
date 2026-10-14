import type { CSSProperties, KeyboardEvent, ReactNode } from 'react'
import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { buttonClass } from './buttonClass'
import type { ButtonSize } from './buttonClass'

export interface MenuItem {
  label: string
  icon?: ReactNode
  /** Navega para esta rota… */
  to?: string
  /** …ou executa esta ação. */
  onSelect?: () => void
}

interface MenuProps {
  /** Nome acessível do botão que abre o menu (ex.: "Mais ações para Ana"). */
  label: string
  icon: ReactNode
  items: MenuItem[]
  size?: ButtonSize
}

// Menu suspenso de ações secundárias (botão ⋯). Setas navegam, Esc fecha e
// devolve o foco ao botão, clique fora fecha. A lista é `position: fixed`
// para não ser cortada pela rolagem horizontal das tabelas.
export function Menu({ label, icon, items, size = 'md' }: MenuProps) {
  const [posicao, setPosicao] = useState<CSSProperties | null>(null)
  const aberto = posicao !== null
  const raiz = useRef<HTMLDivElement>(null)
  const botao = useRef<HTMLButtonElement>(null)
  const id = useId()

  const itens = () => Array.from(raiz.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])

  useEffect(() => {
    if (!aberto) return
    itens()[0]?.focus()
    const fecharSemFoco = () => setPosicao(null)
    document.addEventListener('mousedown', fora)
    window.addEventListener('resize', fecharSemFoco)
    window.addEventListener('scroll', fecharSemFoco, true)
    return () => {
      document.removeEventListener('mousedown', fora)
      window.removeEventListener('resize', fecharSemFoco)
      window.removeEventListener('scroll', fecharSemFoco, true)
    }
    function fora(e: MouseEvent) {
      if (!raiz.current?.contains(e.target as Node)) setPosicao(null)
    }
  }, [aberto])

  function abrir() {
    const caixa = botao.current?.getBoundingClientRect()
    if (!caixa) return
    const alturaEstimada = items.length * 44 + 14
    const abreParaCima = caixa.bottom + alturaEstimada + 8 > window.innerHeight && caixa.top > alturaEstimada
    setPosicao({
      position: 'fixed',
      right: Math.max(8, window.innerWidth - caixa.right),
      ...(abreParaCima ? { bottom: window.innerHeight - caixa.top + 6 } : { top: caixa.bottom + 6 }),
    })
  }

  function fechar(devolverFoco: boolean) {
    setPosicao(null)
    if (devolverFoco) botao.current?.focus()
  }

  function aoTeclar(e: KeyboardEvent<HTMLUListElement>) {
    const lista = itens()
    const atual = lista.indexOf(document.activeElement as HTMLElement)
    if (e.key === 'Escape') {
      e.preventDefault()
      fechar(true)
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      const passo = e.key === 'ArrowDown' ? 1 : -1
      lista[(atual + passo + lista.length) % lista.length]?.focus()
    } else if (e.key === 'Home' || e.key === 'End') {
      e.preventDefault()
      lista[e.key === 'Home' ? 0 : lista.length - 1]?.focus()
    } else if (e.key === 'Tab') {
      fechar(false)
    }
  }

  return (
    <div className="menu" ref={raiz}>
      <button
        ref={botao}
        type="button"
        className={buttonClass('ghost', size, 'btn-icon')}
        aria-label={label}
        title={label}
        aria-haspopup="menu"
        aria-expanded={aberto}
        aria-controls={aberto ? id : undefined}
        onClick={() => (aberto ? fechar(false) : abrir())}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown' && !aberto) {
            e.preventDefault()
            abrir()
          }
        }}
      >
        {icon}
      </button>
      {aberto && (
        <ul className="menu-list" role="menu" id={id} aria-label={label} onKeyDown={aoTeclar} style={posicao ?? undefined}>
          {items.map((item) => (
            <li key={item.label} role="none">
              {item.to ? (
                <Link role="menuitem" className="menu-item" to={item.to} tabIndex={-1} onClick={() => fechar(false)}>
                  {item.icon}
                  {item.label}
                </Link>
              ) : (
                <button
                  role="menuitem"
                  type="button"
                  className="menu-item"
                  tabIndex={-1}
                  onClick={() => {
                    fechar(true)
                    item.onSelect?.()
                  }}
                >
                  {item.icon}
                  {item.label}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
