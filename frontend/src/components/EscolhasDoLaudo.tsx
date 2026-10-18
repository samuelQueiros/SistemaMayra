import { Checkbox } from './ds'
import { ENCAMINHAMENTOS, GRUPOS_CID, textoDaHipotese } from '../laudo/hipotesesCid'

interface EscolhasDoLaudoProps {
  hipoteses: string[]
  encaminhamentos: string[]
  onHipoteses: (ids: string[]) => void
  onEncaminhamentos: (ids: string[]) => void
  desabilitado?: boolean
}

function alternar(lista: string[], id: string, marcar: boolean): string[] {
  return marcar ? [...lista.filter((i) => i !== id), id] : lista.filter((i) => i !== id)
}

// Laudo Por IA: a psicóloga marca as hipóteses diagnósticas (com os subtipos
// da CID-11) e os encaminhamentos antes de enviar os PDFs — a IA não escolhe.
export function EscolhasDoLaudo({ hipoteses, encaminhamentos, onHipoteses, onEncaminhamentos, desabilitado = false }: EscolhasDoLaudoProps) {
  function marcarHipotese(id: string, marcar: boolean, subtipos: string[] = []) {
    // Desmarcar a hipótese principal desmarca os subtipos.
    const sem = marcar ? hipoteses : hipoteses.filter((i) => !subtipos.includes(i))
    onHipoteses(alternar(sem, id, marcar))
  }

  return (
    <div style={{ display: 'grid', gap: 'var(--s-5)' }}>
      <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'grid', gap: 'var(--s-3)' }}>
        <legend className="field-label" style={{ marginBottom: 'var(--s-2)' }}>Hipóteses diagnósticas</legend>
        {GRUPOS_CID.map((grupo) => (
          <div key={grupo.titulo} style={{ display: 'grid', gap: 'var(--s-2)' }}>
            <strong style={{ fontSize: 'var(--fs-label)', color: 'var(--text-2)' }}>{grupo.titulo}</strong>
            {grupo.hipoteses.map((h) => {
              const marcada = hipoteses.includes(h.id)
              const ids = (h.subtipos ?? []).map((s) => s.id)
              return (
                <div key={h.id} style={{ display: 'grid', gap: 'var(--s-2)' }}>
                  <Checkbox label={textoDaHipotese(h)} checked={marcada} disabled={desabilitado} onChange={(e) => marcarHipotese(h.id, e.target.checked, ids)} />
                  {marcada && h.subtipos && (
                    <div role="group" aria-label={`Subtipos de ${h.rotulo}`} style={{ display: 'grid', gap: 'var(--s-2)', paddingLeft: 'var(--s-6)', borderLeft: '2px solid var(--violeta-200)', marginLeft: 'var(--s-3)' }}>
                      {h.subtipos.map((s) => (
                        <Checkbox key={s.id} label={textoDaHipotese(s)} checked={hipoteses.includes(s.id)} disabled={desabilitado} onChange={(e) => onHipoteses(alternar(hipoteses, s.id, e.target.checked))} />
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ))}
      </fieldset>
      <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'grid', gap: 'var(--s-2)' }}>
        <legend className="field-label" style={{ marginBottom: 'var(--s-2)' }}>Encaminhamentos (saem em tópicos no final do relatório)</legend>
        {ENCAMINHAMENTOS.map((e) => (
          <Checkbox key={e.id} label={e.rotulo} checked={encaminhamentos.includes(e.id)} disabled={desabilitado} onChange={(ev) => onEncaminhamentos(alternar(encaminhamentos, e.id, ev.target.checked))} />
        ))}
      </fieldset>
    </div>
  )
}
