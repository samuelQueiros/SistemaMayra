"""Laudo Por IA: a psicóloga envia os PDFs (respostas do Google Forms e
escalas pontuadas), a IA escreve o estudo de caso e preenche os campos do
protocolo fixo, e o resultado vira um laudo comum do protocolo padrão
(template `custom_form`). O documento final — com os gráficos — é gerado
pelo próprio formulário (`formulario-novo-paciente.html?laudo=<id>&modo=gerar`),
exatamente como no fluxo manual; a psicóloga baixa o Word para editar.

Fluxo separado: não muda nada no preenchimento manual do protocolo."""

import json
from datetime import date
from typing import Literal
from functools import partial
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.api.patients import get_patient_or_404
from app.api.relatorios_pdf import _idade, guardar_pdfs, ler_pdfs_enviados
from app.api.templates import garantir_template_custom_form
from app.core.database import get_db
from app.models.ai_settings import AISettings
from app.models.patient import Patient
from app.models.psychologist import Psychologist
from app.models.report import Report
from app.services.ai import AIConfigurationError, resolve_ai_credentials
from app.services import laudo_ia_jobs
from app.services.ai.agentes.extracao import ErroNaEtapaDaIA, motivo_do_erro
from app.services.ai.erros import cota_diaria_esgotada
from app.services.ata import pontuar_ata
from app.services.laudo_ia import (
    CatalogoDoProtocolo,
    dados_da_profissional_em_texto,
    escolhas_da_profissional,
    preencher_protocolo,
    respostas_para_answers,
    valores_da_profissional,
)
from app.services.laudo_ia_jobs import Andamento
from app.services.pendencias import aplicar_dados_confirmados, metodos_nao_aplicados

router = APIRouter(tags=["laudo-ia"])

# Formulários dos responsáveis/escola + escalas (CARS, ATA, SNAP-IV, Portage...).
MAXIMO_DE_ARQUIVOS = 10


def _ler_catalogo(catalogo: str) -> CatalogoDoProtocolo:
    try:
        return CatalogoDoProtocolo.model_validate(json.loads(catalogo))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Catálogo do protocolo inválido. Recarregue a página e tente de novo.",
        ) from exc


def _ler_lista_de_ids(valor: str | None, nome: str) -> list[str]:
    if not valor:
        return []
    try:
        ids = json.loads(valor)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Lista de {nome} inválida.") from exc
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Lista de {nome} inválida.")
    return ids


