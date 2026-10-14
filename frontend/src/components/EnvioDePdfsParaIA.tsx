import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { ApiError } from '../api/client'
import { MAXIMO_DE_PDFS, gerarRelatorioPorPdfs, problemaNosArquivos } from '../api/relatoriosPdf'
import { Alert, Button, Card, Textarea } from './ds'
import { SeletorDePdfs } from './SeletorDePdfs'

// Histórico do paciente: anexar de 1 a 6 PDFs de respostas (Google Forms)
// para a IA gerar o relatório por área/tema, que abre na tela de revisão.
export function EnvioDePdfsParaIA({ patientId, abertoInicial = false }: { patientId: string; abertoInicial?: boolean }) {
  const navigate = useNavigate()
  const [aberto, setAberto] = useState(abertoInicial)
  const [arquivos, setArquivos] = useState<File[]>([])
  const [observacoes, setObservacoes] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [gerando, setGerando] = useState(false)

  async function gerar() {
    setErro(null)
    setGerando(true)
    try {
      const laudo = await gerarRelatorioPorPdfs(patientId, arquivos, observacoes)
      navigate(`/pacientes/${patientId}/relatorio-ia/${laudo.id}`)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível gerar o relatório.')
      setGerando(false)
    }
  }

  if (!aberto) {
    return (
      <Card style={{ marginTop: 'var(--s-5)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-4)', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontWeight: 600 }}>Relatório por IA a partir de formulários</div>
            <div style={{ font: 'var(--type-caption)', color: 'var(--text-2)' }}>
              Anexe até {MAXIMO_DE_PDFS} PDFs com as respostas (ex.: Google Forms). A IA lê perguntas e respostas e monta o relatório por área, com gráficos, para você revisar.
            </div>
          </div>
          <Button type="button" icon={<Sparkles size={16} />} onClick={() => setAberto(true)}>
            Relatório por IA (PDFs)
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card
      title="Relatório por IA a partir de formulários"
      subtitle={`Anexe de 1 a ${MAXIMO_DE_PDFS} PDFs com as respostas. No Google Forms: aba Respostas → Individual → ícone de impressora → Salvar como PDF.`}
      style={{ marginTop: 'var(--s-5)' }}
    >
      <div style={{ display: 'grid', gap: 'var(--s-4)' }}>
        <SeletorDePdfs
          arquivos={arquivos}
          onChange={setArquivos}
          maximo={MAXIMO_DE_PDFS}
          problema={problemaNosArquivos}
          onErro={setErro}
          desabilitado={gerando}
        />

        <Textarea
          id="observacoes-ia"
          label="Observações para a IA (opcional)"
          rows={2}
          value={observacoes}
          onChange={(e) => setObservacoes(e.target.value)}
          placeholder="Ex.: dar atenção especial à comunicação e ao comportamento em sala."
        />
        <Alert tone="info">
          Os PDFs são enviados ao provedor de IA configurado em Configurações → Inteligência Artificial para leitura. Revise sempre o relatório antes de exportar.
        </Alert>
        {erro && <Alert tone="danger">{erro}</Alert>}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s-3)' }}>
          <Button type="button" icon={<Sparkles size={16} />} onClick={gerar} disabled={!arquivos.length || gerando}>
            {gerando ? 'Lendo os formulários… (pode levar 1 a 2 minutos)' : 'Gerar relatório'}
          </Button>
          <Button type="button" variant="ghost" disabled={gerando} onClick={() => setAberto(false)}>
            Cancelar
          </Button>
        </div>
      </div>
    </Card>
  )
}
