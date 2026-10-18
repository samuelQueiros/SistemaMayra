// Hipóteses diagnósticas (tabela "CID-10 × CID-11 – Consulta Rápida NeuroPP")
// e encaminhamentos que a psicóloga escolhe antes de enviar os PDFs do Laudo
// Por IA. Os ids são os mesmos das caixas do formulário padrão
// (public/formulario-novo-paciente.html, seções 9 e 19) — um teste confere.

export interface HipoteseCid {
  id: string
  rotulo: string
  cid11?: string
  cid10?: string
  subtipos?: HipoteseCid[]
}

export interface GrupoCid {
  titulo: string
  hipoteses: HipoteseCid[]
}

const F70_F79 = 'F84.x + F70–F79'

export const GRUPOS_CID: GrupoCid[] = [
  {
    titulo: '1. TEA – Transtorno do Espectro Autista',
    hipoteses: [
      {
        id: 'hip_tea', rotulo: 'Transtorno do Espectro Autista – TEA', cid11: '6A02', cid10: 'F84.0 / F84.1 / F84.5 / F84.9',
        subtipos: [
          { id: 'hip_tea_6a02_0', rotulo: 'TEA sem deficiência intelectual e linguagem funcional preservada', cid11: '6A02.0', cid10: 'F84.x' },
          { id: 'hip_tea_6a02_1', rotulo: 'TEA com deficiência intelectual e linguagem funcional preservada', cid11: '6A02.1', cid10: F70_F79 },
          { id: 'hip_tea_6a02_2', rotulo: 'TEA sem deficiência intelectual e com prejuízo da linguagem funcional', cid11: '6A02.2', cid10: 'F84.x' },
          { id: 'hip_tea_6a02_3', rotulo: 'TEA com deficiência intelectual e prejuízo da linguagem funcional', cid11: '6A02.3', cid10: F70_F79 },
          { id: 'hip_tea_6a02_5', rotulo: 'TEA com deficiência intelectual e ausência/quase ausência de linguagem funcional', cid11: '6A02.5', cid10: F70_F79 },
          { id: 'hip_tea_6a02_z', rotulo: 'TEA não especificado', cid11: '6A02.Z', cid10: 'F84.9' },
        ],
      },
    ],
  },
  {
    titulo: '2. TDAH e Deficiência Intelectual',
    hipoteses: [
      {
        id: 'hip_tdah', rotulo: 'TDAH', cid11: '6A05', cid10: 'F90.0',
        subtipos: [
          { id: 'hip_tdah_6a05_0', rotulo: 'TDAH predominantemente desatento', cid11: '6A05.0', cid10: 'F90.0' },
          { id: 'hip_tdah_6a05_1', rotulo: 'TDAH predominantemente hiperativo/impulsivo', cid11: '6A05.1', cid10: 'F90.0' },
          { id: 'hip_tdah_6a05_2', rotulo: 'TDAH combinado', cid11: '6A05.2', cid10: 'F90.0' },
        ],
      },
      { id: 'hip_di_6a00_0', rotulo: 'Deficiência intelectual leve', cid11: '6A00.0', cid10: 'F70' },
      { id: 'hip_di_6a00_1', rotulo: 'Deficiência intelectual moderada', cid11: '6A00.1', cid10: 'F71' },
      { id: 'hip_di_6a00_2', rotulo: 'Deficiência intelectual grave', cid11: '6A00.2', cid10: 'F72' },
      { id: 'hip_di_6a00_3', rotulo: 'Deficiência intelectual profunda', cid11: '6A00.3', cid10: 'F73' },
      { id: 'hip_di_6a00_z', rotulo: 'Deficiência intelectual não especificada', cid11: '6A00.Z', cid10: 'F79' },
    ],
  },
  {
    titulo: '3. Linguagem e Aprendizagem',
    hipoteses: [
      { id: 'hip_linguagem_6a01_0', rotulo: 'Transtorno dos sons da fala / fonológico', cid11: '6A01.0', cid10: 'F80.0' },
      { id: 'hip_linguagem_6a01_21', rotulo: 'Transtorno de linguagem expressiva', cid11: '6A01.21', cid10: 'F80.1' },
      { id: 'hip_linguagem_6a01_20', rotulo: 'Transtorno de linguagem receptiva e expressiva', cid11: '6A01.20', cid10: 'F80.2' },
      { id: 'hip_linguagem_6a01_22', rotulo: 'Alteração predominantemente pragmática da linguagem', cid11: '6A01.22' },
      { id: 'hip_linguagem_6a01_z', rotulo: 'Transtorno de linguagem não especificado', cid11: '6A01.Z', cid10: 'F80.9' },
      { id: 'hip_ta_6a03_0', rotulo: 'Transtorno específico da leitura / dislexia', cid11: '6A03.0', cid10: 'F81.0' },
      { id: 'hip_ta_6a03_1', rotulo: 'Transtorno da expressão escrita', cid11: '6A03.1', cid10: 'F81.1 / F81.8' },
      { id: 'hip_ta_6a03_2', rotulo: 'Transtorno da matemática / discalculia', cid11: '6A03.2', cid10: 'F81.2' },
      { id: 'hip_ta_6a03_z', rotulo: 'Transtorno da aprendizagem não especificado', cid11: '6A03.Z', cid10: 'F81.9' },
    ],
  },
  {
    titulo: '4. Outros',
    hipoteses: [
      { id: 'hip_coordenacao', rotulo: 'Transtorno do desenvolvimento da coordenação motora', cid11: '6A04', cid10: 'F82' },
      { id: 'hip_tod', rotulo: 'Transtorno Opositor Desafiador – TOD', cid11: '6C90', cid10: 'F91.3' },
      { id: 'hip_conduta', rotulo: 'Transtorno de conduta', cid11: '6C91', cid10: 'F91.x' },
      // Fora da tabela, mantido: já usado em laudos, quadros e encaminhamentos.
      { id: 'hip_tpac', rotulo: 'TPAC – Transtorno do Processamento Auditivo Central' },
    ],
  },
]

