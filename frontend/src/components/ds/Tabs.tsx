import type { CSSProperties, ReactNode } from 'react'

interface TabItem {
  id: string
  label: ReactNode
  count?: number
}

interface TabsProps {
  items: TabItem[]
  activeId?: string
  onSelect?: (id: string) => void
  style?: CSSProperties
}

export function Tabs({ items = [], activeId, onSelect, style }: TabsProps) {
  return (
    <div
      role="tablist"
      style={{ display: 'flex', gap: 'var(--np-space-1)', padding: 4, background: 'var(--np-surface-sunken)', borderRadius: 'var(--np-radius-pill)', ...style }}
    >
      {items.map((it) => {
        const active = it.id === activeId
        return (
          <button
            key={it.id}
            role="tab"
            aria-selected={active}
            type="button"
            onClick={() => onSelect?.(it.id)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--np-space-2)',
              border: 0,
              cursor: 'pointer',
              padding: '8px var(--np-space-4)',
              borderRadius: 'var(--np-radius-pill)',
              background: active ? 'var(--np-surface)' : 'transparent',
              boxShadow: active ? 'var(--np-shadow-xs)' : 'none',
              color: active ? 'var(--np-text-brand)' : 'var(--np-text-muted)',
              font: active ? 'var(--np-type-label)' : 'var(--np-type-body)',
              fontSize: 'var(--np-text-sm)',
            }}
          >
            {it.label}
            {it.count != null && <span style={{ font: 'var(--np-type-overline)', color: 'var(--np-text-subtle)' }}>{it.count}</span>}
          </button>
        )
      })}
    </div>
  )
}
