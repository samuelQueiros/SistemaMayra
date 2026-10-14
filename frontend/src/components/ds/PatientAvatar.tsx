import type { CSSProperties } from 'react'

const TONS = ['violeta', 'ceu', 'sol'] as const
const PARTICULAS = new Set(['da', 'das', 'de', 'do', 'dos', 'e'])

// Cor fixa por nome: o mesmo paciente tem sempre a mesma cor.
function tomDoNome(nome: string) {
  let soma = 0
  for (const letra of nome.trim().toLowerCase()) soma = (soma * 31 + letra.charCodeAt(0)) >>> 0
  return TONS[soma % TONS.length]
}

interface PatientAvatarProps {
  name?: string
  photoUrl?: string
  size?: number
  style?: CSSProperties
}

export function PatientAvatar({ name = '', photoUrl, size = 40, style }: PatientAvatarProps) {
  const initials = name
    .trim()
    .split(/\s+/)
    .filter((parte) => !PARTICULAS.has(parte.toLowerCase()))
    .slice(0, 2)
    .map((n) => n[0] || '')
    .join('')
    .toUpperCase()
  return (
    <span
      aria-hidden="true"
      className={`avatar avatar-${tomDoNome(name)}`}
      style={{
        width: size,
        height: size,
        fontSize: Math.round(size * 0.36),
        ...(photoUrl ? { backgroundImage: `url(${photoUrl})` } : null),
        ...style,
      }}
    >
      {!photoUrl && initials}
    </span>
  )
}
