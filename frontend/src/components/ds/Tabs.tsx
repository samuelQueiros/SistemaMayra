/** Design system: abas. */
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
    <div role="tablist" className="tabs" style={style}>
      {items.map((it) => (
        <button key={it.id} role="tab" aria-selected={it.id === activeId} type="button" className="tab" onClick={() => onSelect?.(it.id)}>
          {it.label}
          {it.count != null && <span className="tab-count">{it.count}</span>}
        </button>
      ))}
    </div>
  )
}
