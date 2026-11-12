"""v2.601 (Faz 4 paketi F4-G, Stage 8 finansal motor sınırı) — `piyasa_fiyat_surum`: saatlik PTF/SMF/yön satırlarının YALNIZ-EKLEME sürüm tarihçesi.

Bulgu M6: `piyasa_fiyat` üzerine yazılır (gün öncesi PTF → gece tam satır; geri doldurma; EPİAŞ düzeltmesi) — geçmiş bir finansal sonucun
hangi fiyatla hesaplandığı kaybolur, yeniden hesap eski sonucu üretmeyebilir. Bu tablo her yazımda DEĞİŞEN satırın yeni hâlini ekler
(ts_utc, ptf, smf, yon, kaynak, alinma); `piyasa_service.fiyatlar(index, itibariyle=T)` T anında geçerli sürümü okur, sonuç meta'ları
`fiyat.sha16` + `fiyat.itibariyle` taşır. `piyasa_fiyat` güncel görünüm olarak kalır (okuyucular değişmez).
Tek seferlik doldurma: mevcut `piyasa_fiyat` satırları `alinma = guncelleme` ile ilk sürüm olarak kopyalanır.
Kiracı verisi değildir (RLS yok); uygulama rolü ekler ve okur, UPDATE/DELETE yok.

Revision ID: v2601_piyasa_fiyat_surum
Revises: v2600_kural_sicili_anlik
"""
from alembic import op

revision = "v2601_piyasa_fiyat_surum"
down_revision = "v2600_kural_sicili_anlik"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS piyasa_fiyat_surum (
        id BIGSERIAL PRIMARY KEY,
        ts_utc TIMESTAMPTZ NOT NULL,
        ptf DOUBLE PRECISION,
        smf DOUBLE PRECISION,
        yon TEXT,
        kaynak TEXT NOT NULL,
        alinma TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS piyasa_fiyat_surum_ts_alinma ON piyasa_fiyat_surum(ts_utc, alinma DESC)")
    op.execute("INSERT INTO piyasa_fiyat_surum(ts_utc, ptf, smf, yon, kaynak, alinma) "
               "SELECT f.ts_utc, f.ptf, f.smf, f.yon, f.kaynak, f.guncelleme FROM piyasa_fiyat f "
               "WHERE NOT EXISTS (SELECT 1 FROM piyasa_fiyat_surum v WHERE v.ts_utc = f.ts_utc)")
    op.execute("GRANT SELECT, INSERT ON piyasa_fiyat_surum TO pvq_app")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE piyasa_fiyat_surum_id_seq TO pvq_app")
    op.execute("GRANT SELECT ON piyasa_fiyat_surum TO pvq_api")
    op.execute("REVOKE UPDATE, DELETE ON piyasa_fiyat_surum FROM pvq_api")
    op.execute("REVOKE UPDATE, DELETE ON piyasa_fiyat_surum FROM pvq_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS piyasa_fiyat_surum")
