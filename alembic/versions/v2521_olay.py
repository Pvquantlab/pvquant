"""v2.521 (P1a) — olay kaydı: planlı bakım, arıza, talimat (YAL/YAT), acil durum kesmesi, şebeke kesintisi, hasar. Her olay: başlangıç,
bitiş (açık olay = NULL), etkilenen güç (kW; NULL = tesisin tamamı), neden, EAK gerekçe sütunu (TPYS EAK.csv), istisna bayrağı, kanıt notu.
Tüketiciler: KGÜP/EAK dosyası (saatlik EAK düşümü ve gerekçe sütunu), kullanılabilirlik istisnası, aylık arıza sayacı (KÜPST n katsayısı ve
alarm), dâhilî bilgi geri sayımı (Karar 14967, yürürlük belirsiz), hasar dosyası (CSV). RLS kiracı bağlamı; pvq_app SELECT/INSERT/UPDATE
(silme yok: olay «iptal» durumuna alınır; geçmiş kayıt korunur).

Revision ID: v2521_olay
Revises: v2520_yekdem
"""
from alembic import op

revision = "v2521_olay"
down_revision = "v2520_yekdem"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS olay (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      tur TEXT NOT NULL CHECK (tur IN ('planli_bakim', 'ariza', 'talimat_yat', 'talimat_yal', 'acil_kesme', 'sebeke_kesintisi', 'hasar')),
      baslangic TIMESTAMPTZ NOT NULL,
      bitis TIMESTAMPTZ,
      etkilenen_kw DOUBLE PRECISION,
      neden TEXT,
      eak_gerekcesi TEXT CHECK (eak_gerekcesi IS NULL OR eak_gerekcesi IN ('kaynak_yetersizligi', 'iklim_verim', 'mucbir', 'dissal', 'guvenlik')),
      kanit TEXT,
      durum TEXT NOT NULL DEFAULT 'acik' CHECK (durum IN ('acik', 'kapali', 'iptal')),
      olusturan UUID,
      olusturma TIMESTAMPTZ NOT NULL DEFAULT now(),
      guncelleme TIMESTAMPTZ NOT NULL DEFAULT now(),
      CHECK (bitis IS NULL OR bitis > baslangic),
      CHECK (etkilenen_kw IS NULL OR etkilenen_kw > 0)
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS olay_plant_bas ON olay(plant_id, baslangic DESC)")
    op.execute("ALTER TABLE olay ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE olay FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_olay ON olay")
    op.execute("CREATE POLICY p_olay ON olay USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT, UPDATE ON olay TO pvq_app")   # DELETE yok — iptal durumu


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS olay")
