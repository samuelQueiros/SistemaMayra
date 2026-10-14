import { Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../../api/client'
import {
  createGuardianForm,
  deleteGuardianForm,
  listGuardianForms,
  rejectGuardianForm,
  uploadGuardianFormFile,
  validateGuardianForm,
} from '../../api/guardianForms'
import type { GuardianFormSubmission } from '../../api/types'
import { Alert, Badge, Button, Card, Input } from '../ds'


const STATUS_TONE: Record<GuardianFormSubmission['status'], 'warning' | 'success' | 'danger'> = {
  pendente: 'warning',
  validado: 'success',
  rejeitado: 'danger',
}
const STATUS_LABEL: Record<GuardianFormSubmission['status'], string> = {
  pendente: 'Pendente de validação',
  validado: 'Validado',
  rejeitado: 'Rejeitado',
}

// Ponto 4 da revisão de relatórios: registro de formulários preenchidos
// pelos responsáveis/família fora do sistema (papel, verbal). Preserva o
// original como anexo, quem preencheu e quando, e exige validação
// explícita da psicóloga antes de ela considerar os dados confiáveis para
// lançar no laudo/gráficos — nada aqui alimenta o laudo automaticamente.
export function FormulariosDeResponsaveis({ patientId }: { patientId: string }) {
  const [itens, setItens] = useState<GuardianFormSubmission[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [salvando, setSalvando] = useState(false)
  const [form, setForm] = useState({ kind: '', respondent_name: '', respondent_relation: '', filled_at: '', notes: '' })
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({})

  function carregar() {
    setLoading(true)
    listGuardianForms(patientId)
      .then(setItens)
      .catch(() => setError('Não foi possível carregar os formulários dos responsáveis.'))
      .finally(() => setLoading(false))
  }

  useEffect(carregar, [patientId])

  async function handleCriar() {
    if (!form.kind.trim() || !form.respondent_name.trim() || !form.filled_at) {
      setError('Preencha ao menos o formulário, quem preencheu e a data.')
      return
    }
    setSalvando(true)
    setError(null)
    try {
      const criado = await createGuardianForm(patientId, {
        kind: form.kind.trim(),
        respondent_name: form.respondent_name.trim(),
        respondent_relation: form.respondent_relation.trim() || undefined,
        filled_at: form.filled_at,
        notes: form.notes.trim() || undefined,
      })
      setItens((prev) => [criado, ...prev])
      setForm({ kind: '', respondent_name: '', respondent_relation: '', filled_at: '', notes: '' })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível registrar o formulário.')
    } finally {
      setSalvando(false)
    }
  }

  async function handleUploadArquivo(submissionId: string) {
    const file = fileInputRefs.current[submissionId]?.files?.[0]
    if (!file) return
    try {
      const atualizado = await uploadGuardianFormFile(patientId, submissionId, file)
      setItens((prev) => prev.map((i) => (i.id === submissionId ? atualizado : i)))
    } catch {
      setError('Não foi possível anexar o formulário original.')
    }
  }

  async function handleValidar(submissionId: string) {
    try {
      const atualizado = await validateGuardianForm(patientId, submissionId)
      setItens((prev) => prev.map((i) => (i.id === submissionId ? atualizado : i)))
    } catch {
      setError('Não foi possível validar este formulário.')
    }
  }

  async function handleRejeitar(submissionId: string) {
    try {
      const atualizado = await rejectGuardianForm(patientId, submissionId)
      setItens((prev) => prev.map((i) => (i.id === submissionId ? atualizado : i)))
    } catch {
      setError('Não foi possível rejeitar este formulário.')
    }
  }

  async function handleExcluir(submissionId: string) {
    try {
      await deleteGuardianForm(patientId, submissionId)
      setItens((prev) => prev.filter((i) => i.id !== submissionId))
    } catch {
      setError('Não foi possível excluir este registro.')
    }
  }

  if (loading) return null

  return (
    <Card
      title="Formulários dos responsáveis"
      subtitle="Registre o que a família preencheu fora do sistema (papel, verbal). Só considere validado o que já foi conferido — isto não lança nada automaticamente no laudo ou nos gráficos."
      style={{ marginTop: 'var(--s-5)' }}
    >
      {error && <Alert tone="danger" style={{ marginBottom: 'var(--s-3)' }}>{error}</Alert>}

      <div style={{ display: 'grid', gap: 'var(--s-3)' }}>
        {itens.length === 0 && (
          <p className="caption" style={{ margin: 0 }}>
            Nenhum formulário de responsável registrado ainda.
          </p>
        )}
        {itens.map((item) => (
          <Card key={item.id} tone="sunken" padding="var(--s-4)">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--s-2)' }}>
              <div>
                <strong>{item.kind}</strong>
                <div className="caption">
                  Preenchido por {item.respondent_name}
                  {item.respondent_relation ? ` (${item.respondent_relation})` : ''} em{' '}
                  {new Date(item.filled_at + 'T00:00:00').toLocaleDateString('pt-BR')}
                </div>
                {item.notes && <div style={{ font: 'var(--type-caption)', marginTop: 4 }}>{item.notes}</div>}
              </div>
              <Badge tone={STATUS_TONE[item.status]}>{STATUS_LABEL[item.status]}</Badge>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s-2)', flexWrap: 'wrap', marginTop: 'var(--s-3)' }}>
              {item.file_path ? (
                <a
                  href={`/api/patients/${patientId}/guardian-forms/${item.id}/file`}
                  target="_blank"
                  rel="noreferrer"
                  style={{ font: 'var(--type-label)' }}
                >
                  Ver formulário original anexado
                </a>
              ) : (
                <>
                  <input
                    type="file"
                    accept=".jpg,.jpeg,.png,.webp,.pdf"
                    ref={(el) => {
                      fileInputRefs.current[item.id] = el
                    }}
                    style={{ maxWidth: 260 }}
                    aria-label={`Arquivo original de ${item.kind}`}
                  />
                  <Button type="button" size="sm" variant="secondary" onClick={() => handleUploadArquivo(item.id)}>
                    Anexar original
                  </Button>
                </>
              )}
              {item.status === 'pendente' && (
                <>
                  <Button type="button" size="sm" onClick={() => handleValidar(item.id)}>
                    Validar
                  </Button>
                  <Button type="button" size="sm" variant="ghost" onClick={() => handleRejeitar(item.id)}>
                    Rejeitar
                  </Button>
                </>
              )}
              <Button size="sm" variant="danger-ghost" icon={<Trash2 />} onClick={() => handleExcluir(item.id)} style={{ marginLeft: 'auto' }}>
                Excluir
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <h3 style={{ margin: 'var(--s-6) 0 var(--s-3)', font: 'var(--type-h3)' }}>Registrar formulário preenchido</h3>
      <div className="form-grid">
        <Input
          id="responsavel-formulario"
          label="Formulário"
          required
          placeholder="Ex.: SNAP-IV, anamnese"
          value={form.kind}
          onChange={(e) => setForm((f) => ({ ...f, kind: e.target.value }))}
        />
        <Input
          id="responsavel-quem"
          label="Quem preencheu"
          required
          value={form.respondent_name}
          onChange={(e) => setForm((f) => ({ ...f, respondent_name: e.target.value }))}
        />
        <Input
          id="responsavel-relacao"
          label="Relação com o paciente"
          placeholder="Ex.: mãe, pai"
          value={form.respondent_relation}
          onChange={(e) => setForm((f) => ({ ...f, respondent_relation: e.target.value }))}
        />
        <Input
          id="responsavel-data"
          label="Data do preenchimento"
          required
          type="date"
          value={form.filled_at}
          onChange={(e) => setForm((f) => ({ ...f, filled_at: e.target.value }))}
        />
        <Input
          id="responsavel-observacoes"
          label="Observações (opcional)"
          value={form.notes}
          onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
          style={{ gridColumn: '1 / -1' }}
        />
      </div>
      <Button onClick={handleCriar} loading={salvando} loadingLabel="Registrando…" style={{ marginTop: 'var(--s-4)' }}>
        Registrar formulário
      </Button>
    </Card>
  )
}
