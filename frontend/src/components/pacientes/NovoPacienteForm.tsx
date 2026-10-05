import { useState } from 'react'
import type { FormEvent } from 'react'
import { UserPlus } from 'lucide-react'
import { ApiError } from '../../api/client'
import { createPatient } from '../../api/patients'
import type { Patient } from '../../api/types'
import { Alert, Button, Input, Select } from '../ds'

// Cadastro rápido de paciente (nome, nascimento, sexo), usado onde é
// preciso escolher um paciente que ainda não existe — ex.: Relatório Por IA.
export function NovoPacienteForm({ onCriado, onCancelar }: { onCriado: (p: Patient) => void; onCancelar?: () => void }) {
  const [nome, setNome] = useState('')
  const [nascimento, setNascimento] = useState('')
  const [sexo, setSexo] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  async function salvar(e: FormEvent) {
    e.preventDefault()
    if (!nome.trim() || !nascimento) {
      setErro('Preencha o nome e a data de nascimento.')
      return
    }
    setSalvando(true)
    setErro(null)
    try {
      onCriado(await createPatient({ name: nome.trim(), birth_date: nascimento, sex: sexo || undefined }))
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível cadastrar o paciente.')
      setSalvando(false)
    }
  }

  return (
    <form onSubmit={salvar} style={{ display: 'grid', gap: 'var(--np-space-4)' }} aria-label="Cadastrar novo paciente">
      <div style={{ display: 'grid', gap: 'var(--np-space-4)', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
        <Input id="novo-paciente-nome" label="Nome Do Paciente" value={nome} onChange={(e) => setNome(e.target.value)} required />
        <Input id="novo-paciente-nascimento" label="Data De Nascimento" type="date" value={nascimento} onChange={(e) => setNascimento(e.target.value)} required />
        <Select
          id="novo-paciente-sexo"
          label="Sexo"
          placeholder="Selecione"
          value={sexo}
          options={[
            { value: 'Feminino', label: 'Feminino' },
            { value: 'Masculino', label: 'Masculino' },
          ]}
          onChange={(e) => setSexo(e.target.value)}
        />
      </div>
      {erro && <Alert tone="danger">{erro}</Alert>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--np-space-3)' }}>
        <Button type="submit" icon={<UserPlus size={16} />} disabled={salvando}>
          {salvando ? 'Cadastrando…' : 'Cadastrar Paciente'}
        </Button>
        {onCancelar && (
          <Button type="button" variant="ghost" onClick={onCancelar} disabled={salvando}>
            Cancelar
          </Button>
        )}
      </div>
    </form>
  )
}
