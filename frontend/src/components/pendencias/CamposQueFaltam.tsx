import { useEffect, useRef, useState } from 'react'
import { ChevronRight, ClipboardList, RefreshCw, Save, X } from 'lucide-react'
import type { CatalogoDoProtocolo } from '../../api/laudoIA'
import { carregarPendencias } from '../../api/carregarPendencias'
import type { GrupoPendente, PendenciasDoLaudo as Pendencias } from '../../api/pendencias'
import { rotuloParaExibicao } from '../../utils/exibicao'
import { Alert, Button, Card, Checkbox, IconButton } from '../ds'
import { CompletarLaudo } from './CompletarLaudo'
import type { ControleDasPendencias } from './PendenciasDoLaudo'

interface Props {
  laudoId: string
  pacienteId: string
  obterCatalogo: () => Promise<CatalogoDoProtocolo>
  /** "Salvar e gerar o protocolo": aplica os dados e gera o documento de novo. */
  onGerar: (reescreverEstudo: boolean) => void
  gerando?: boolean
  /** Incrementado por quem usa (ex.: depois de gerar) para recarregar o resumo. */
  recarregar?: number
}

// Itens de um grupo em uma linha: escalas como contagem, o resto pelo nome.
function descricaoDoGrupo(g: GrupoPendente) {
  const pendentes = g.itens.filter((i) => !i.situacao)
  if (g.escala) return `${pendentes.length} ${pendentes.length === 1 ? 'item sem resposta' : 'itens sem resposta'}`
  // Só o nome principal de cada item, sem repetir ("Metacognição — indicador…"
  // e "Andou com — observações" viram "Metacognição" e "Andou com").
  const nomes = pendentes.map((i) => rotuloParaExibicao(i.rotulo.split(' — ')[0]))
  return [...new Set(nomes)].join(' · ')
}

// Resumo do que falta no laudo ("Há alguns campos que podem ser
// preenchidos:") e, ao clicar, o modal com os campos para preencher.
export function CamposQueFaltam({ laudoId, pacienteId, obterCatalogo, onGerar, gerando = false, recarregar = 0 }: Props) {
  const [pendencias, setPendencias] = useState<Pendencias | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [modal, setModal] = useState<{ secao?: string } | null>(null)
  const [versao, setVersao] = useState(0)

  useEffect(() => {
    carregarPendencias(laudoId, obterCatalogo)
      .then(setPendencias)
      .catch(() => setErro('Não foi possível verificar os campos que faltam.'))
  }, [laudoId, obterCatalogo, recarregar, versao])

  if (erro) return <Alert tone="danger">{erro}</Alert>
  if (!pendencias) return null

  const grupos = pendencias.grupos.filter((g) => g.itens.some((i) => !i.situacao))
  const fechar = () => {
    setModal(null)
    setVersao((v) => v + 1) // atualiza o resumo com o que foi preenchido
  }

  return (
    <>
      <section
        aria-label="Campos que podem ser preenchidos"
        style={{ display: 'grid', gap: 'var(--s-3)', padding: 'var(--s-4)', background: 'var(--primary-soft)', border: '1px solid var(--violeta-200)', borderRadius: 'var(--r-md)' }}
      >
        {grupos.length === 0 ? (
          <div><p style={{ margin: 0 }}>Todos os campos do protocolo estão preenchidos.</p>{pendencias.metodos && <Button onClick={() => setModal({})}>Revisar métodos</Button>}</div>
        ) : (
          <>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--s-3)' }}>
              <h3 style={{ margin: 0, font: 'var(--type-h3)', display: 'flex', alignItems: 'center', gap: 'var(--s-2)' }}>
                <ClipboardList aria-hidden="true" /> Há alguns campos que podem ser preenchidos:
              </h3>
              {pendencias.essenciais.total > 0 && (
                <span style={{ color: 'var(--text-2)', font: 'var(--type-caption)' }}>
                  {pendencias.essenciais.resolvidos} de {pendencias.essenciais.total} essenciais preenchidos
                </span>
              )}
            </div>
            <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 'var(--s-1)' }}>
              {grupos.map((g) => (
                <li key={g.chave}>
                  <button
                    type="button"
                    className="pendencia-resumo"
                    onClick={() => setModal({ secao: g.chave })}
                    style={{ width: '100%', display: 'flex', alignItems: 'flex-start', gap: 'var(--s-2)', textAlign: 'left', padding: 'var(--s-2) var(--s-3)', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', cursor: 'pointer', font: 'inherit', color: 'var(--text)' }}
                  >
                    <span style={{ flex: 1 }}>
                      <strong>{g.titulo}</strong>
                      {!g.essencial && <span style={{ color: 'var(--text-2)' }}> (opcional)</span>}
                      <span style={{ display: 'block', color: 'var(--text-2)', font: 'var(--type-caption)' }}>{descricaoDoGrupo(g)}</span>
                    </span>
                    <ChevronRight aria-hidden="true" style={{ flexShrink: 0, marginTop: 2 }} />
                  </button>
                </li>
              ))}
            </ul>
            <div>
              <Button onClick={() => setModal({})}>Preencher campos</Button>
            </div>
          </>
        )}
      </section>
      {modal && (
        <ModalDosCampos
          laudoId={laudoId}
          pacienteId={pacienteId}
          obterCatalogo={obterCatalogo}
          secaoInicial={modal.secao}
          gerando={gerando}
          onFechar={fechar}
          onGerar={(reescrever) => {
            fechar()
            onGerar(reescrever)
          }}
        />
      )}
    </>
  )
}

