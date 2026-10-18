import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as patients from '../api/patients'
import * as laudoIA from '../api/laudoIA'
import * as reports from '../api/reports'
import * as pendencias from '../api/pendencias'
import LaudoPorIA from './LaudoPorIA'

vi.mock('../api/patients', () => ({ listPatients: vi.fn(), createPatient: vi.fn() }))
vi.mock('../api/reports', () => ({ getReport: vi.fn(), getReportResumo: vi.fn(), downloadReportDocx: vi.fn(), downloadReportPdf: vi.fn() }))
vi.mock('../api/laudoIA', async (original) => ({ ...(await original<typeof laudoIA>()), gerarLaudoPorIA: vi.fn(), acompanharGeracao: vi.fn() }))
vi.mock('../api/anexos', async (original) => ({ ...(await original<object>()), listarAnexos: vi.fn().mockResolvedValue([]) }))
vi.mock('../api/pendencias', () => ({
  getPendencias: vi.fn().mockResolvedValue({ essenciais: { total: 0, resolvidos: 0 }, grupos: [], escalas_para_adicionar: [], estudo_de_caso: { editado: false } }),
  atualizarLaudo: vi.fn(),
}))

const paciente = { id: 'p1', name: 'Bia Lima', birth_date: '2020-01-10', notes: null, sex: 'Feminino', school_info: null }
const catalogo = { campos: [{ id: 'parto', tipo: 'opcao' }], contexto: '' }

function mensagemDoFormulario(data: unknown) {
  act(() => {
    window.dispatchEvent(new MessageEvent('message', { data, origin: window.location.origin }))
  })
}

async function prepararEGerar() {
  render(
    <MemoryRouter initialEntries={['/laudo-ia?paciente=p1']}>
      <LaudoPorIA />
    </MemoryRouter>,
  )
  const pdf = new File(['%PDF-1.4'], 'anamnese.pdf', { type: 'application/pdf' })
  fireEvent.change(await screen.findByTestId('arquivos-pdf'), { target: { files: [pdf] } })
  fireEvent.change(screen.getByLabelText(/Data do relatório/), { target: { value: '2026-10-15' } })
  fireEvent.change(screen.getByLabelText(/Cidade do relatório/), { target: { value: 'Gama – DF' } })
  fireEvent.click(screen.getByRole('button', { name: 'Gerar relatório com IA' }))
  return pdf
}

