"""v2289_paylasim

Revision ID: v2289_paylasim
Revises: v2279_skill_cliper
Create Date: 2026-09-07

v2.289 — Tablo 3.5 satır 6: kuruluşlar arası veri paylaşımı (SFA kalıbı). Paylaşım satırı iki kiracıyı birden
ilgilendirir: RLS politikası kaynak YA DA hedef kiracıya görünürlük verir; yazma yalnız kaynak kiracıya.
Denetim izi paylasim_denetim'de (kaynak kiracı okur).
"""
from alembic import op

revision = "v2289_paylasim"
down_revision = "v2279_skill_cliper"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS paylasimlar ("
        " id uuid PRIMARY KEY DEFAULT gen_random_uuid(),"
        " kaynak_tenant uuid NOT NULL, hedef_tenant uuid NOT NULL,"
        " plant_id uuid NOT NULL REFERENCES plants(id),"
        " izinler jsonb NOT NULL, takma_ad text,"
        " baslangic timestamptz NOT NULL DEFAULT now(), bitis timestamptz,"
        " iptal boolean NOT NULL DEFAULT false,"
        " olusturan uuid, created_at timestamptz NOT NULL DEFAULT now())")
    op.execute("ALTER TABLE paylasimlar ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE paylasimlar FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_paylasimlar ON paylasimlar")
    op.execute("CREATE POLICY p_paylasimlar ON paylasimlar "
               "USING (kaynak_tenant = current_setting('app.tenant_id')::uuid OR hedef_tenant = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (kaynak_tenant = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT, UPDATE ON paylasimlar TO pvq_app")
    op.execute(
        "CREATE TABLE IF NOT EXISTS paylasim_denetim ("
        " id bigserial PRIMARY KEY, tenant_id uuid NOT NULL,"           # kaynak kiracı (izin sahibi) — RLS standart kalıp
        " zaman timestamptz NOT NULL DEFAULT now(), kullanici uuid, kullanici_tenant uuid,"
        " eylem text NOT NULL, plant_id uuid, sonuc text NOT NULL, not_ text)")
    op.execute("ALTER TABLE paylasim_denetim ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE paylasim_denetim FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_paylasim_denetim ON paylasim_denetim")
    op.execute("CREATE POLICY p_paylasim_denetim ON paylasim_denetim "
               "USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (true)")   # hedef tarafın okuma kararı da kaynak kiracının iznine yazılır
    op.execute("GRANT SELECT, INSERT ON paylasim_denetim TO pvq_app")
    op.execute("GRANT USAGE ON SEQUENCE paylasim_denetim_id_seq TO pvq_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS paylasim_denetim")
    op.execute("DROP TABLE IF EXISTS paylasimlar")
