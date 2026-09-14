from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
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

    total_patients = db.query(Patient).filter(Patient.owner_id == current.id).count()

    total_reports = (
        db.query(Report)
        .join(Patient, Report.patient_id == Patient.id)
        .filter(Patient.owner_id == current.id)
        .count()
    )

    trinta_dias_atras = datetime.now(timezone.utc) - timedelta(days=30)
    reports_last_30_days = (
        db.query(Report)
        .join(Patient, Report.patient_id == Patient.id)
        .filter(Patient.owner_id == current.id, Report.created_at >= trinta_dias_atras)
        .count()
    )

    contagem_por_modelo = (
        db.query(ReportTemplate.name, func.count(Report.id))
        .join(Report, Report.template_id == ReportTemplate.id)
        .join(Patient, Report.patient_id == Patient.id)
        .filter(Patient.owner_id == current.id)
        .group_by(ReportTemplate.name)
        .order_by(func.count(Report.id).desc())
        .all()
    )

    return StatsSummary(
        total_patients=total_patients,
        total_reports=total_reports,
        reports_last_30_days=reports_last_30_days,
        reports_by_template=[
            StatsByTemplate(template_name=nome, count=contagem) for nome, contagem in contagem_por_modelo
        ],
    )
