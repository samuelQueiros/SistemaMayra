import { lazy } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import { AuthProvider } from './context/AuthContext'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'

// Telas carregadas sob demanda: o login e a lista de pacientes não baixam
// o código das demais (editor de protocolo, laudos com Chart.js...).
const ConfiguracoesRegistro = lazy(() => import('./pages/ConfiguracoesRegistro'))
const ConfiguracoesCapa = lazy(() => import('./pages/ConfiguracoesCapa'))
const ConfiguracoesProtocolos = lazy(() => import('./pages/ConfiguracoesProtocolos'))
const ConfiguracoesIA = lazy(() => import('./pages/ConfiguracoesIA'))
const FormulariosResponsaveisPaciente = lazy(() => import('./pages/FormulariosResponsaveisPaciente'))
const Logs = lazy(() => import('./pages/Logs'))
const RedirecionarRelatorioIA = lazy(() => import('./pages/RedirecionarRelatorioIA'))
const LaudoPorIA = lazy(() => import('./pages/LaudoPorIA'))
const SecoesClinicasPaciente = lazy(() => import('./pages/SecoesClinicasPaciente'))
const HistoricoPaciente = lazy(() => import('./pages/HistoricoPaciente'))
const NovoAtendimento = lazy(() => import('./pages/NovoAtendimento'))
const AtendimentoProtocolo = lazy(() => import('./pages/AtendimentoProtocolo'))
const EditorProtocolo = lazy(() => import('./pages/EditorProtocolo'))
const RelatorioPorPdfs = lazy(() => import('./pages/RelatorioPorPdfs'))

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route element={<RequireAuth />}>
            <Route element={<Layout />}>
              <Route path="/pacientes" element={<Dashboard />} />
              <Route path="/dashboard" element={<Navigate to="/pacientes" replace />} />
              <Route path="/pacientes/:id/formularios-responsaveis" element={<FormulariosResponsaveisPaciente />} />
              <Route path="/pacientes/:id/secoes-clinicas" element={<SecoesClinicasPaciente />} />
              <Route path="/relatorio-ia" element={<RedirecionarRelatorioIA />} />
              <Route path="/laudo-ia" element={<LaudoPorIA />} />
              <Route path="/logs" element={<Logs />} />
              <Route path="/atendimento/novo" element={<NovoAtendimento />} />
              <Route path="/pacientes/:id/historico" element={<HistoricoPaciente />} />
              <Route path="/pacientes/:id/relatorio-ia/:laudoId" element={<RelatorioPorPdfs />} />
              <Route path="/atendimento/protocolo/:modeloId" element={<AtendimentoProtocolo />} />
              <Route path="/configuracoes" element={<Navigate to="/configuracoes/registro" replace />} />
              <Route path="/configuracoes/registro" element={<ConfiguracoesRegistro />} />
              <Route path="/configuracoes/capa" element={<ConfiguracoesCapa />} />
              <Route path="/configuracoes/protocolos" element={<ConfiguracoesProtocolos />} />
              <Route path="/configuracoes/ia" element={<ConfiguracoesIA />} />
              <Route path="/configuracoes/protocolos/:id" element={<EditorProtocolo />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
