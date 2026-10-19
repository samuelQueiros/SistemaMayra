import { Select } from './ds'
import type { CampoDoCatalogo, CatalogoDoProtocolo } from '../api/laudoIA'

interface DadosDaProfissionalProps {
  catalogo: CatalogoDoProtocolo | null
  valores: Record<string, string>
  onChange: (valores: Record<string, string>) => void
  desabilitado?: boolean
}

// Mesmas situações em que o formulário mostra a idade do desfralde.
const DESFRALDE_COM_IDADE = ['Controle Total', 'Controle Diurno', 'Escapes']

function opcoes(catalogo: CatalogoDoProtocolo, id: string) {
  const campo = (catalogo.campos as CampoDoCatalogo[]).find((c) => c.id === id)
  return (campo?.opcoes ?? []).map((o) => ({ value: o.valor, label: o.rotulo || o.valor }))
}

// Relatório por IA: desfralde, ano escolar e desempenho em cada habilidade do
// ano são escolhidos pela psicóloga antes de enviar os PDFs. As opções vêm do
// próprio formulário (catálogo); a IA recebe as respostas como dados
// confirmados e não altera esses campos.
export function DadosDaProfissional({ catalogo, valores, onChange, desabilitado = false }: DadosDaProfissionalProps) {
  if (!catalogo) return <p role="status">Carregando as opções do protocolo…</p>

  const mudar = (id: string, valor: string) => {
    const novos = { ...valores, [id]: valor }
    if (!valor) delete novos[id]
    if (id === 'desfralde' && !DESFRALDE_COM_IDADE.includes(valor)) {
      delete novos.desfraldeAno
      delete novos.desfraldeMes
    }
    // Outro ano escolar, outra lista de habilidades.
    if (id === 'anoEscolar') Object.keys(novos).filter((k) => k.startsWith('hab_status_')).forEach((k) => delete novos[k])
    onChange(novos)
  }
  const ano = valores.anoEscolar ?? ''
  const habilidades = (ano && catalogo.habilidadesPorAno?.[ano]) || []
  const status = opcoes(catalogo, 'hab_status_0')

  return (
    <div style={{ display: 'grid', gap: 'var(--s-5)' }}>
      <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'grid', gap: 'var(--s-3)' }}>
        <legend className="field-label" style={{ marginBottom: 'var(--s-2)' }}>Desfralde</legend>
        <div className="form-grid">
          <Select id="dados-desfralde" label="Situação" value={valores.desfralde ?? ''} options={opcoes(catalogo, 'desfralde')} disabled={desabilitado} onChange={(e) => mudar('desfralde', e.target.value)} />
          {DESFRALDE_COM_IDADE.includes(valores.desfralde ?? '') && (
            <>
              <Select id="dados-desfralde-ano" label="Idade do desfralde (anos)" value={valores.desfraldeAno ?? ''} options={opcoes(catalogo, 'desfraldeAno')} disabled={desabilitado} onChange={(e) => mudar('desfraldeAno', e.target.value)} />
              <Select id="dados-desfralde-mes" label="Idade do desfralde (meses)" value={valores.desfraldeMes ?? ''} options={opcoes(catalogo, 'desfraldeMes')} disabled={desabilitado} onChange={(e) => mudar('desfraldeMes', e.target.value)} />
            </>
          )}
        </div>
      </fieldset>
      <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'grid', gap: 'var(--s-3)' }}>
        <legend className="field-label" style={{ marginBottom: 'var(--s-2)' }}>Ano escolar e habilidades acadêmicas</legend>
        <div className="form-grid">
          <Select id="dados-ano-escolar" label="Ano escolar" value={ano} options={opcoes(catalogo, 'anoEscolar')} disabled={desabilitado} onChange={(e) => mudar('anoEscolar', e.target.value)} />
        </div>
        {habilidades.length > 0 && (
          <div style={{ display: 'grid', gap: 'var(--s-3)' }}>
            {habilidades.map((nome, i) => (
              <Select key={`${ano}-${i}`} id={`dados-hab-${i}`} label={nome} value={valores[`hab_status_${i}`] ?? ''} options={status} disabled={desabilitado} onChange={(e) => mudar(`hab_status_${i}`, e.target.value)} />
            ))}
          </div>
        )}
      </fieldset>
    </div>
  )
}