def _ler_dados_da_profissional(valor: str | None) -> dict:
    if not valor:
        return {}
    try:
        dados = json.loads(valor)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dados da profissional inválidos.") from exc
    if not isinstance(dados, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dados da profissional inválidos.")
    return dados


def _observacoes_para_a_ia(observacoes: str | None, dados_texto: str) -> str | None:
    partes = [p for p in ((observacoes or "").strip(), dados_texto) if p]
    return "\n\n".join(partes) or None


def _respostas_calculadas(documentos, catalogo: CatalogoDoProtocolo) -> dict:
    """Campos que o sistema calcula a partir dos PDFs (pontuação da ATA) —
    prevalecem sobre o que a IA preencheu."""
    ids = {c.id for c in catalogo.campos}
    return {chave: valor for chave, valor in pontuar_ata(documentos).items() if chave in ids}


def _descricao_do_paciente(patient: Patient) -> str:
    texto = patient.name
    if patient.birth_date:
        texto += f" ({_idade(patient.birth_date)})"
    if patient.sex:
        texto += f", sexo {patient.sex}"
    return texto


def _credenciais(db: Session, current: Psychologist) -> dict:
    ai_settings = db.query(AISettings).filter(AISettings.owner_id == current.id).first()
    try:
        provider, model, api_key = resolve_ai_credentials(ai_settings)
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return {"provider": provider, "model": model, "api_key": api_key}


def _erro_da_ia(exc: Exception, provider: str, model: str) -> tuple[int, str]:
    """Status HTTP e mensagem para a tela de uma falha da geração."""
    if isinstance(exc, ErroNaEtapaDaIA):
        # Já diz qual documento/parte falhou e por quê.
        return status.HTTP_502_BAD_GATEWAY, str(exc)
    if cota_diaria_esgotada(exc):
        return status.HTTP_429_TOO_MANY_REQUESTS, (
            f"A cota diária de uso da IA ({provider}/{model}) foi esgotada. "
            "Aguarde a renovação da cota informada pelo provedor ou revise o plano "
            "e o faturamento da API. Você também pode selecionar outro modelo ou "
            "provedor com cota disponível em Configurações → Inteligência Artificial. "
            "Uma geração de laudo pode usar várias chamadas de IA."
        )
    return status.HTTP_502_BAD_GATEWAY, (
        "Não foi possível ler os PDFs com o provedor de IA configurado "
        f'({provider}/{model}): {motivo_do_erro(exc)}. Verifique a chave e o modelo em "Configurações → '
        'Inteligência Artificial" (o modelo precisa aceitar PDFs).'
    )


class GeracaoIniciada(BaseModel):
    job_id: str


class AndamentoOut(BaseModel):
    id: str
    patient_id: str
    status: str
    mensagem: str
    documentos: list[dict]
    report_id: str | None
    erro: str | None
    progresso: int = 0
    progresso_teto: int = 0


def _gerar_laudo(
    andamento: Andamento,
    *,
    bind,
    owner_id: UUID,
    patient_id: UUID,
    paciente: str,
    pdfs: list[dict],
    catalogo: CatalogoDoProtocolo,
    observacoes: str | None,
    credenciais: dict,
    data_relatorio: date,
    cidade: str | None,
    escolhas: dict[str, bool],
    valores: dict[str, str],
) -> None:
    """Roda fora da requisição (laudo_ia_jobs.executar), com sessão própria."""
    try:
        resultado = preencher_protocolo(
            paciente=paciente,
            pdfs=pdfs,
            catalogo=catalogo,
            observacoes=_observacoes_para_a_ia(observacoes, dados_da_profissional_em_texto(catalogo, valores)),
            com_estudo_de_caso=True,
            ao_progredir=andamento,
            **credenciais,
        )
    except Exception as exc:  # noqa: BLE001 - vira mensagem no andamento
        andamento.falhar(_erro_da_ia(exc, credenciais["provider"], credenciais["model"])[1])
        return

    andamento.mensagem("Salvando o laudo…", progresso=95, teto=99)
    answers, descartados = respostas_para_answers(resultado.protocolo, catalogo)
    answers.update(_respostas_calculadas(resultado.documentos, catalogo))
    # Hipóteses, encaminhamentos, desfralde, ano escolar e habilidades:
    # escolhidos pela psicóloga, nunca pela IA.
    answers.update(escolhas)
    answers.update(valores)
    # "Métodos do relatório": só as escalas que vieram nos PDFs.
    answers["__metodosExcluidos"] = metodos_nao_aplicados(answers, {d.tipo for d in resultado.documentos})
    with Session(bind=bind) as db:
        # Dados já confirmados pela psicóloga em laudos anteriores preenchem o
        # que a IA deixou vazio (nunca sobrescrevem o que veio dos PDFs).
        answers, _ = aplicar_dados_confirmados(catalogo, answers, db.get(Patient, patient_id).dados_complementares)
        answers["dataRelatorio"] = data_relatorio.isoformat()
        answers["cidade"] = cidade or ""
        current = db.get(Psychologist, owner_id)
        template = garantir_template_custom_form(db, current)
        report = Report(
            patient_id=patient_id,
            template_id=template.id,
            answers_json=answers,
            computed_json={
                "origem": "ia_pdf",
                "arquivos": guardar_pdfs(patient_id, pdfs),
                "observacoes": observacoes or "",
                "lacunas": resultado.protocolo.lacunas,
                "campos_descartados": descartados,
                # PDFs transcritos em JSON (o que os agentes leram) e tempo de cada etapa.
                "documentos": [d.model_dump() for d in resultado.documentos],
                "tempos": resultado.tempos,
                # Para as pendências (app/services/pendencias.py) e para saber
                # se a psicóloga editou o estudo de caso antes de reescrevê-lo.
                "catalogo": catalogo.model_dump(),
                "estudo_de_caso_ia": answers.get("estudoCaso", ""),
            },
        )
        db.add(report)
        db.commit()
        andamento.concluir(report.id)


@router.post(
    "/api/patients/{patient_id}/laudo-ia", response_model=GeracaoIniciada, status_code=status.HTTP_202_ACCEPTED
)
def criar_laudo_por_ia(
    patient_id: UUID,
    arquivos: list[UploadFile] = File(...),
    catalogo: str = Form(...),
    data_relatorio: date = Form(...),
    cidade: Literal["Cidade Ocidental – GO", "Gama – DF", ""] | None = Form(default=None),
    observacoes: str | None = Form(default=None),
    hipoteses: str | None = Form(default=None),
    encaminhamentos: str | None = Form(default=None),
    dados_profissional: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> GeracaoIniciada:
    """Valida e começa a geração em segundo plano; a tela acompanha em
    GET /api/laudo-ia/jobs/{job_id} (antes a requisição ficava aberta por
    minutos e um proxy com tempo-limite curto a cortava)."""
    patient = get_patient_or_404(patient_id, db, current)
    catalogo_do_protocolo = _ler_catalogo(catalogo)
    escolhas = escolhas_da_profissional(
        catalogo_do_protocolo,
        _ler_lista_de_ids(hipoteses, "hipóteses"),
        _ler_lista_de_ids(encaminhamentos, "encaminhamentos"),
    )
    valores = valores_da_profissional(catalogo_do_protocolo, _ler_dados_da_profissional(dados_profissional))
    pdfs = ler_pdfs_enviados(arquivos, MAXIMO_DE_ARQUIVOS)
    credenciais = _credenciais(db, current)

    job = laudo_ia_jobs.criar(owner_id=current.id, patient_id=patient.id, nomes_dos_arquivos=[p["nome"] for p in pdfs])
    laudo_ia_jobs.executar(
        job,
        partial(
            _gerar_laudo,
            bind=db.get_bind(),
            owner_id=current.id,
            patient_id=patient.id,
            paciente=_descricao_do_paciente(patient),
            pdfs=pdfs,
            catalogo=catalogo_do_protocolo,
            observacoes=observacoes,
            credenciais=credenciais,
            data_relatorio=data_relatorio,
            cidade=cidade,
            escolhas=escolhas,
            valores=valores,
        ),
    )
    return GeracaoIniciada(job_id=job["id"])


@router.get("/api/laudo-ia/jobs/{job_id}", response_model=AndamentoOut)
def andamento_do_laudo_por_ia(job_id: str, current: Psychologist = Depends(get_current_psychologist)) -> dict:
    job = laudo_ia_jobs.ler(job_id)
    if job is None or job["owner_id"] != str(current.id):
        # Não revela se a geração existe e é de outra pessoa.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Geração não encontrada.")
    return job


# Fluxo manual, seção "Pontuações ATA E CARS": a psicóloga anexa os PDFs das
# escalas já pontuadas e os agentes transcrevem item a item (sem criar laudo
# e sem estudo de caso).


@router.post("/api/patients/{patient_id}/escalas-de-pdf")
def extrair_escalas_de_pdf(
    patient_id: UUID,
    arquivos: list[UploadFile] = File(...),
    catalogo: str = Form(...),
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> dict:
    patient = get_patient_or_404(patient_id, db, current)
    catalogo_do_protocolo = _ler_catalogo(catalogo)
    pdfs = ler_pdfs_enviados(arquivos, MAXIMO_DE_ARQUIVOS)
    credenciais = _credenciais(db, current)
    try:
        resultado = preencher_protocolo(
            paciente=_descricao_do_paciente(patient),
            pdfs=pdfs,
            catalogo=catalogo_do_protocolo,
            com_estudo_de_caso=False,
            **credenciais,
        )
    except Exception as exc:
        codigo, mensagem = _erro_da_ia(exc, credenciais["provider"], credenciais["model"])
        raise HTTPException(status_code=codigo, detail=mensagem) from exc
    answers, descartados = respostas_para_answers(resultado.protocolo, catalogo_do_protocolo)
    answers.update(_respostas_calculadas(resultado.documentos, catalogo_do_protocolo))
    answers.pop("estudoCaso", None)  # importar escalas nunca mexe no estudo de caso
    return {"respostas": answers, "lacunas": resultado.protocolo.lacunas, "descartados": descartados}
