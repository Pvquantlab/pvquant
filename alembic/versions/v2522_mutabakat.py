"""v2.522 (P2b-1) — EPİAŞ uzlaştırma bildirimi kalemleri: müşterinin EPYS'den indirdiği «Uzlaştırma Bildirimi» dosyasındaki (CSV/XLSX)
aylık alacak/borç kalemleri (GÖP, GİP, YEK, dengesizlik, DGP, GDDK, fark tutarı, SBDT, PİÜ, KÜPST, gecikme zammı, …; 02-23) santral ve
dönem bazında saklanır; PVQuant'ın yeniden hesabıyla kalem kalem mutabakat (mutabakat_service). Her yükleme ayrı yukleme_id ile tutulur,
son yükleme geçerlidir; silme/güncelleme yok (geçmiş korunur). RLS kiracı bağlamı; pvq_app SELECT/INSERT.

Revision ID: v2522_mutabakat
Revises: v2521_olay
"""
from alembic import op

revision = "v2522_mutabakat"
down_revision = "v2521_olay"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS uzlastirma_bildirimi (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      donem DATE NOT NULL,
      surum TEXT NOT NULL CHECK (surum IN ('on', 'nihai')),
      yukleme_id UUID NOT NULL,
      kalem TEXT NOT NULL,
      kalem_ad TEXT,
      yon TEXT NOT NULL CHECK (yon IN ('alacak', 'borc')),
      tutar_tl DOUBLE PRECISION NOT NULL,
      dosya_adi TEXT,
      sha256 TEXT,
      dosya_donem DATE,
      dosya_surum TEXT,
      surum_kaynagi TEXT CHECK (surum_kaynagi IS NULL OR surum_kaynagi IN ('dosya', 'kullanici', 'varsayilan')),
      yukleyen UUID,
      olusturma TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS uzl_bildirim_plant_donem ON uzlastirma_bildirimi(plant_id, donem, olusturma DESC)")
    op.execute("ALTER TABLE uzlastirma_bildirimi ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE uzlastirma_bildirimi FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_uzl_bildirim ON uzlastirma_bildirimi")
    op.execute("CREATE POLICY p_uzl_bildirim ON uzlastirma_bildirimi USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT ON uzlastirma_bildirimi TO pvq_app")   # güncelleme/silme yok — her yükleme yeni sürüm


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS uzlastirma_bildirimi")