describe('Relatório por IA', () => {
  beforeEach(() => {
    vi.mocked(patients.listPatients).mockResolvedValue([paciente])
    vi.mocked(reports.getReportResumo).mockImplementation((id) => reports.getReport(id))
    vi.mocked(reports.downloadReportDocx).mockResolvedValue(undefined)
  })

  it('lê o catálogo no formulário, chama a IA e gera o documento pelo formulário', async () => {
    vi.mocked(laudoIA.gerarLaudoPorIA).mockResolvedValue({ id: 'l1' } as laudoIA.LaudoPorIA)
    vi.mocked(reports.getReport).mockResolvedValue({
      id: 'l1',
      answers_json: { nomePaciente: 'Bia Lima' },
      computed_json: { origem: 'ia_pdf', arquivos: [], lacunas: ['Sem dados do Portage.'], campos_descartados: [] },
      generated_text: '<html><body>Laudo</body></html>',
    } as never)
    const pdf = await prepararEGerar()

    expect(screen.getByTitle('Gerando o laudo')).toHaveAttribute('src', '/formulario-novo-paciente.html?paciente=p1&modo=catalogo')
    mensagemDoFormulario({ tipo: 'laudo-ia:catalogo', catalogo })

    expect(await screen.findByTitle('Gerando o laudo')).toHaveAttribute('src', '/formulario-novo-paciente.html?laudo=l1&modo=gerar&tentativa=1')
    expect(laudoIA.gerarLaudoPorIA).toHaveBeenCalledWith('p1', [pdf], '', catalogo, expect.any(Function), '2026-10-15', 'Gama – DF', { hipoteses: [], encaminhamentos: [] })
    mensagemDoFormulario({ tipo: 'laudo-ia:gerado', laudoId: 'l1' })

    expect(await screen.findByText('Laudo gerado')).toBeInTheDocument()
    expect(await screen.findByText('Todos os campos do protocolo estão preenchidos.')).toBeInTheDocument()
    // A prévia só aparece quando ela pede.
    expect(screen.queryByTitle('Pré-visualização do laudo')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Ver prévia do relatório' }))
    expect(await screen.findByTitle('Pré-visualização do laudo')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Baixar Word (DOCX)' }))
    expect(reports.downloadReportDocx).toHaveBeenCalledWith('l1', 'laudo_ia_Bia_Lima.docx')
  })

  it('se o documento falhar duas vezes, avisa e permite gerar só o documento de novo', async () => {
    vi.mocked(laudoIA.gerarLaudoPorIA).mockResolvedValue({ id: 'l2' } as laudoIA.LaudoPorIA)
    vi.mocked(reports.getReport).mockResolvedValue({
      id: 'l2',
      answers_json: {},
      computed_json: { origem: 'ia_pdf', arquivos: [], lacunas: [], campos_descartados: [] },
      generated_text: null,
    } as never)
    await prepararEGerar()
    mensagemDoFormulario({ tipo: 'laudo-ia:catalogo', catalogo })
    await screen.findByTitle('Gerando o laudo')
    await act(async () => {})
    mensagemDoFormulario({ tipo: 'laudo-ia:etapa', etapa: 'salvando as respostas' })
    expect(await screen.findByText(/salvando as respostas/)).toBeInTheDocument()
    mensagemDoFormulario({ tipo: 'laudo-ia:erro', mensagem: 'Falhou ao gerar.' })
    // Segunda tentativa automática, num iframe novo.
    await waitFor(() => expect(screen.getByTitle('Gerando o laudo')).toHaveAttribute('src', '/formulario-novo-paciente.html?laudo=l2&modo=gerar&tentativa=2'))
    await act(async () => {})
    mensagemDoFormulario({ tipo: 'laudo-ia:erro', mensagem: 'Falhou ao gerar.' })

    expect(await screen.findByText(/Falhou ao gerar\./)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Abrir no formulário' })).toHaveAttribute('href', '/atendimento/novo?laudo=l2')
    expect(laudoIA.gerarLaudoPorIA).toHaveBeenCalledTimes(1)

    // Refaz só o documento: sem chamar a IA de novo.
    fireEvent.click(screen.getByRole('button', { name: 'Gerar o documento de novo' }))
    await waitFor(() => expect(screen.getByTitle('Gerando o laudo')).toHaveAttribute('src', '/formulario-novo-paciente.html?laudo=l2&modo=gerar&tentativa=1'))
    await act(async () => {})
    mensagemDoFormulario({ tipo: 'laudo-ia:gerado', laudoId: 'l2' })
    expect(await screen.findByText('Laudo gerado')).toBeInTheDocument()
    expect(laudoIA.gerarLaudoPorIA).toHaveBeenCalledTimes(1)
  })

  it('mostra o andamento por etapa e cada documento enquanto a IA trabalha', async () => {
    let terminar: (v: { id: string }) => void = () => {}
    vi.mocked(laudoIA.gerarLaudoPorIA).mockImplementation((_p, _a, _o, _c, aoProgredir) => {
      aoProgredir?.({
        id: 'j1',
        status: 'processando',
        mensagem: 'Lendo documento 2 de 3…',
        documentos: [
          { nome: 'mae.pdf', status: 'lido' },
          { nome: 'escola.pdf', status: 'lendo' },
          { nome: 'cars.pdf', status: 'aguardando' },
        ],
        report_id: null,
        erro: null,
      })
      return new Promise((resolve) => (terminar = resolve))
    })
    await prepararEGerar()
    mensagemDoFormulario({ tipo: 'laudo-ia:catalogo', catalogo })

    expect(await screen.findByText('Lendo documento 2 de 3…')).toBeInTheDocument()
    expect(screen.getByText('mae.pdf: lido ✓')).toBeInTheDocument()
    expect(screen.getByText('escola.pdf: lendo…')).toBeInTheDocument()
    await act(async () => terminar({ id: 'l3' }))
  })

  it('mostra a mensagem da geração quando um documento não pôde ser lido', async () => {
    vi.mocked(laudoIA.gerarLaudoPorIA).mockRejectedValue(new Error("Não foi possível ler 'escola.pdf' (o provedor de IA demorou demais para responder)."))
    await prepararEGerar()
    mensagemDoFormulario({ tipo: 'laudo-ia:catalogo', catalogo })

    expect(await screen.findByText(/Não foi possível ler 'escola\.pdf'/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Gerar relatório com IA' })).toBeEnabled()
  })

  it('abre direto nos campos que faltam e "Atualizar relatório" inclui os dados e gera o documento de novo', async () => {
    vi.mocked(reports.getReport).mockResolvedValue({
      id: 'l5',
      answers_json: { nomePaciente: 'Bia Lima' },
      computed_json: { origem: 'ia_pdf', arquivos: [], lacunas: [], campos_descartados: [] },
      generated_text: '<html><body>Laudo</body></html>',
    } as never)
    vi.mocked(pendencias.atualizarLaudo).mockResolvedValue({ job_id: 'j9', campos_aplicados: 2, estudo: 'reescrevendo' })
    vi.mocked(laudoIA.acompanharGeracao).mockResolvedValue({ id: 'l5' })
    vi.mocked(pendencias.getPendencias).mockResolvedValue({
      essenciais: { total: 1, resolvidos: 0 },
      estudo_de_caso: { editado: false },
      escalas_para_adicionar: [],
      grupos: [
        {
          chave: 'gestacao', titulo: 'Gestação e parto', escala: false, essencial: true, pendentes: 1,
          itens: [{ chave: 'parto', rotulo: 'Parto', essencial: true, campos: [{ id: 'parto', tipo: 'texto', opcoes: [], min: null, max: null }], valores: {}, situacao: null, origem: null, sugestoes: [] }],
        },
      ],
    })
    render(
      <MemoryRouter initialEntries={['/laudo-ia?paciente=p1&laudo=l5']}>
        <LaudoPorIA />
      </MemoryRouter>,
    )
    // Sem clicar em "Preencher campos": o modal já abre.
    const modal = await screen.findByRole('dialog', { name: 'Campos que faltam no laudo' })
    fireEvent.click(within(modal).getByRole('button', { name: 'Atualizar relatório' }))
    expect(await screen.findByTitle('Gerando o laudo')).toHaveAttribute('src', '/formulario-novo-paciente.html?laudo=l5&modo=gerar&tentativa=1')
    expect(pendencias.atualizarLaudo).toHaveBeenCalledWith('l5', false)
    expect(laudoIA.acompanharGeracao).toHaveBeenCalledWith('j9', expect.any(Function))
    mensagemDoFormulario({ tipo: 'laudo-ia:gerado', laudoId: 'l5' })
    expect(await screen.findByText('Relatório atualizado com 2 dados novos. Os dados novos foram incluídos no estudo de caso.')).toBeInTheDocument()
    expect(screen.queryByTitle('Pré-visualização do laudo')).not.toBeInTheDocument()
  })
})


it('exige data do relatório antes de iniciar a geração', async () => {
  vi.mocked(patients.listPatients).mockResolvedValue([paciente])
  render(<MemoryRouter initialEntries={['/laudo-ia?paciente=p1']}><LaudoPorIA /></MemoryRouter>)
  fireEvent.change(await screen.findByTestId('arquivos-pdf'), { target: { files: [new File(['%PDF'], 'a.pdf', { type: 'application/pdf' })] } })
  expect(screen.getByRole('button', { name: 'Gerar relatório com IA' })).toBeDisabled()
  fireEvent.change(screen.getByLabelText(/Data do relatório/), { target: { value: '2026-10-15' } })
  expect(screen.getByRole('button', { name: 'Gerar relatório com IA' })).toBeEnabled()
})


it('ao abrir pelo histórico mostra carregamento, sem exibir o formulário de geração nem baixar o documento', async () => {
  let resolver!: (value: Awaited<ReturnType<typeof reports.getReportResumo>>) => void
  vi.mocked(reports.getReportResumo).mockImplementation(() => new Promise(resolve => { resolver = resolve }))
  vi.mocked(patients.listPatients).mockResolvedValue([paciente])
  vi.mocked(pendencias.getPendencias).mockResolvedValue({ essenciais: { total: 0, resolvidos: 0 }, grupos: [], escalas_para_adicionar: [] })
  render(<MemoryRouter initialEntries={['/laudo-ia?paciente=p1&laudo=l10']}><LaudoPorIA /></MemoryRouter>)
  expect(screen.getByRole('status')).toHaveTextContent('Carregando os campos que faltam')
  expect(screen.queryByTestId('arquivos-pdf')).not.toBeInTheDocument()
  expect(pendencias.getPendencias).toHaveBeenCalledWith('l10') // em paralelo com o resumo
  expect(reports.getReport).not.toHaveBeenCalled()
  await act(async () => { resolver({ id: 'l10', patient_id: 'p1', computed_json: { origem: 'ia_pdf' } } as never) })
  expect(await screen.findByText('Todos os campos do protocolo estão preenchidos.')).toBeInTheDocument()
  expect(reports.getReport).not.toHaveBeenCalled()
  expect(screen.getByRole('button', { name: 'Gerar novo relatório' })).toBeInTheDocument()
  vi.mocked(reports.getReport).mockResolvedValue({ id: 'l10', answers_json: {}, generated_text: '<p>Prévia</p>' } as never)
  fireEvent.click(screen.getByRole('button', { name: 'Ver prévia do relatório' }))
  expect(await screen.findByTitle('Pré-visualização do laudo')).toBeInTheDocument()
  expect(reports.getReport).toHaveBeenCalledWith('l10')
})
