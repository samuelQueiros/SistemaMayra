import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import { AuthProvider } from './context/AuthContext'
import Configuracoes from './pages/Configuracoes'
import Dashboard from './pages/Dashboard'
import HistoricoPaciente from './pages/HistoricoPaciente'
import Login from './pages/Login'
import ModelosDeLaudo from './pages/ModelosDeLaudo'
import NovoAtendimento from './pages/NovoAtendimento'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route element={<RequireAuth />}>
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/atendimento/novo" element={<NovoAtendimento />} />
              <Route path="/modelos" element={<ModelosDeLaudo />} />
              <Route path="/pacientes/:id/historico" element={<HistoricoPaciente />} />
              <Route path="/configuracoes" element={<Configuracoes />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
