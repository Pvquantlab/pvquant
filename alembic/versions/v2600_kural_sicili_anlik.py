"""v2.600 (Faz 4 paketi F4-F, Stage 9 mevzuat kural sicili) — `kural_sicili_anlik`: kod içi sicilin yalnız-ekleme anlık görüntüsü.

Kural tablosu DB'de DÜZENLENMEZ (geri test ve CI deterministik; tek kaynak ext/turkiye/kural_sicili.py). Gece işi ve ihtiyaç hâlinde
servis, sicilin sha16'sı yeni ise bir satır ekler: sha16 (benzersiz), sicil_json, yazilim_surumu, olusturma. Sonuç meta'ları
(finansal etki, portföy, bağımsız doğrulama) `kural_sicili_sha` taşır; bu tablo o sha'nın hangi kural kümesi olduğunu söyler.
Kiracı verisi değildir (RLS yok); uygulama rolü yalnız ekler ve okur.

Revision ID: v2600_kural_sicili_anlik
Revises: v2599_santral_kunye
"""
from alembic import op

revision = "v2600_kural_sicili_anlik"
down_revision = "v2599_santral_kunye"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS kural_sicili_anlik (
        id BIGSERIAL PRIMARY KEY,
        sha16 TEXT NOT NULL UNIQUE,
        sicil_surumu TEXT NOT NULL,
        kayit_sayisi INT NOT NULL,
        sicil_json JSONB NOT NULL,
        yazilim_surumu TEXT,
        olusturma TIMESTAMPTZ NOT NULL DEFAULT now()
    )""")
    op.execute("GRANT SELECT, INSERT ON kural_sicili_anlik TO pvq_app")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE kural_sicili_anlik_id_seq TO pvq_app")
    op.execute("GRANT SELECT ON kural_sicili_anlik TO pvq_api")
    op.execute("REVOKE UPDATE, DELETE ON kural_sicili_anlik FROM pvq_api")
    op.execute("REVOKE UPDATE, DELETE ON kural_sicili_anlik FROM pvq_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kural_sicili_anlik")
