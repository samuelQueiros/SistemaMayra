import type { CSSProperties, ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

interface SidebarNavItem {
  to: string
  label: string
  icon?: ReactNode
}

interface SidebarNavProps {
  items: SidebarNavItem[]
  logoUrl?: string
  footer?: ReactNode
  style?: CSSProperties
}

export function SidebarNav({ items, logoUrl, footer, style }: SidebarNavProps) {
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
        {items.map((it) => (
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
        ))}
      </ul>
      <div style={{ marginTop: 'auto' }}>{footer}</div>
    </nav>
  )
}
