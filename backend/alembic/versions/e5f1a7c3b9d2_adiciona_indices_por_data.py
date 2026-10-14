"""adiciona índices por data em reports e report_change_logs

Revision ID: e5f1a7c3b9d2
Revises: c4e8a2d6f1b3
Create Date: 2026-10-14 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5f1a7c3b9d2'
down_revision: Union[str, None] = 'c4e8a2d6f1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Histórico do paciente: laudos de um paciente, mais recentes primeiro.
    op.create_index("ix_reports_patient_id_created_at", "reports", ["patient_id", "created_at"])
    # Registro de atividades: edições mais recentes primeiro (até 500).
    op.create_index("ix_report_change_logs_created_at", "report_change_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_report_change_logs_created_at", table_name="report_change_logs")
    op.drop_index("ix_reports_patient_id_created_at", table_name="reports")