interface ModalProps {
  laudoId: string
  pacienteId: string
  obterCatalogo: () => Promise<CatalogoDoProtocolo>
  secaoInicial?: string
  gerando: boolean
  onFechar: () => void
  onGerar: (reescreverEstudo: boolean) => void
}

function ModalDosCampos({ laudoId, pacienteId, obterCatalogo, secaoInicial, gerando, onFechar, onGerar }: ModalProps) {
  const controle = useRef<ControleDasPendencias | null>(null)
  const [reescrever, setReescrever] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const acaoEmCurso = useRef(false)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    const fechar = (e: KeyboardEvent) => e.key === 'Escape' && void salvarEFechar()
    window.addEventListener('keydown', fechar)
    return () => window.removeEventListener('keydown', fechar)
  })

  async function salvarTudo() {
    if (acaoEmCurso.current) return false
    acaoEmCurso.current = true
    setErro(null)
    setSalvando(true)
    const ok = (await controle.current?.salvarAgora()) ?? true
    setSalvando(false)
    acaoEmCurso.current = false
    if (!ok) setErro('Não foi possível salvar. Verifique a conexão e tente de novo.')
    return ok
  }

  async function salvarEFechar() {
    if (await salvarTudo()) onFechar()
  }

  return (
    <div role="dialog" aria-modal="true" aria-label="Campos que faltam no laudo" className="dialog-backdrop" onClick={(e) => e.target === e.currentTarget && void salvarEFechar()}>
      <Card
        title="Campos que faltam no laudo"
        subtitle="Preencha o que tiver; o resto pode ficar para depois. Tudo é salvo automaticamente."
        action={<IconButton label="Fechar" icon={<X />} onClick={() => void salvarEFechar()} />}
        className="dialog-alto"
        style={{ width: 'min(920px, 100%)', maxHeight: '90vh' }}
      >
        <div style={{ overflowY: 'auto', flex: 1, paddingRight: 'var(--s-2)' }}>
          <CompletarLaudo laudoId={laudoId} pacienteId={pacienteId} obterCatalogo={obterCatalogo} controle={controle} secaoInicial={secaoInicial}>
            {({ estudoEditado }) =>
              estudoEditado ? (
                <Checkbox
                  label="Reescrever o estudo de caso com os dados novos"
                  description="Você editou o estudo de caso: sem marcar aqui, o texto atual é mantido."
                  checked={reescrever}
                  onChange={(e) => setReescrever(e.target.checked)}
                />
              ) : null
            }
          </CompletarLaudo>
        </div>
        {erro && <Alert tone="danger">{erro}</Alert>}
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 'var(--s-2)', borderTop: '1px solid var(--divider)', paddingTop: 'var(--s-3)', marginTop: 'var(--s-3)' }}>
          <Button variant="secondary" icon={<Save />} onClick={() => void salvarEFechar()} loading={salvando} loadingLabel="Salvando…">
            Salvar
          </Button>
          <Button
            icon={<RefreshCw />}
            disabled={gerando || salvando}
            onClick={async () => {
              if (await salvarTudo()) onGerar(reescrever)
            }}
          >
            Salvar e gerar o protocolo
          </Button>
        </div>
      </Card>
    </div>
  )
}
