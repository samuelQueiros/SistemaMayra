/** Design system: menu lateral. */
import type { CSSProperties, ReactNode } from 'react'
import { Fragment, useId, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { NavLink, useLocation } from 'react-router-dom'
import styles from './SidebarNav.module.css'

interface SidebarNavItem {
  to: string
  label: string
  icon?: ReactNode
  /** Rótulo do grupo do menu (ex.: "Clínica", "Sistema"), mostrado em caixa
   * alta antes do primeiro item do grupo. */
  section?: string
  /** Quando true, `to` é tratado como um link externo/arquivo estático real
   * (ex.: o formulário standalone) e abre em nova aba, em vez de navegação
   * client-side do React Router. */
  external?: boolean
  children?: SidebarNavItem[]
  /** Grupo com as subopções sempre visíveis (sem recolher). */
  alwaysOpen?: boolean
}

interface SidebarNavProps {
  items: SidebarNavItem[]
  logoUrl?: string
  footer?: ReactNode
  style?: CSSProperties
}

const classes = (...nomes: (string | false | undefined)[]) => nomes.filter(Boolean).join(' ')

// Agrupa itens consecutivos com o mesmo `section`.
function porSecao(items: SidebarNavItem[]) {
  const grupos: { section?: string; items: SidebarNavItem[] }[] = []
  for (const item of items) {
    const ultimo = grupos[grupos.length - 1]
    if (ultimo && ultimo.section === item.section) ultimo.items.push(item)
    else grupos.push({ section: item.section, items: [item] })
  }
  return grupos
}

export function SidebarNav({ items, logoUrl, footer, style }: SidebarNavProps) {
  const { pathname } = useLocation()
  const idBase = useId()
  return (
    <nav className={styles.nav} aria-label="Menu principal" style={style}>
      {logoUrl && (
        <div className={styles.brand}>
          <img src={logoUrl} alt="" className={styles.logo} />
          <div className={styles.brandText}>
            <strong>Mayra Vanessa</strong>
            <span>Neuropsicopedagoga</span>
          </div>
        </div>
      )}
      <div className={styles.sections}>
        {porSecao(items).map((grupo, g) => {
          const idSecao = `${idBase}-secao-${g}`
          return (
            <Fragment key={grupo.section ?? g}>
              {grupo.section && (
                <p className={styles.sectionLabel} id={idSecao}>
                  {grupo.section}
                </p>
              )}
              <ul className={styles.list} aria-labelledby={grupo.section ? idSecao : undefined}>
                {grupo.items.map((it) =>
                  it.children ? (
                    <SidebarGroup key={`${it.to}:${pathname}`} item={it} />
                  ) : it.external ? (
                    <li key={it.to}>
                      <a href={it.to} target="_blank" rel="noreferrer" className={styles.item}>
                        {it.icon && <span className={styles.icon}>{it.icon}</span>}
                        <span className={styles.label}>{it.label}</span>
                      </a>
                    </li>
                  ) : (
                    <li key={it.to}>
                      <NavLink to={it.to} className={({ isActive }) => classes(styles.item, isActive && styles.active)}>
                        {it.icon && <span className={styles.icon}>{it.icon}</span>}
                        <span className={styles.label}>{it.label}</span>
                      </NavLink>
                    </li>
                  ),
                )}
              </ul>
            </Fragment>
          )
        })}
      </div>
      {footer && <div className={styles.footer}>{footer}</div>}
    </nav>
  )
}

function SidebarGroup({ item }: { item: SidebarNavItem }) {
  const { pathname } = useLocation()
  const active = [item.to, ...(item.children ?? []).map((c) => c.to)].some((to) => pathname === to || pathname.startsWith(to + '/'))
  const [expanded, setExpanded] = useState(active)
  const id = useId()

  const submenu = (
    <ul id={id} hidden={!item.alwaysOpen && !expanded} aria-labelledby={item.alwaysOpen ? `${id}-titulo` : undefined} className={styles.submenu}>
      {item.children?.map((child) => (
        <li key={child.to}>
          <NavLink to={child.to} className={({ isActive }) => classes(styles.subitem, isActive && styles.subActive)}>
            {child.label}
          </NavLink>
        </li>
      ))}
    </ul>
  )

  if (item.alwaysOpen) {
    return (
      <li>
        <div className={classes(styles.item, styles.heading, active && styles.groupActive)} id={`${id}-titulo`}>
          {item.icon && <span className={styles.icon}>{item.icon}</span>}
          <span className={styles.label}>{item.label}</span>
        </div>
        {submenu}
      </li>
    )
  }

  return (
    <li>
      <button
        type="button"
        className={classes(styles.item, active && styles.groupActive)}
        aria-expanded={expanded}
        aria-controls={id}
        onClick={() => setExpanded((value) => !value)}
      >
        {item.icon && <span className={styles.icon}>{item.icon}</span>}
        <span className={styles.label}>{item.label}</span>
        <ChevronDown aria-hidden="true" className={classes(styles.chevron, expanded && styles.expanded)} />
      </button>
      {submenu}
    </li>
  )
}
