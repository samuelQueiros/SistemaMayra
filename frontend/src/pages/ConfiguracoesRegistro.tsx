import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { me as getMe, updateProfile } from '../api/auth'
import { Alert, Button, Card, Input, PageHeader } from '../components/ds'

export default function ConfiguracoesRegistro() {
  return (
    <div>
      <PageHeader eyebrow="Configurações" title="Registro Profissional" description="Defina o registro usado na assinatura dos relatórios." />
      <RegistroProfissional />
    </div>
  )
}

function RegistroProfissional() {
  const [value, setValue] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    getMe()
      .then((data) => setValue(data.professional_registration ?? ''))
      .finally(() => setLoading(false))
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setSuccess(false)
    try {
      await updateProfile({ professional_registration: value || null })
      setSuccess(true)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return null

  return (
    <Card title="Registro Profissional" subtitle="Usado no bloco de assinatura do PDF completo (ex.: número do CRP).">
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 'var(--np-space-4)' }}>
        <Input
          id="registro-profissional"
          label="Registro Profissional (Ex.: CRP)"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="CRP 12/34567"
        />
        {success && <Alert tone="success">Registro salvo com sucesso.</Alert>}
        <Button type="submit" disabled={saving} style={{ justifySelf: 'start' }}>
          {saving ? 'Salvando...' : 'Salvar Registro'}
        </Button>
      </form>
    </Card>
  )
}
