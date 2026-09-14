import type { CSSProperties } from 'react'

interface PatientAvatarProps {
  name?: string
  photoUrl?: string
  size?: number
  accent?: string
  style?: CSSProperties
}

export function PatientAvatar({ name = '', photoUrl, size = 40, accent = 'var(--np-purple-300)', style }: PatientAvatarProps) {
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((n) => n[0] || '')
    .join('')
    .toUpperCase()
  return (
    <span
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: photoUrl ? `center/cover url(${photoUrl})` : accent,
        color: 'var(--np-purple-900)',
        font: 'var(--np-type-label)',
        fontSize: Math.round(size * 0.36),
        border: '2px solid var(--np-white)',
        boxShadow: 'var(--np-shadow-xs)',
        flex: '0 0 auto',
        ...style,
      }}
    >
      {!photoUrl && initials}
    </span>
  )
}
