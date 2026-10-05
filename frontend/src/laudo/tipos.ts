// Formato dos modelos de protocolo configuráveis — espelha
// backend/app/schemas/protocolo.py (validação de verdade fica lá).

export type TipoPergunta =
  | 'texto_curto'
  | 'texto_longo'
  | 'sim_nao'
  | 'multipla_escolha'
  | 'caixas'
  | 'data'
  | 'numero'

export type TipoSecao = 'perguntas' | 'escala' | 'fotos' | 'texto'

export interface OpcaoPergunta {
  rotulo: string
  texto_relatorio?: string | null
}

export interface Pergunta {
  id: string
  rotulo: string
  tipo: TipoPergunta
  ajuda?: string | null
  opcoes?: OpcaoPergunta[] | null
  obrigatoria?: boolean
  detalhar_quando_sim?: boolean
}

export interface ItemEscala {
  id: string
  rotulo: string
}

export interface OpcaoEscala {
  rotulo: string
  valor: number
}

export interface FaixaEscala {
  min: number
  max: number
  rotulo: string
  texto_relatorio?: string | null
}

export interface Escala {
  itens: ItemEscala[]
  opcoes: OpcaoEscala[]
  faixas: FaixaEscala[]
  grafico: 'barras' | 'nenhum'
}

export interface RelatorioDaSecao {
  mostrar: boolean
  formato: 'lista' | 'tabela' | 'so_texto'
  texto_padrao?: string | null
}

export interface Secao {
  id: string
  titulo: string
  tipo: TipoSecao
  ajuda?: string | null
  perguntas?: Pergunta[] | null
  escala?: Escala | null
  relatorio: RelatorioDaSecao
}

export interface ModeloProtocolo {
  rule_type: 'protocolo'
  name: string
  descricao?: string | null
  titulo_relatorio: string
  secoes: Secao[]
}

export interface Protocolo {
  id: string
  name: string
  version: number
  schema_json: ModeloProtocolo
  arquivado: boolean
  created_at: string
}

// Respostas de um atendimento (Report.answers_json).
export interface Identificacao {
  nome: string
  data_nascimento: string // AAAA-MM-DD
  sexo: string // "Feminino" | "Masculino" | ""
  responsavel: string
  cidade: string
  data_relatorio: string // AAAA-MM-DD
}

export type Resposta = string | string[]

export interface TextoDaSecao {
  valor: string
  // true depois que a psicóloga mexe no texto: ele para de ser
  // recalculado a partir das respostas (como os campos automáticos do
  // protocolo fixo).
  editado: boolean
}

export interface Foto {
  nome: string
  src: string
}

export interface CapaConfig {
  escreverNome: boolean
  faixa: { x: number; y: number; largura: number; altura: number }
  corNome: string
}

export interface RespostasProtocolo {
  identificacao: Identificacao
  respostas: Record<string, Resposta>
  detalhes: Record<string, string>
  escalas: Record<string, Record<string, number>> // secao -> item -> índice da opção
  textos: Record<string, TextoDaSecao>
  fotos: Record<string, Foto[]> // secao -> fotos
  capa: { src: string; config: CapaConfig } | null
}
