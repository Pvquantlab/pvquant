"""v2328_vitrin_basvuru

Revision ID: v2328_vitrin_basvuru
Revises: v2323_hypertable_parca
Create Date: 2026-09-15

v2.328 — vitrin "Karneni başlat" başvuru hattı: kamuya açık formdan gelen
talepler bu tabloya düşer, panelde yönetici görür. Kiracı tablosu DEĞİL —
başvuru henüz kiracı olmayan birinden gelir; platform sahibinin yöneticisi
okur (bugünkü tek-kiracılı kurulumda bu, hesabın yöneticisidir; gerçek çok
kiracılılıkta platform-sahibi rolüne taşınacak — bilinçli basitlik).
"""
from alembic import op

revision = "v2328_vitrin_basvuru"
down_revision = "v2323_hypertable_parca"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE vitrin_basvurulari(
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      eposta TEXT NOT NULL,
      santral_adi TEXT,
      kurulu_guc_kwp DOUBLE PRECISION,
      kaynak TEXT NOT NULL DEFAULT 'vitrin',
      okundu BOOLEAN NOT NULL DEFAULT false,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
    GRANT SELECT, INSERT, UPDATE ON vitrin_basvurulari TO pvq_app;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE vitrin_basvurulari")
