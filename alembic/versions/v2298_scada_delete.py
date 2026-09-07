"""v2298_scada_delete

Revision ID: v2298_scada_delete
Revises: v2289_paylasim
Create Date: 2026-09-08

v2.298 — "veriniz sizindir": müşteri kendi ham SCADA aralığını silebilsin diye uygulama rolüne
scada_hourly üzerinde DELETE verildi (bugüne dek hiç gerekmemişti — yalnız SELECT/INSERT/UPDATE vardı).
RLS politikası USING ile DELETE'i de kiracı duvarında tutar.
"""
from alembic import op

revision = "v2298_scada_delete"
down_revision = "v2289_paylasim"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT DELETE ON scada_hourly TO pvq_app")


def downgrade() -> None:
    op.execute("REVOKE DELETE ON scada_hourly FROM pvq_app")
