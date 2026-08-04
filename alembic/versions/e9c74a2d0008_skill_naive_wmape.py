"""0008_skill_naive_wmape

Revision ID: e9c74a2d0008
Revises: d4e52a0c0007
Create Date: 2026-08-04

M1 (Rapor Spesifikasyonu v2.0, S4): naif WMAPE artik TURETILMEZ, SAKLANIR.
v2.76'daki API turetmesi (naif = mape/(1-skill/100)) gecis cozumuydu;
sartname naive_wmape'yi birinci sinif olcum yapti (S4 kesikli referans
cizgisi + Excel M5 kolonu buradan okunacak). Gecmis satirlar ayni
ozdeslikle backfill edilir — turetme, icat degil (worker tanimi:
skill = 100*(1-mape/naif)). skill_vs_naive=100 korumasi: payda sifir.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e9c74a2d0008'
down_revision: Union[str, Sequence[str], None] = 'd4e52a0c0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TABLE skill_daily "
        "ADD COLUMN IF NOT EXISTS naive_wmape DOUBLE PRECISION")
    op.execute(
        "UPDATE skill_daily "
        "SET naive_wmape = mape / (1 - skill_vs_naive / 100.0) "
        "WHERE naive_wmape IS NULL AND skill_vs_naive IS NOT NULL "
        "AND skill_vs_naive < 100")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE skill_daily DROP COLUMN IF EXISTS naive_wmape")
