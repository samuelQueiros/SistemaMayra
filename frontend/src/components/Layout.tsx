import { ClipboardPlus, FileStack, LogOut, Menu, Settings, Users, X } from 'lucide-react'
import { useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { IconButton, SidebarNav } from './ds'
import styles from './Layout.module.css'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Pacientes', icon: <Users size={18} /> },
  { to: '/atendimento/novo', label: 'Novo Atendimento', icon: <ClipboardPlus size={18} /> },
  { to: '/modelos', label: 'Modelos De Laudo', icon: <FileStack size={18} /> },
  { to: '/configuracoes', label: 'Configurações', icon: <Settings size={18} /> },
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
      <button type="button" className={styles.logoutButton} onClick={handleLogout}>
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

      <div className={`${styles.sidebar} ${menuOpen ? styles.open : ''}`} onClick={() => setMenuOpen(false)}>
        <SidebarNav items={NAV_ITEMS} logoUrl="/logo-neuropp.png" footer={footer} />
      </div>

      <main className={styles.content}>
        <div className={styles.contentInner}>
          <Outlet />
        </div>
      </main>
    </div>
  )
}
