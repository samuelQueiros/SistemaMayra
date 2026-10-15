import { useState } from 'react'
import type { FormEvent } from 'react'
import { UserPlus } from 'lucide-react'
import { ApiError } from '../../api/client'
import { createPatient, uploadPatientPhoto } from '../../api/patients'
import type { Patient } from '../../api/types'
import { Alert, Button, Input, Select, Textarea } from '../ds'

// Cadastro rápido de paciente (nome, nascimento, sexo), usado onde é
// preciso escolher um paciente que ainda não existe — ex.: Relatório Por IA.
export function NovoPacienteForm({ onCriado, onCancelar }: { onCriado: (p: Patient) => void; onCancelar?: () => void }) {
  const [nome, setNome] = useState('')
  const [nascimento, setNascimento] = useState('')
  const [sexo, setSexo] = useState('')
  const [escola, setEscola] = useState('')
  const [observacoes, setObservacoes] = useState('')
  const [fotos, setFotos] = useState<File[]>([])
  const [criado, setCriado] = useState<Patient | null>(null)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  async function salvar(e: FormEvent) {
    e.preventDefault()
    if (salvando) return
    if (!nome.trim() || !nascimento) {
      setErro('Preencha o nome e a data de nascimento.')
      return
    }
    setSalvando(true)
    setErro(null)
    try {
      const paciente = criado ?? await createPatient({ name: nome.trim(), birth_date: nascimento, sex: sexo || undefined, school_info: escola.trim() || undefined, notes: observacoes.trim() || undefined })
      setCriado(paciente)
      for (const foto of fotos) {
        await uploadPatientPhoto(paciente.id, foto)
        setFotos((atuais) => atuais.filter((f) => f !== foto))
      }
      onCriado(paciente)
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : 'Não foi possível cadastrar o paciente.')
      setSalvando(false)
    }
  }

  return (
    <form onSubmit={salvar} style={{ display: 'grid', gap: 'var(--s-4)' }} aria-label="Cadastrar novo paciente">
      <fieldset disabled={salvando || !!criado} style={{ border: 0, padding: 0, margin: 0 }}><div className="form-grid">
        <Input id="novo-paciente-nome" label="Nome do paciente" value={nome} onChange={(e) => setNome(e.target.value)} required />
        <Input id="novo-paciente-nascimento" label="Data de nascimento" type="date" value={nascimento} onChange={(e) => setNascimento(e.target.value)} required />
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
        <Input id="novo-paciente-escola" label="Escola (opcional)" value={escola} onChange={(e) => setEscola(e.target.value)} />
        <Textarea id="novo-paciente-observacoes" label="Informações básicas e observações (opcional)" value={observacoes} onChange={(e) => setObservacoes(e.target.value)} />
      </fieldset>
      <label htmlFor="novo-paciente-fotos">Fotos do paciente (opcional)</label>
      <input id="novo-paciente-fotos" type="file" accept="image/jpeg,image/png,image/webp" multiple disabled={salvando} onChange={(e) => setFotos(Array.from(e.target.files ?? []))} />
      {fotos.length > 0 && <p>{fotos.length} foto(s) aguardando envio: {fotos.map((f) => f.name).join(', ')}</p>}
      {criado && <Alert tone="info">Paciente cadastrado. Conclua o envio das fotos ou continue sem as fotos pendentes.</Alert>}
      {erro && <Alert tone="danger">{erro}</Alert>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-3)' }}>
        <Button type="submit" icon={<UserPlus />} loading={salvando} loadingLabel="Cadastrando…">
          {criado ? 'Enviar fotos pendentes' : 'Cadastrar paciente'}
        </Button>
        {criado && <Button variant="secondary" disabled={salvando} onClick={() => onCriado(criado)}>Continuar sem as fotos pendentes</Button>}
        {onCancelar && !criado && (
          <Button type="button" variant="ghost" onClick={onCancelar} disabled={salvando}>
            Cancelar
          </Button>
        )}
      </div>
    </form>
  )
}
