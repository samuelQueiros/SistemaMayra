"""adiciona bio profissional e credenciais assinatura

Revision ID: 9d06aea4a965
Revises: d11dc0afd0e2
Create Date: 2026-09-28 15:31:49.776858

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d06aea4a965'
down_revision: Union[str, None] = 'd11dc0afd0e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("psychologists", sa.Column("bio_profissional", sa.Text(), nullable=True))
    op.add_column("psychologists", sa.Column("credenciais_assinatura", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("psychologists", "credenciais_assinatura")
    op.drop_column("psychologists", "bio_profissional")
