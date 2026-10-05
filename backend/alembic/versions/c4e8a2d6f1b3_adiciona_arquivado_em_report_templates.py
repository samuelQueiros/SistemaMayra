"""adiciona arquivado em report_templates (modelos de protocolo)

Revision ID: c4e8a2d6f1b3
Revises: b7c3e1f2a9d4
Create Date: 2026-10-05 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e8a2d6f1b3'
down_revision: Union[str, None] = 'b7c3e1f2a9d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "report_templates",
        sa.Column("arquivado", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("report_templates", "arquivado")
