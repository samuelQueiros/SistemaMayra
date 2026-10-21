import { readFileSync } from 'node:fs'
import { JSDOM } from 'jsdom'
import { afterEach, beforeEach, expect, it } from 'vitest'

// Ajustes da videochamada de 2026-10-16: o documento do protocolo padrão
// segue o relatório-modelo da psicóloga (João Neto).

let dom
let w

beforeEach(async () => {
  const html = readFileSync('public/formulario-novo-paciente.html', 'utf8')
  dom = new JSDOM(html, { runScripts: 'dangerously', url: 'http://localhost/formulario-novo-paciente.html?modo=catalogo', pretendToBeVisual: true })
  await new Promise(resolve => dom.window.addEventListener('load', resolve))
  w = dom.window
  w.gerarCapaRelatorio = async () => 'data:image/png;base64,CAPA'
  w.prepararFoto = async (src) => src
  for (const nome of ['graficoCARS', 'graficoATA', 'graficoPortage', 'graficoFuncoesExecutivas', 'graficoDominios', 'graficoHabilidadesAcademicas']) {
    w[nome] = () => `data:image/png;base64,${nome}`
  }
  w.graficosSNAP = () => ({ pontos: 'data:image/png;base64,snapPontos', perc: 'data:image/png;base64,snapPerc' })
})

afterEach(() => dom.window.close())

const ata23 = Object.fromEntries(Array.from({ length: 22 }, (_, i) => [`ata_item_${i}`, i === 17 ? '2' : '1']))

it('cabeçalho, metodologia, destaques e final no modelo do relatório', async () => {
  w.aplicarDados({
    nomePaciente: 'Paciente Teste', sexo: 'Masculino', dataNascimento: '2019-11-02', dataRelatorio: '2026-10-15',
    metodologia: '**PROTOCOLO UTILIZADO**: Realizada análise dos comportamentos.',
    estudoCaso: 'Texto do estudo de caso que não vai para o documento.',
    filhoUnico: 'Não', filhoUnicoDescricao: '9 anos, com laudo de TEA; 4 anos, sem laudo',
    ...ata23, cars_0: '2',
    parto: 'Cesáreo', complicacaoParto: 'Sim', complicacaoPartoDescricao: 'pressão alta',
    hcog_0: 'Sim', hcog_1: 'Às Vezes', fe_manif_0: 'Percebe quando algo dá errado.',
    hip_tea: true, hip_tea_6a02_0: true, hip_tod: true,
    enc_fonoaudiologia: true,
    __fotosPacienteDados: [{ src: 'data:image/png;base64,FOTO1' }, { src: 'data:image/png;base64,FOTO2' }],
  })
  w.calcularATA()
  const doc = await w.gerarDocumentoLaudoHTML()

  expect(doc).toContain('PARECER NEUROPSICOPEDAGÓGICO ANÁLISE COMPORTAMENTAL</div>')
  expect(doc).toContain('METODOLOGIA E PROTOCOLOS UTILIZADOS')
  expect(doc).not.toContain('PROTOCOLO UTILIZADO**')

  // Irmãos com idade e laudo
  expect(doc).toContain('<li><strong>Irmãos:</strong> 9 anos, com laudo de TEA; 4 anos, sem laudo.</li>')

  // ATA: 23 pontos, 52% (23 ÷ 44), destaques em amarelo, faixa de traços autísticos
  expect(doc).toContain('<mark class="amarelo"><strong>23 pontos na análise da escala ATA</strong></mark>')
  expect(doc).toContain('<mark class="amarelo"><strong>52% de características</strong></mark>')
  expect(doc).toContain('<mark class="amarelo">Pontuação acima 20 pontos')

  // Quadros por área do desenvolvimento; 2ª hipótese com a faixa própria
  expect(doc).toContain('<h3 class="area">ÁREA DO DESENVOLVIMENTO: ')
  expect(doc).toContain('HIPÓTESE DE TRANSTORNO OPOSITOR DESAFIADOR – TOD')

  // Hipóteses: todas as marcadas, pelo subtipo quando houver
  expect(doc).toContain('Hipóteses e/ou Confirmações Diagnósticas:')
  expect(doc).toContain('TEA sem deficiência intelectual e linguagem funcional preservada')
  expect(doc).toContain('Transtorno Opositor Desafiador – TOD')
  expect(doc).not.toContain('Transtorno do Espectro Autista – TEA</strong>')
  expect(doc).toContain('<li>Fonoaudiologia</li>')

  // Habilidades gerais (tabelas do modelo) e quadro das funções executivas
  expect(doc).toContain('<u>HABILIDADES COGNITIVAS E METACOGNITIVAS</u>')
  expect(doc).toContain('<td>Atenção e concentração</td><td>Mantém atenção e foco nas atividades propostas e no ambiente escolar.</td>')
  expect(doc).toContain('Quadro – Aplicação das Funções Executivas do paciente')
  expect(doc).toContain('<th>Habilidades identificadas no paciente</th>')
  expect(doc).toContain('<li><strong>Parto:</strong> Cesáreo com complicação (pressão alta).</li>')
  expect(doc).toContain('Idade Cronológica:')
  expect(doc).toContain('<strong><u>Hipóteses e/ou Confirmações Diagnósticas:</u></strong>')

  // Sequência do modelo: domínios (resume as áreas) → funções executivas
  // (quadro e gráfico juntos) → Portage → CARS → ATA → hipóteses → encaminhamentos
  const ordem = ['base64,graficoDominios', 'Quadro – Aplicação das Funções Executivas', 'base64,graficoFuncoesExecutivas', 'base64,graficoCARS', 'pontos na análise da escala ATA', 'Hipóteses e/ou Confirmações', '<li>Fonoaudiologia</li>']
  const posicoes = ordem.map((t) => doc.indexOf(t))
  expect(posicoes.every((p) => p > 0)).toBe(true)
  expect([...posicoes].sort((a, b) => a - b)).toEqual(posicoes)

  // "Considerações Finais" (aviso de que o documento não é laudo médico)
  // repete no final de cada protocolo finalizado, não só uma vez no fechamento.
  const ocorrenciasConsideracoes = doc.split('Considerações Finais').length - 1
  expect(ocorrenciasConsideracoes).toBeGreaterThan(1)
  expect(doc.lastIndexOf('Considerações Finais')).toBeGreaterThan(doc.indexOf('<li>Fonoaudiologia</li>'))

  // Fora do documento
  expect(doc).not.toContain('Estudo De Caso E Observações Clínicas')
  expect(doc).not.toContain('Encaminhei também')
  expect(doc).not.toContain('Observação sobre a faixa etária do Portage')

  // Nota perto da assinatura; galeria depois dela, com todas as fotos
  const sobre = doc.indexOf('SOBRE A PROFISSIONAL RESPONSÁVEL')
  const nota = doc.indexOf('NOTA SOBRE OS RESULTADOS')
  const atenciosamente = doc.indexOf('Atenciosamente')
  const galeria = doc.indexOf('REGISTROS DOS ATENDIMENTOS')
  expect(sobre).toBeGreaterThan(0)
  expect(nota).toBeGreaterThan(sobre)
  expect(atenciosamente).toBeGreaterThan(nota)
  expect(galeria).toBeGreaterThan(atenciosamente)
  const fotosNaGaleria = doc.slice(galeria)
  expect(fotosNaGaleria).toContain('FOTO1')
  expect(fotosNaGaleria).toContain('FOTO2')
  // Sem fotos no meio do texto: só a do cabeçalho antes da galeria
  expect(doc.slice(0, galeria).split('FOTO2').length).toBe(1)
})