export interface Encaminhamento {
  id: string
  rotulo: string
}

export const ENCAMINHAMENTOS: Encaminhamento[] = [
  { id: 'enc_neuropediatra', rotulo: 'Neuropediatra' },
  { id: 'enc_avaliacao_neuropsicologica', rotulo: 'Avaliação Neuropsicológica' },
  { id: 'enc_avaliacao_do_processamento_auditivo_central_tpac', rotulo: 'Avaliação Do Processamento Auditivo Central – TPAC' },
  { id: 'enc_fonoaudiologia', rotulo: 'Fonoaudiologia' },
  { id: 'enc_terapia_ocupacional', rotulo: 'Terapia Ocupacional' },
  { id: 'enc_acompanhamento_neuropsicopedagogico_psicopedagogico', rotulo: 'Acompanhamento Neuropsicopedagógico/Psicopedagógico' },
  { id: 'enc_terapia', rotulo: 'Terapia' },
  { id: 'enc_fisioterapia', rotulo: 'Fisioterapia' },
  { id: 'enc_nutricao', rotulo: 'Nutrição' },
  { id: 'enc_psicologia_infantil', rotulo: 'Psicologia Infantil' },
]

/** Texto da hipótese no relatório: "Rótulo (CID-11 6A02.0 / CID-10 F84.x)". */
export function textoDaHipotese(h: HipoteseCid): string {
  if (!h.cid11) return h.rotulo
  return `${h.rotulo} (CID-11 ${h.cid11}${h.cid10 ? ` / CID-10 ${h.cid10}` : ''})`
}

/** Todas as hipóteses (principais e subtipos), na ordem da tabela. */
export function todasAsHipoteses(): HipoteseCid[] {
  return GRUPOS_CID.flatMap((g) => g.hipoteses.flatMap((h) => [h, ...(h.subtipos ?? [])]))
}
