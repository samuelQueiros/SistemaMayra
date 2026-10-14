import { History, LogOut, Menu, Settings, Users, X } from 'lucide-react'
import { Suspense, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { IconButton, SidebarNav } from './ds'
import styles from './Layout.module.css'

const NAV_ITEMS = [
  {
    to: '/pacientes', label: 'Pacientes', icon: <Users size={18} />, alwaysOpen: true,
    children: [
      { to: '/pacientes', label: 'Todos Os Pacientes' },
      { to: '/atendimento/novo', label: 'Novo Atendimento' },
      { to: '/laudo-ia', label: 'Laudo Por IA' },
    ],
  },
  {
    to: '/configuracoes', label: 'Configurações', icon: <Settings size={18} />,
    children: [
      { to: '/configuracoes/registro', label: 'Registro Profissional' },
      { to: '/configuracoes/capa', label: 'Capa Dos Relatórios' },
      { to: '/configuracoes/protocolos', label: 'Modelos De Protocolo' },
      { to: '/configuracoes/ia', label: 'Inteligência Artificial' },
    ],
  },
  { to: '/logs', label: 'Ver Logs', icon: <History size={18} /> },
]

export default function Layout() {
  const { psychologist, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/')
  }

  const footer = (
    <div className={styles.footer}>
      {psychologist && <span className={styles.userName}>{psychologist.name}</span>}
      <button type="button" className={styles.logoutButton} onClick={handleLogout} data-confirmar-saida>
        <LogOut size={16} /> Sair
      </button>
    </div>
  )

  return (
    <div className={styles.wrapper}>
      <div className={styles.mobileBar}>
        <img src="/logo-neuropp.png" alt="Neuropp Mayra Vanessa" />
        <IconButton
          label={menuOpen ? 'Fechar menu' : 'Abrir menu'}
          icon={menuOpen ? <X size={20} /> : <Menu size={20} />}
          onClick={() => setMenuOpen((v) => !v)}
        />
      </div>

      {menuOpen && <div className={styles.overlay} onClick={() => setMenuOpen(false)} />}

      <div className={`${styles.sidebar} ${menuOpen ? styles.open : ''}`} onClick={(event) => {
        if (!event.defaultPrevented && (event.target as Element).closest('a, [data-confirmar-saida]')) setMenuOpen(false)
      }}>
        <SidebarNav items={NAV_ITEMS} logoUrl="/logo-neuropp.png" footer={footer} />
      </div>

      <main className={styles.content}>
        <div className={styles.contentInner}>
          {/* Telas carregadas sob demanda (App.tsx): o menu continua na tela enquanto a página chega. */}
          <Suspense fallback={<p style={{ color: 'var(--np-text-muted)' }}>Carregando…</p>}>
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  )
}
