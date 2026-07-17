"""meteo_ozet — forecast_runs'a kosu-duzeyi meteo ozet blob'u

Fable 5 v1.8 karari: 'saatlik meteo arsivi P4-sonrasi yasak; kosu-duzeyi
ozet tuketici-kanitli istisna' (hero hava kartlari + icgoru sablon 1).

Revision ID: 2e8fd90d43a4
Revises: d688ccc7983c
Create Date: 2026-07-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2e8fd90d43a4'
down_revision: Union[str, Sequence[str], None] = 'd688ccc7983c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """forecast_runs tablosuna meteo_ozet_json (JSONB) kolonu ekle."""
    op.add_column(
        'forecast_runs',
        sa.Column('meteo_ozet_json', postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column('forecast_runs', 'meteo_ozet_json')
