"""Números de uso do painel (pacientes, laudos, laudos nos últimos 30 dias e por modelo), sempre da
psicóloga logada."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.core.database import get_db
from app.models.patient import Patient
from app.models.psychologist import Psychologist
from app.models.report import Report
from app.models.report_template import ReportTemplate
from app.schemas.stats import StatsByTemplate, StatsSummary

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary", response_model=StatsSummary)
def get_stats_summary(
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> StatsSummary:
    """Números de uso para a própria psicóloga acompanhar (painel do
    Dashboard) — sempre filtrados pelo dono, mesmo isolamento das demais
    rotas do sistema."""

    total_patients = db.query(func.count(Patient.id)).filter(Patient.owner_id == current.id).scalar()

    # Uma consulta só para os três números de laudos, e com count(id): o
    # Query.count() contava sobre um SELECT de todas as colunas do laudo
    # (respostas e HTML, > 1 MB cada).
    trinta_dias_atras = datetime.now(timezone.utc) - timedelta(days=30)
    contagem_por_modelo = (
        db.query(
            ReportTemplate.name,
            func.count(Report.id),
            func.count(case((Report.created_at >= trinta_dias_atras, Report.id))),
        )
        .join(Report, Report.template_id == ReportTemplate.id)
        .join(Patient, Report.patient_id == Patient.id)
        .filter(Patient.owner_id == current.id)
        .group_by(ReportTemplate.name)
        .order_by(func.count(Report.id).desc())
        .all()
    )
    total_reports = sum(contagem for _, contagem, _ in contagem_por_modelo)
    reports_last_30_days = sum(recentes for _, _, recentes in contagem_por_modelo)

    return StatsSummary(
        total_patients=total_patients,
        total_reports=total_reports,
        reports_last_30_days=reports_last_30_days,
        reports_by_template=[
            StatsByTemplate(template_name=nome, count=contagem) for nome, contagem, _ in contagem_por_modelo
        ],
    )
