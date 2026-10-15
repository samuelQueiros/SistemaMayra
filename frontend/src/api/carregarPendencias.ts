import { ApiError } from './client'
import type { CatalogoDoProtocolo } from './laudoIA'
import { enviarCatalogoDoLaudo, getPendencias } from './pendencias'
import type { PendenciasDoLaudo } from './pendencias'

// Carrega as pendências; laudo antigo sem cópia do catálogo recebe o do formulário.
export async function carregarPendencias(laudoId: string, obterCatalogo: () => Promise<CatalogoDoProtocolo>): Promise<PendenciasDoLaudo> {
  try {
    return await getPendencias(laudoId)
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) return enviarCatalogoDoLaudo(laudoId, await obterCatalogo())
    throw e
  }
}
