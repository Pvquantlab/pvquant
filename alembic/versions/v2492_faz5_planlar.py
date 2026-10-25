"""v2.492 — Faz 5 planlar (uyarı kipi) (26.10.2026, docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md §6 satır 4):

- planlar: ad PK, baslik, limitler (NULL = sınırsız): santral, kullanici, api_rpm, aylik_rapor, aylik_dis_api; notlar. Tohum: pilot /
  standart / kurumsal (ilk eşikler; sahip Planlar sayfasından değiştirir). tenants.plan'da olup tohumda olmayan adlar da (varsa) eklenir ki
  FK kırılmasın. tenants.plan → planlar(ad) FK (ON UPDATE CASCADE). ZORLAMA YOK: limitler yalnız rozet; müşteri uçları değişmez.
- RLS yok (sistem tablosu); pvq_app/pvq_api SELECT (+ pvq_api UPDATE — yalnız platform sahibi ucu yazar).

Revision ID: v2492_faz5_planlar
Revises: v2488_db_rolu
"""
from alembic import op

revision = "v2492_faz5_planlar"
down_revision = "v2488_db_rolu"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS planlar(
      ad TEXT PRIMARY KEY,
      baslik TEXT NOT NULL,
      santral_limit INTEGER,
      kullanici_limit INTEGER,
      api_rpm_limit INTEGER,
      aylik_rapor_limit INTEGER,
      aylik_dis_api_limit INTEGER,
      notlar TEXT,
      sira INTEGER NOT NULL DEFAULT 0,
      guncelleme TIMESTAMPTZ NOT NULL DEFAULT now());
    INSERT INTO planlar(ad, baslik, santral_limit, kullanici_limit, api_rpm_limit, aylik_rapor_limit, aylik_dis_api_limit, sira) VALUES
      ('pilot',    'Pilot',    3,  3,  60,  50,  5000,  1),
      ('standart', 'Standart', 25, 10, 120, 500, 50000, 2),
      ('kurumsal', 'Kurumsal', NULL, NULL, NULL, NULL, NULL, 3)
    ON CONFLICT (ad) DO NOTHING;
    INSERT INTO planlar(ad, baslik, sira)
      SELECT DISTINCT t.plan, initcap(t.plan), 9 FROM tenants t WHERE t.plan IS NOT NULL AND t.plan NOT IN (SELECT ad FROM planlar);
    ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_plan_fkey;
    ALTER TABLE tenants ADD CONSTRAINT tenants_plan_fkey FOREIGN KEY (plan) REFERENCES planlar(ad) ON UPDATE CASCADE;
    GRANT SELECT ON planlar TO pvq_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON planlar TO pvq_api;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_plan_fkey; DROP TABLE IF EXISTS planlar;")