it('laudos antigos com DI ou aprendizagem sem grau usam a opção não especificada', async () => {
  w.aplicarDados({ nomePaciente: 'Paciente Antigo', hip_di: true, hip_ta: true })
  const doc = await w.gerarDocumentoLaudoHTML()
  expect(doc).toContain('Deficiência intelectual não especificada')
  expect(doc).toContain('Transtorno da aprendizagem não especificado')
})

it('M-CHAT entra no lugar do SNAP-IV dos 16 aos 30 meses', async () => {
  const snap = Object.fromEntries(Array.from({ length: 18 }, (_, i) => [`snap_${i}`, '2']))
  w.aplicarDados({ nomePaciente: 'Bebê Teste', dataNascimento: '2025-02-10', dataRelatorio: '2026-10-15', mchat_0: 'sim', ...snap })
  const pequeno = await w.gerarDocumentoLaudoHTML()
  expect(pequeno).toContain('M-CHAT — Modified Checklist For Autism In Toddlers')
  expect(pequeno).not.toContain('snapPontos')

  w.aplicarDados({ dataNascimento: '2019-02-10' })
  const maior = await w.gerarDocumentoLaudoHTML()
  expect(maior).not.toContain('M-CHAT — Modified Checklist For Autism In Toddlers')
  expect(maior).toContain('snapPontos')
})

it('gráfico da ATA vai só até 2 e a idade cognitiva sai só como faixa', () => {
  const fonte = readFileSync('public/formulario-novo-paciente.html', 'utf8')
  const graficoATA = fonte.slice(fonte.indexOf('function graficoATA()'), fonte.indexOf('function graficoATA()') + 1500)
  expect(graficoATA).toContain('min:0,max:2')
  expect(fonte).not.toContain('Repertório de referência pelo Portage')
})
