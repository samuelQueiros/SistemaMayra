import type { CSSProperties, ReactNode } from 'react'
import { useId, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { NavLink, useLocation } from 'react-router-dom'
import styles from './SidebarNav.module.css'

interface SidebarNavItem {
  to: string
  label: string
  icon?: ReactNode
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

export function SidebarNav({ items, logoUrl, footer, style }: SidebarNavProps) {
  const { pathname } = useLocation()
  return (
    <nav
      style={{
        width: 'var(--np-sidebar-w)',
        flex: '0 0 auto',
        background: 'var(--np-surface)',
        borderRight: '1px solid var(--np-border)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--np-space-5)',
        padding: 'var(--np-space-5) var(--np-space-4)',
        ...style,
      }}
    >
      {logoUrl && <img src={logoUrl} alt="Neuropsicopedagoga Mayra Vanessa" style={{ width: 132, alignSelf: 'center' }} />}
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--np-space-1)' }}>
        {items.map((it) =>
          it.children ? (
            <SidebarGroup key={`${it.to}:${pathname}`} item={it} />
          ) : it.external ? (
            <li key={it.to}>
              <a
                href={it.to}
                target="_blank"
                rel="noreferrer"
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--np-space-3)',
                  padding: '10px var(--np-space-3)',
                  cursor: 'pointer',
                  textDecoration: 'none',
                  borderRadius: 'var(--np-radius-md)',
                  color: 'var(--np-text-muted)',
                  font: 'var(--np-type-body)',
                }}
              >
                {it.icon && (
                  <span style={{ display: 'inline-flex', width: 20, color: 'var(--np-text-subtle)' }}>{it.icon}</span>
                )}
                <span style={{ flex: 1 }}>{it.label}</span>
              </a>
            </li>
          ) : (
            <li key={it.to}>
              <NavLink
                to={it.to}
                style={({ isActive }): CSSProperties => ({
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--np-space-3)',
                  padding: '10px var(--np-space-3)',
                  cursor: 'pointer',
                  textDecoration: 'none',
                  borderRadius: 'var(--np-radius-md)',
                  background: isActive ? 'var(--np-surface-alt)' : 'transparent',
                  color: isActive ? 'var(--np-text-brand)' : 'var(--np-text-muted)',
                  font: isActive ? 'var(--np-type-body-strong)' : 'var(--np-type-body)',
                  transition: 'background var(--np-dur) var(--np-ease)',
                })}
              >
                {({ isActive }) => (
                  <>
                    {it.icon && (
                      <span style={{ display: 'inline-flex', width: 20, color: isActive ? 'var(--np-primary)' : 'var(--np-text-subtle)' }}>
                        {it.icon}
                      </span>
                    )}
                    <span style={{ flex: 1 }}>{it.label}</span>
                  </>
                )}
              </NavLink>
            </li>
          ),
        )}
      </ul>
      <div style={{ marginTop: 'auto' }}>{footer}</div>
    </nav>
  )
}

function SidebarGroup({ item }: { item: SidebarNavItem }) {
  const { pathname } = useLocation()
  const active = [item.to, ...(item.children ?? []).map((c) => c.to)].some((to) => pathname === to || pathname.startsWith(to + '/'))
  const [expanded, setExpanded] = useState(active)
  const id = useId()

  if (item.alwaysOpen) {
    return (
      <li>
        <div className={`${styles.trigger} ${styles.heading} ${active ? styles.active : ''}`} id={id}>
          {item.icon}
          <span>{item.label}</span>
        </div>
        <ul aria-labelledby={id} className={styles.submenu}>
          {item.children?.map((child) => (
            <li key={child.to}>
              <NavLink to={child.to} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
                {child.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </li>
    )
  }

  return (
    <li>
      <button
        type="button"
        className={`${styles.trigger} ${active ? styles.active : ''}`}
        aria-expanded={expanded}
        aria-controls={id}
        onClick={() => setExpanded((value) => !value)}
      >
        {item.icon}
        <span>{item.label}</span>
        <ChevronDown size={16} className={`${styles.chevron} ${expanded ? styles.expanded : ''}`} />
      </button>
      <ul id={id} hidden={!expanded} className={styles.submenu}>
        {item.children?.map((child) => (
          <li key={child.to}>
            <NavLink to={child.to} className={({ isActive }) => `${styles.link} ${isActive ? styles.active : ''}`}>
              {child.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </li>
  )
}
