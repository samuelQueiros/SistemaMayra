import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as patients from '../api/patients'
import * as laudoIA from '../api/laudoIA'
import * as reports from '../api/reports'
import LaudoPorIA from './LaudoPorIA'

vi.mock('../api/patients', () => ({ listPatients: vi.fn(), createPatient: vi.fn() }))
vi.mock('../api/reports', () => ({ getReport: vi.fn(), downloadReportDocx: vi.fn(), downloadReportPdf: vi.fn() }))
vi.mock('../api/laudoIA', async (original) => ({ ...(await original<typeof laudoIA>()), gerarLaudoPorIA: vi.fn() }))
vi.mock('../api/pendencias', () => ({
  getPendencias: vi.fn().mockResolvedValue({ essenciais: { total: 0, resolvidos: 0 }, grupos: [], escalas_para_adicionar: [] }),
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
  fireEvent.click(screen.getByRole('button', { name: 'Gerar laudo com IA' }))
  return pdf
}

describe('Laudo Por IA', () => {
  beforeEach(() => {
    vi.mocked(patients.listPatients).mockResolvedValue([paciente])
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

    expect(await screen.findByTitle('Gerando o laudo')).toHaveAttribute('src', '/formulario-novo-paciente.html?laudo=l1&modo=gerar')
    expect(laudoIA.gerarLaudoPorIA).toHaveBeenCalledWith('p1', [pdf], '', catalogo, expect.any(Function))
    mensagemDoFormulario({ tipo: 'laudo-ia:gerado', laudoId: 'l1' })

    expect(await screen.findByText('Laudo gerado')).toBeInTheDocument()
    expect(await screen.findByText('Dados que faltaram')).toBeInTheDocument()
    expect(screen.getByTitle('Pré-visualização do laudo')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Baixar Word (DOCX)' }))
    expect(reports.downloadReportDocx).toHaveBeenCalledWith('l1', 'laudo_ia_Bia_Lima.docx')
  })

  it('se o documento falhar, avisa e oferece abrir o laudo criado no formulário', async () => {
    vi.mocked(laudoIA.gerarLaudoPorIA).mockResolvedValue({ id: 'l2' } as laudoIA.LaudoPorIA)
    await prepararEGerar()
    mensagemDoFormulario({ tipo: 'laudo-ia:catalogo', catalogo })
    await screen.findByTitle('Gerando o laudo')
    await act(async () => {})
    mensagemDoFormulario({ tipo: 'laudo-ia:erro', mensagem: 'Falhou ao gerar.' })

    expect(await screen.findByText(/Falhou ao gerar\./)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'abra no formulário' })).toHaveAttribute('href', '/atendimento/novo?laudo=l2')
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
    expect(screen.getByRole('button', { name: 'Gerar laudo com IA' })).toBeEnabled()
  })
})
