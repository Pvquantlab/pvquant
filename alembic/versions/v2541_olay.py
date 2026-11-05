"""v2.541 (EK-3 DK-741/DK-743) — olay kaydına iki alan: `bildirim_zamani` (acil durum kesmesinde şebeke işletmecisinin «acil durum sona erdi»
bildiriminin tesise ulaştığı an; LÜY m.21(8): sona ermeden itibaren 15 dakika içinde telefon ve kalıcı veri saklayıcısı ile) ve `talimat_mw`
(YAL/YAT talimat miktarı, MW; yalnız kayıt — uzlaştırma hesabına girmez). Gerekçe son günü (DUY m.71/A(1): olayı takip eden 3 iş günü) türetilir,
saklanmaz.

Revision ID: v2541_olay
Revises: v2527_saatlik_detay
"""
from alembic import op

revision = "v2541_olay"
down_revision = "v2527_saatlik_detay"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE olay ADD COLUMN IF NOT EXISTS bildirim_zamani TIMESTAMPTZ")
    op.execute("ALTER TABLE olay ADD COLUMN IF NOT EXISTS talimat_mw DOUBLE PRECISION")
    op.execute("ALTER TABLE olay DROP CONSTRAINT IF EXISTS olay_talimat_mw_check")
    op.execute("ALTER TABLE olay ADD CONSTRAINT olay_talimat_mw_check CHECK (talimat_mw IS NULL OR talimat_mw > 0)")


def downgrade() -> None:
    op.execute("ALTER TABLE olay DROP CONSTRAINT IF EXISTS olay_talimat_mw_check")
    op.execute("ALTER TABLE olay DROP COLUMN IF EXISTS talimat_mw")
    op.execute("ALTER TABLE olay DROP COLUMN IF EXISTS bildirim_zamani")
