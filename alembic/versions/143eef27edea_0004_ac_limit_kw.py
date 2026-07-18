"""0004_ac_limit_kw

Revision ID: 143eef27edea
Revises: 95d3cc814e0a
Create Date: 2026-07-18 17:52:22.585974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '143eef27edea'
down_revision: Union[str, Sequence[str], None] = '95d3cc814e0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # B-1 Adım 1: AC invertör tavanı (nullable) — pilot-öncesi kapı hazırlığı
    op.add_column("plants",
        sa.Column("ac_limit_kw", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("plants", "ac_limit_kw")
