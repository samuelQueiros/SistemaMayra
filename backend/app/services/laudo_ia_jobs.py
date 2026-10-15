"""Laudo Por IA em segundo plano, com andamento consultável pela tela.

A geração leva minutos (vários PDFs, vários agentes). Antes era uma única
requisição HTTP aberta esse tempo todo — qualquer proxy com tempo-limite
curto cortava a resposta e a tela ficava sem nada. Agora a rota responde na
hora com o id da geração, o trabalho segue numa thread do próprio processo e
o andamento fica num JSON no storage (`form_pdfs/laudo_ia_jobs/`), visível
para qualquer um dos processos do servidor (WEB_CONCURRENCY) — sem fila
externa nem tabela nova.

O JSON guarda só nomes de arquivo, etapas e mensagens de erro: nada do
conteúdo clínico."""

import json
import logging
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from app.services.laudo_ia import ROTULOS_DAS_ETAPAS
from app.services.storage import get_form_pdfs_storage

logger = logging.getLogger(__name__)

_PASTA = "laudo_ia_jobs"
# Gerações ao mesmo tempo por processo; as demais esperam na fila (cada uma
# já faz várias chamadas paralelas ao provedor).
_GERACOES_SIMULTANEAS = 2
# A geração viva atualiza o andamento pelo menos a cada _BATIMENTO; sem
# notícia há _PARADA_APOS, o servidor reiniciou no meio.
_BATIMENTO = timedelta(seconds=30)
_PARADA_APOS = timedelta(minutes=5)

MENSAGEM_INTERROMPIDA = (
    "A geração foi interrompida (o servidor reiniciou no meio). Tente de novo: "
    "os documentos já lidos não serão lidos outra vez."
)

_executor = ThreadPoolExecutor(max_workers=_GERACOES_SIMULTANEAS, thread_name_prefix="laudo-ia")


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _chave(job_id: str) -> str:
    return f"{_PASTA}/{job_id}.json"


def _salvar(job: dict) -> None:
    job["atualizado_em"] = _agora().isoformat()
    get_form_pdfs_storage().save(_chave(job["id"]), json.dumps(job, ensure_ascii=False).encode("utf-8"))


def ler(job_id: str) -> dict | None:
    try:
        uuid.UUID(job_id)
    except ValueError:
        return None
    storage = get_form_pdfs_storage()
    if not storage.exists(_chave(job_id)):
        return None
    job = json.loads(storage.read(_chave(job_id)))
    parado = _agora() - datetime.fromisoformat(job["atualizado_em"]) > _PARADA_APOS
    if job["status"] in ("na_fila", "processando") and parado:
        job.update(status="erro", erro=MENSAGEM_INTERROMPIDA, mensagem="")
        _salvar(job)
    return job


def criar(*, owner_id, patient_id, nomes_dos_arquivos: list[str]) -> dict:
    job = {
        "id": str(uuid.uuid4()),
        "owner_id": str(owner_id),
        "patient_id": str(patient_id),
        "status": "na_fila",
        "mensagem": "Aguardando para começar…",
        "documentos": [{"nome": nome, "status": "aguardando"} for nome in nomes_dos_arquivos],
        "etapas_pendentes": [],
        "report_id": None,
        "erro": None,
        "criado_em": _agora().isoformat(),
    }
    _salvar(job)
    return job


class Andamento:
    """Recebe os avisos da geração (`ao_progredir` de preencher_protocolo) e
    grava o andamento com uma mensagem pronta para a tela."""

    def __init__(self, job: dict):
        self.job = job
        self._trava = threading.Lock()

    def _gravar(self, **mudancas) -> None:
        with self._trava:
            self.job.update(mudancas)
            _salvar(self.job)

    def _documento(self, indice: int, status: str) -> None:
        self.job["documentos"][indice - 1]["status"] = status

    def _mensagem_da_leitura(self) -> str:
        total = len(self.job["documentos"])
        prontos = sum(d["status"] == "lido" for d in self.job["documentos"])
        return f"Lendo documento {min(prontos + 1, total)} de {total}…"

    def __call__(self, evento: str, **dados) -> None:
        with self._trava:
            if evento == "lendo_documento":
                self._documento(dados["indice"], "lendo")
                self.job["mensagem"] = self._mensagem_da_leitura()
            elif evento == "documento_lido":
                self._documento(dados["indice"], "lido")
                self.job["mensagem"] = self._mensagem_da_leitura()
            elif evento == "documento_com_erro":
                self._documento(dados["indice"], "erro")
            elif evento == "preenchendo":
                self.job["etapas_pendentes"] = list(dados["etapas"])
            elif evento == "etapa_concluida":
                self.job["etapas_pendentes"] = [e for e in self.job["etapas_pendentes"] if e != dados["etapa"]]
            else:
                return
            if evento in ("preenchendo", "etapa_concluida") and self.job["etapas_pendentes"]:
                pendentes = self.job["etapas_pendentes"]
                if pendentes == ["estudo_de_caso"]:
                    self.job["mensagem"] = "Redigindo o estudo de caso…"
                else:
                    partes = ", ".join(ROTULOS_DAS_ETAPAS.get(e, e) for e in pendentes if e != "estudo_de_caso")
                    extra = " e redigindo o estudo de caso" if "estudo_de_caso" in pendentes else ""
                    self.job["mensagem"] = f"Preenchendo o protocolo ({partes}){extra}…"
            _salvar(self.job)

    def mensagem(self, texto: str) -> None:
        self._gravar(mensagem=texto)

    def concluir(self, report_id) -> None:
        self._gravar(status="concluido", mensagem="Laudo pronto.", report_id=str(report_id), etapas_pendentes=[])

    def falhar(self, erro: str) -> None:
        self._gravar(status="erro", mensagem="", erro=erro)

    def batida(self) -> None:
        self._gravar()


def em_segundo_plano(trabalho: Callable[[], None], descricao: str) -> None:
    """Outras tarefas de IA (ex.: ler um anexo) na mesma fila deste processo.
    Quem chama registra o desfecho; aqui só garante que um erro não suma."""

    def rodar() -> None:
        try:
            trabalho()
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s falhou: %s", descricao, type(exc).__name__)

    _executor.submit(rodar)


def executar(job: dict, trabalho: Callable[[Andamento], None]) -> None:
    """Agenda `trabalho(andamento)` na fila de gerações deste processo. Um
    erro não tratado vira mensagem genérica no andamento (sem conteúdo no log)."""
    andamento = Andamento(job)

    def rodar() -> None:
        andamento._gravar(status="processando", mensagem="Começando…")
        parar = threading.Event()

        def bater() -> None:
            while not parar.wait(_BATIMENTO.total_seconds()):
                andamento.batida()

        batimento = threading.Thread(target=bater, daemon=True)
        batimento.start()
        try:
            trabalho(andamento)
        except Exception as exc:  # noqa: BLE001 - nunca deixa a geração sem desfecho
            logger.warning("Laudo Por IA %s falhou: %s", job["id"], type(exc).__name__)
            andamento.falhar("Não foi possível gerar o laudo por um erro inesperado. Tente de novo.")
        finally:
            parar.set()

    _executor.submit(rodar)
