import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import { AuthProvider } from './context/AuthContext'
import ConfiguracoesRegistro from './pages/ConfiguracoesRegistro'
import ConfiguracoesCapa from './pages/ConfiguracoesCapa'
import ConfiguracoesProtocolos from './pages/ConfiguracoesProtocolos'
import ConfiguracoesIA from './pages/ConfiguracoesIA'
import Dashboard from './pages/Dashboard'
import FormulariosResponsaveisPaciente from './pages/FormulariosResponsaveisPaciente'
import Logs from './pages/Logs'
import RelatorioIA from './pages/RelatorioIA'
import SecoesClinicasPaciente from './pages/SecoesClinicasPaciente'
import HistoricoPaciente from './pages/HistoricoPaciente'
import Login from './pages/Login'
import NovoAtendimento from './pages/NovoAtendimento'
import AtendimentoProtocolo from './pages/AtendimentoProtocolo'
import EditorProtocolo from './pages/EditorProtocolo'
import RelatorioPorPdfs from './pages/RelatorioPorPdfs'

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
              <Route path="/relatorio-ia" element={<RelatorioIA />} />
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
