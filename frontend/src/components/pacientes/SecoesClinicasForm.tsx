import { useEffect, useState } from 'react'
import { listCidCodes, updateClinicalSections } from '../../api/reports'
import type { CidCode, ClinicalSections, ReportResumo } from '../../api/types'
import { Alert, Button, Card, Checkbox, Input, Textarea } from '../ds'

const ENCAMINHAMENTOS_SUGERIDOS = [
  'Neuropediatra',
  'Avaliação Neuropsicológica',
  'Fonoaudiologia',
  'Terapia Ocupacional',
  'Psicopedagogia',
]

export function SecoesClinicasForm({
  report,
  onSaved,
}: {
  report: ReportResumo
  onSaved: (updated: ReportResumo) => void
}) {
  const atuais = report.clinical_sections_json ?? {}
  const [form, setForm] = useState<ClinicalSections>(atuais)
  const [cidCodes, setCidCodes] = useState<CidCode[]>([])
  const [outraHipotese, setOutraHipotese] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    listCidCodes()
      .then(setCidCodes)
      .catch(() => setCidCodes([]))
  }, [])

  function setCampo<K extends keyof ClinicalSections>(campo: K, valor: ClinicalSections[K]) {
    setForm((prev) => ({ ...prev, [campo]: valor }))
  }

  function toggleEncaminhamento(nome: string) {
    setForm((prev) => {
      const atuais = prev.encaminhamentos ?? []
      const proximos = atuais.includes(nome) ? atuais.filter((e) => e !== nome) : [...atuais, nome]
      return { ...prev, encaminhamentos: proximos }
    })
  }

  function toggleHipotese(label: string, cid: string | null) {
    setForm((prev) => {
      const atuais = prev.diagnostic_hypotheses ?? []
      const jaMarcada = atuais.some((h) => h.label === label)
      const proximas = jaMarcada
        ? atuais.filter((h) => h.label !== label)
        : [...atuais, { label, cid, selected: atuais.length === 0 }]
      return { ...prev, diagnostic_hypotheses: proximas }
    })
  }

  // Só a hipótese marcada aqui aparece no PDF final — as demais ficam
  // registradas como "investigadas", mas não impressas no relatório.
  function selecionarHipotesePrincipal(label: string) {
    setForm((prev) => ({
      ...prev,
      diagnostic_hypotheses: (prev.diagnostic_hypotheses ?? []).map((h) => ({ ...h, selected: h.label === label })),
    }))
  }

  function adicionarOutraHipotese() {
    if (!outraHipotese.trim()) return
    toggleHipotese(outraHipotese.trim(), null)
    setOutraHipotese('')
  }

  async function handleSalvar() {
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      const updated = await updateClinicalSections(report.id, form)
      onSaved(updated)
      setSuccess(true)
    } catch {
      setError('Não foi possível salvar as seções clínicas.')
    } finally {
      setSaving(false)
    }
  }

  const hipotesesMarcadas = new Set((form.diagnostic_hypotheses ?? []).map((h) => h.label))

  return (
    <Card tone="sunken" style={{ boxShadow: 'none', textAlign: 'left' }}>
      <div style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
        <Textarea label="Anamnese Inicial" value={form.anamnese ?? ''} onChange={(e) => setCampo('anamnese', e.target.value)} rows={3} />
        <Textarea
          label="Histórico De Desenvolvimento"
          value={form.historico_desenvolvimento ?? ''}
          onChange={(e) => setCampo('historico_desenvolvimento', e.target.value)}
          rows={3}
        />
        <Textarea
          label="Encaminhamento, Histórico E Queixas"
          value={form.encaminhamento_queixas ?? ''}
          onChange={(e) => setCampo('encaminhamento_queixas', e.target.value)}
          rows={3}
        />
        <Textarea label="Metodologia" value={form.metodologia ?? ''} onChange={(e) => setCampo('metodologia', e.target.value)} rows={2} />
        <Textarea
          label="Estudo De Caso E Observações Clínicas"
          value={form.estudo_de_caso ?? ''}
          onChange={(e) => setCampo('estudo_de_caso', e.target.value)}
          rows={4}
        />

        <div>
          <span style={{ font: 'var(--np-type-label)', color: 'var(--np-text)', display: 'block', marginBottom: 'var(--np-space-2)' }}>
            Hipóteses Diagnósticas Investigadas
          </span>
          <div style={{ display: 'grid', gap: 'var(--np-space-2)' }}>
            {cidCodes.map((c) => (
              <Checkbox
                key={c.label}
                label={`${c.label} (CID: ${c.cid})`}
                checked={hipotesesMarcadas.has(c.label)}
                onChange={() => toggleHipotese(c.label, c.cid)}
              />
            ))}
            {(form.diagnostic_hypotheses ?? [])
              .filter((h) => !cidCodes.some((c) => c.label === h.label))
              .map((h) => (
                <Checkbox key={h.label} label={h.label} checked onChange={() => toggleHipotese(h.label, h.cid ?? null)} />
              ))}
          </div>
          <div style={{ display: 'flex', gap: 'var(--np-space-2)', marginTop: 'var(--np-space-3)' }}>
            <Input placeholder="Outra hipótese..." value={outraHipotese} onChange={(e) => setOutraHipotese(e.target.value)} style={{ flex: 1 }} />
            <Button type="button" variant="outline" onClick={adicionarOutraHipotese}>
              Adicionar
            </Button>
          </div>

          {(form.diagnostic_hypotheses ?? []).length > 0 && (
            <div style={{ marginTop: 'var(--np-space-4)' }}>
              <span style={{ font: 'var(--np-type-label)', color: 'var(--np-text)', display: 'block', marginBottom: 'var(--np-space-2)' }}>
                Hipótese Selecionada Para Este Paciente (única que aparece no PDF)
              </span>
              <div style={{ display: 'grid', gap: 'var(--np-space-2)' }}>
                {(form.diagnostic_hypotheses ?? []).map((h) => (
                  <label key={h.label} style={{ display: 'flex', gap: 'var(--np-space-2)', alignItems: 'center', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="hipotese-principal"
                      checked={!!h.selected}
                      onChange={() => selecionarHipotesePrincipal(h.label)}
                    />
                    <span>
                      {h.label}
                      {h.cid ? ` (CID: ${h.cid})` : ''}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        <Textarea
          label="Plano De Intervenção"
          value={form.plano_intervencao ?? ''}
          onChange={(e) => setCampo('plano_intervencao', e.target.value)}
          rows={3}
        />

        <div>
          <span style={{ font: 'var(--np-type-label)', color: 'var(--np-text)', display: 'block', marginBottom: 'var(--np-space-2)' }}>
            Encaminhamentos
          </span>
          <div style={{ display: 'grid', gap: 'var(--np-space-2)' }}>
            {ENCAMINHAMENTOS_SUGERIDOS.map((nome) => (
              <Checkbox
                key={nome}
                label={nome}
                checked={(form.encaminhamentos ?? []).includes(nome)}
                onChange={() => toggleEncaminhamento(nome)}
              />
            ))}
          </div>
        </div>

        <Textarea
          label="Considerações Finais"
          value={form.consideracoes_finais ?? ''}
          onChange={(e) => setCampo('consideracoes_finais', e.target.value)}
          rows={3}
        />

        {error && <Alert tone="danger">{error}</Alert>}
        {success && <Alert tone="success">Seções clínicas salvas com sucesso.</Alert>}
        <Button type="button" onClick={handleSalvar} disabled={saving} style={{ justifySelf: 'start' }}>
          {saving ? 'Salvando...' : 'Salvar Seções Clínicas'}
        </Button>
      </div>
    </Card>
  )
}
