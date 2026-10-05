"""adiciona capa personalizada da psicologa

Revision ID: b7c3e1f2a9d4
Revises: a1dfba2f3f57
Create Date: 2026-10-05 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c3e1f2a9d4'
down_revision: Union[str, None] = 'a1dfba2f3f57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("psychologists", sa.Column("capa_arquivo", sa.String(length=500), nullable=True))
    op.add_column("psychologists", sa.Column("capa_config", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("psychologists", "capa_config")
    op.drop_column("psychologists", "capa_arquivo")
