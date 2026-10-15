"""Laudo Por IA: a psicóloga envia os PDFs (respostas do Google Forms e
escalas pontuadas), a IA escreve o estudo de caso e preenche os campos do
protocolo fixo, e o resultado vira um laudo comum do protocolo padrão
(template `custom_form`). O documento final — com os gráficos — é gerado
pelo próprio formulário (`formulario-novo-paciente.html?laudo=<id>&modo=gerar`),
exatamente como no fluxo manual; a psicóloga baixa o Word para editar.

Fluxo separado: não muda nada no preenchimento manual do protocolo."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
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
from app.schemas.report import ReportOut
from app.services.ai import AIConfigurationError, resolve_ai_credentials
from app.services.ai.agentes.extracao import ErroNaEtapaDaIA
from app.services.ai.erros import cota_diaria_esgotada
from app.services.laudo_ia import CatalogoDoProtocolo, ResultadoDaIA, preencher_protocolo, respostas_para_answers

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


def _descricao_do_paciente(patient: Patient) -> str:
    texto = patient.name
    if patient.birth_date:
        texto += f" ({_idade(patient.birth_date)})"
    if patient.sex:
        texto += f", sexo {patient.sex}"
    return texto


def _preencher_com_ia(
    patient: Patient,
    pdfs: list[dict],
    catalogo: CatalogoDoProtocolo,
    observacoes: str | None,
    db: Session,
    current: Psychologist,
    com_estudo_de_caso: bool = True,
) -> ResultadoDaIA:
    ai_settings = db.query(AISettings).filter(AISettings.owner_id == current.id).first()
    try:
        provider, model, api_key = resolve_ai_credentials(ai_settings)
        return preencher_protocolo(
            provider=provider,
            model=model,
            api_key=api_key,
            paciente=_descricao_do_paciente(patient),
            pdfs=pdfs,
            catalogo=catalogo,
            observacoes=observacoes,
            com_estudo_de_caso=com_estudo_de_caso,
        )
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except ErroNaEtapaDaIA as exc:
        # Já diz qual documento/parte falhou e por quê.
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:
        if cota_diaria_esgotada(exc):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"A cota diária de uso da IA ({provider}/{model}) foi esgotada. "
                    "Aguarde a renovação da cota informada pelo provedor ou revise o plano "
                    "e o faturamento da API. Você também pode selecionar outro modelo ou "
                    "provedor com cota disponível em Configurações → Inteligência Artificial. "
                    "Uma geração de laudo pode usar várias chamadas de IA."
                ),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Não foi possível ler os PDFs com o provedor de IA configurado "
                f"({provider}/{model}). Verifique a chave e o modelo em \"Configurações → "
                f"Inteligência Artificial\" (o modelo precisa aceitar PDFs). Detalhe técnico: {exc}"
            ),
        ) from exc


@router.post("/api/patients/{patient_id}/laudo-ia", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def criar_laudo_por_ia(
    patient_id: UUID,
    arquivos: list[UploadFile] = File(...),
    catalogo: str = Form(...),
    observacoes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Report:
    patient = get_patient_or_404(patient_id, db, current)
    catalogo_do_protocolo = _ler_catalogo(catalogo)
    pdfs = ler_pdfs_enviados(arquivos, MAXIMO_DE_ARQUIVOS)
    resultado = _preencher_com_ia(patient, pdfs, catalogo_do_protocolo, observacoes, db, current)

    answers, descartados = respostas_para_answers(resultado.protocolo, catalogo_do_protocolo)
    template = garantir_template_custom_form(db, current)
    report = Report(
        patient_id=patient.id,
        template_id=template.id,
        answers_json=answers,
        computed_json={
            "origem": "ia_pdf",
            "arquivos": guardar_pdfs(patient.id, pdfs),
            "observacoes": observacoes or "",
            "lacunas": resultado.protocolo.lacunas,
            "campos_descartados": descartados,
            # PDFs transcritos em JSON (o que os agentes leram) e tempo de cada etapa.
            "documentos": [d.model_dump() for d in resultado.documentos],
            "tempos": resultado.tempos,
        },
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


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
    resultado = _preencher_com_ia(patient, pdfs, catalogo_do_protocolo, None, db, current, com_estudo_de_caso=False)
    answers, descartados = respostas_para_answers(resultado.protocolo, catalogo_do_protocolo)
    answers.pop("estudoCaso", None)  # importar escalas nunca mexe no estudo de caso
    return {"respostas": answers, "lacunas": resultado.protocolo.lacunas, "descartados": descartados}
