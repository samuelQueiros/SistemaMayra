"""adiciona guardian_form_submissions

Revision ID: a1dfba2f3f57
Revises: 9d06aea4a965
Create Date: 2026-09-28 15:49:04.668782

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1dfba2f3f57'
down_revision: Union[str, None] = '9d06aea4a965'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guardian_form_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=255), nullable=False),
        sa.Column("respondent_name", sa.String(length=255), nullable=False),
        sa.Column("respondent_relation", sa.String(length=100), nullable=True),
        sa.Column("filled_at", sa.Date(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("validated_by_id", sa.Uuid(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["validated_by_id"], ["psychologists.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["psychologists.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_guardian_form_submissions_patient_id"),
        "guardian_form_submissions",
        ["patient_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_guardian_form_submissions_patient_id"),
        table_name="guardian_form_submissions",
    )
    op.drop_table("guardian_form_submissions")
