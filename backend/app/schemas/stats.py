"""Formato do painel de números de uso."""

from pydantic import BaseModel


class StatsByTemplate(BaseModel):
    template_name: str
    count: int


class StatsSummary(BaseModel):
    total_patients: int
    total_reports: int
    reports_last_30_days: int
    reports_by_template: list[StatsByTemplate]
