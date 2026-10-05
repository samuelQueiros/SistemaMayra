const TOKEN_KEY = 'formpsico_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const MENSAGEM_SEM_CONEXAO =
  'Não foi possível falar com o servidor. Verifique sua conexão com a internet e tente novamente.'

// Mensagem para a pessoa usuária: o que aconteceu e o que fazer. O backend já
// devolve `detail` em português para erros previstos (404, 400, 422...); os
// códigos abaixo cobrem respostas sem mensagem útil (proxy, servidor fora do
// ar, arquivo grande demais).
export function mensagemDeErro(status: number, detail: unknown): string {
  if (typeof detail === 'string' && detail.trim() && status < 500) return detail
  // 422 do FastAPI/Pydantic: lista de erros; os validadores do projeto já
  // escrevem a mensagem em português ("Value error, ..." na frente).
  if (status === 422 && Array.isArray(detail) && detail.length) {
    const primeiro = detail[0] as { msg?: unknown }
    if (typeof primeiro?.msg === 'string') return primeiro.msg.replace(/^Value error,\s*/, '')
  }
  if (status === 401) return 'Sua sessão expirou. Entre novamente para continuar.'
  if (status === 403) return 'Você não tem permissão para acessar este conteúdo.'
  if (status === 404) return 'O item procurado não foi encontrado. Ele pode ter sido excluído.'
  if (status === 413) return 'O arquivo enviado é grande demais. Reduza o tamanho (ex.: fotos menores) e tente novamente.'
  if (status === 429) return 'Muitas tentativas seguidas. Aguarde alguns minutos e tente novamente.'
  if (status >= 500) {
    return typeof detail === 'string' && detail.trim()
      ? detail
      : 'O sistema encontrou um erro inesperado. Tente novamente em alguns instantes; se continuar, avise o suporte técnico.'
  }
  return 'Não foi possível concluir a ação. Confira os dados e tente novamente.'
}

async function lerErro(response: Response): Promise<ApiError> {
  let detail: unknown = null
  try {
    detail = (await response.json()).detail
  } catch {
    // resposta sem corpo JSON (ex.: página de erro do proxy)
  }
  return new ApiError(response.status, mensagemDeErro(response.status, detail))
}

// Sessão expirada em qualquer tela logada: limpa o token e volta para o
// login explicando o motivo (o próprio login trata o 401 de senha errada).
function tratarSessaoExpirada(path: string, status: number): void {
  if (status !== 401 || path.startsWith('/auth/')) return
  clearToken()
  if (!window.location.pathname.startsWith('/login')) {
    window.location.assign('/login?sessao=expirada')
  }
}

async function enviar(path: string, init: RequestInit): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, init)
  } catch {
    throw new ApiError(0, MENSAGEM_SEM_CONEXAO)
  }
  if (!response.ok) {
    tratarSessaoExpirada(path, response.status)
    throw await lerErro(response)
  }
  return response
}

function cabecalhos(extra?: Record<string, string>): Record<string, string> {
  const token = getToken()
  return { ...(extra ?? {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await enviar(path, {
    ...options,
    headers: cabecalhos({ 'Content-Type': 'application/json', ...(options.headers as Record<string, string> | undefined) }),
  })
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

export const apiGet = <T>(path: string) => request<T>(path)
export const apiPost = <T>(path: string, body: unknown) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body) })
export const apiPut = <T>(path: string, body: unknown) =>
  request<T>(path, { method: 'PUT', body: JSON.stringify(body) })
export const apiPatch = <T>(path: string, body: unknown) =>
  request<T>(path, { method: 'PATCH', body: JSON.stringify(body) })
export const apiDelete = <T>(path: string) => request<T>(path, { method: 'DELETE' })

export async function apiPostFile<T>(path: string, file: File, method: 'POST' | 'PUT' = 'POST'): Promise<T> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await enviar(path, { method, headers: cabecalhos(), body: formData })
  return response.json() as Promise<T>
}

// Arquivo de rota autenticada como URL de objeto local, para usar em <img
// src>, que não manda o token Bearer sozinho.
export async function fetchObjectUrl(path: string): Promise<string> {
  const response = await enviar(path, { headers: cabecalhos() })
  return URL.createObjectURL(await response.blob())
}

function baixar(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export async function downloadGet(path: string, fileName: string): Promise<void> {
  const response = await enviar(path, { headers: cabecalhos() })
  baixar(await response.blob(), fileName)
}

export async function downloadBlob(path: string, body: unknown, fileName: string): Promise<void> {
  const response = await enviar(path, {
    method: 'POST',
    headers: cabecalhos({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  baixar(await response.blob(), fileName)
}
