"""adiciona dados complementares do paciente e anexos para completar laudos

Revision ID: f2b8d4e6a1c7
Revises: e5f1a7c3b9d2
Create Date: 2026-10-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2b8d4e6a1c7'
down_revision: Union[str, None] = 'e5f1a7c3b9d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("dados_complementares", sa.JSON(), nullable=True))
    op.create_table(
        "patient_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("mime", sa.String(length=100), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("secao", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("sugestoes_json", sa.JSON(), nullable=True),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["psychologists.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_attachments_patient_id", "patient_attachments", ["patient_id"])
    op.create_index("ix_patient_attachments_report_id", "patient_attachments", ["report_id"])


def downgrade() -> None:
    op.drop_index("ix_patient_attachments_report_id", table_name="patient_attachments")
    op.drop_index("ix_patient_attachments_patient_id", table_name="patient_attachments")
    op.drop_table("patient_attachments")
    op.drop_column("patients", "dados_complementares")
