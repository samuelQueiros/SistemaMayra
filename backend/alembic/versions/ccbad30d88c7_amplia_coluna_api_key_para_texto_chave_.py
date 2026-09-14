"""amplia coluna api_key para texto (chave criptografada)

Revision ID: ccbad30d88c7
Revises: 069c31366544
Create Date: 2026-09-13 13:58:10.786617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccbad30d88c7'
down_revision: Union[str, None] = '069c31366544'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # batch_alter_table: SQLite não suporta ALTER COLUMN ... TYPE direto
    # (usado em dev/testes); em Postgres (produção) gera o ALTER normal.
    with op.batch_alter_table("ai_settings") as batch_op:
        batch_op.alter_column(
            "api_key",
            existing_type=sa.VARCHAR(length=500),
            type_=sa.Text(),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("ai_settings") as batch_op:
        batch_op.alter_column(
            "api_key",
            existing_type=sa.Text(),
            type_=sa.VARCHAR(length=500),
            existing_nullable=False,
        )
