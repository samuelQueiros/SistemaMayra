import { Navigate, useLocation } from 'react-router-dom'

// Mantém links antigos funcionando, inclusive o paciente selecionado.
export default function RedirecionarRelatorioIA() {
  const { search } = useLocation()
  return <Navigate to={`/laudo-ia${search}`} replace />
}
