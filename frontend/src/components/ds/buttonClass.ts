export type ButtonVariant = 'primary' | 'secondary' | 'tonal' | 'ghost' | 'danger' | 'danger-ghost'
export type ButtonSize = 'sm' | 'md' | 'lg'

// Classes do botão — também para elementos que não podem ser um <button>
// (ex.: <Link> do react-router-dom usado como ação de navegação).
export function buttonClass(variant: ButtonVariant = 'primary', size: ButtonSize = 'md', extra?: string): string {
  return ['btn', `btn-${variant}`, size !== 'md' && `btn-${size}`, extra].filter(Boolean).join(' ')
}
