import { ClipboardList, LogOut, Menu, Settings, Users, X } from 'lucide-react'
import { Suspense, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { nomeParaExibicao } from '../utils/exibicao'
import { IconButton, PatientAvatar, SidebarNav } from './ds'
import styles from './Layout.module.css'

const NAV_ITEMS = [
  {
    section: 'Clínica',
    to: '/pacientes', label: 'Pacientes', icon: <Users />, alwaysOpen: true,
    children: [
      { to: '/pacientes', label: 'Todos os pacientes' },
      { to: '/atendimento/novo', label: 'Novo atendimento' },
      { to: '/laudo-ia', label: 'Laudo por IA' },
    ],
  },
  {
    section: 'Sistema',
    to: '/configuracoes', label: 'Configurações', icon: <Settings />,
    children: [
      { to: '/configuracoes/registro', label: 'Registro profissional' },
      { to: '/configuracoes/capa', label: 'Capa dos relatórios' },
      { to: '/configuracoes/protocolos', label: 'Modelos de protocolo' },
      { to: '/configuracoes/ia', label: 'Inteligência artificial' },
    ],
  },
  { section: 'Sistema', to: '/logs', label: 'Registro de atividades', icon: <ClipboardList /> },
]

export default function Layout() {
  const { psychologist, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/')
  }

  const nome = nomeParaExibicao(psychologist?.name)
  const footer = (
    <div className={styles.footer}>
      <PatientAvatar name={nome || '?'} size={40} />
      <div className={styles.user}>
        <span className={styles.userName}>{nome}</span>
        <span className={styles.userRole}>Neuropsicopedagoga</span>
      </div>
      <IconButton label="Sair do sistema" icon={<LogOut />} onClick={handleLogout} data-confirmar-saida />
    </div>
  )

  return (
    <div className={styles.wrapper}>
      <div className={styles.mobileBar}>
        <span className={styles.mobileBrand}>
          <img src="/identidade/logo-marca.png" alt="" />
          Mayra Vanessa
        </span>
        <IconButton
          label={menuOpen ? 'Fechar menu' : 'Abrir menu'}
          icon={menuOpen ? <X /> : <Menu />}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((v) => !v)}
        />
      </div>

      <div className={`${styles.sidebar} ${menuOpen ? styles.open : ''}`} onClick={(event) => {
        if (!event.defaultPrevented && (event.target as Element).closest('a, [data-confirmar-saida]')) setMenuOpen(false)
      }}>
        <SidebarNav items={NAV_ITEMS} logoUrl="/identidade/logo-marca-clara.png" footer={footer} />
      </div>
      {menuOpen && <div className={styles.backdrop} aria-hidden="true" onClick={() => setMenuOpen(false)} />}

      <main className={styles.content}>
        <div className={styles.contentInner}>
          {/* Telas carregadas sob demanda (App.tsx): o menu continua na tela enquanto a página chega. */}
          <Suspense fallback={<p className="text-2">Carregando…</p>}>
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  )
}
