"""v2.558 (Aşama 5 V5 + Aşama 6 E1/E2) — kısıt yüzdesi, alım kanalı, saha toplayıcısı kimliği ve idempotent alım defteri.

canli_ornek.kisit_yuzde: cihazın raporladığı güç kısması (701 ThrotPct; 704/123 azami güç sınırından türetilmiş) — talimat değil, cihaz raporu.
canli_ornek.kanal: 'dogrudan' (PVQuant sunucusu okudu) | 'edge' (saha toplayıcısı gönderdi).
edge_toplayici: santrala bağlı toplayıcı kimliği; anahtarın yalnız SHA-256 özeti saklanır (kullanıcı API anahtarlarından ayrı; kapsam tek santral).
edge_alim: (plant, toplayıcı, sıra) birincil anahtarlı alım defteri — aynı sıra yeniden gelirse içerik özeti eşitse yinelenen (sessiz kabul), değilse çatışma.
Hepsi RLS'li.

Revision ID: v2558_edge_kisit
Revises: v2556_bulut_kimlik
"""
from alembic import op

revision = "v2558_edge_kisit"
down_revision = "v2556_bulut_kimlik"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE canli_ornek ADD COLUMN IF NOT EXISTS kisit_yuzde DOUBLE PRECISION")
    op.execute("ALTER TABLE canli_ornek ADD COLUMN IF NOT EXISTS kanal TEXT NOT NULL DEFAULT 'dogrudan' CHECK (kanal IN ('dogrudan','edge'))")
    op.execute("""
    CREATE TABLE IF NOT EXISTS edge_toplayici (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      ad TEXT NOT NULL,
      prefix TEXT NOT NULL,
      anahtar_hash TEXT NOT NULL UNIQUE,
      durum TEXT NOT NULL DEFAULT 'etkin' CHECK (durum IN ('etkin','iptal')),
      olusturma TIMESTAMPTZ NOT NULL DEFAULT now(),
      son_gorulme TIMESTAMPTZ,
      son_sira BIGINT,
      iptal_zamani TIMESTAMPTZ,
      notlar TEXT
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS edge_toplayici_plant ON edge_toplayici(plant_id)")
    op.execute("ALTER TABLE edge_toplayici ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE edge_toplayici FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_edge_toplayici ON edge_toplayici")
    op.execute("CREATE POLICY p_edge_toplayici ON edge_toplayici USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT, UPDATE ON edge_toplayici TO pvq_app")
    op.execute("""
    CREATE TABLE IF NOT EXISTS edge_alim (
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      toplayici_id UUID NOT NULL REFERENCES edge_toplayici(id),
      sira BIGINT NOT NULL,
      icerik_ozeti TEXT NOT NULL,
      ts_utc TIMESTAMPTZ,
      alinma TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (plant_id, toplayici_id, sira)
    )""")
    op.execute("ALTER TABLE edge_alim ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE edge_alim FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_edge_alim ON edge_alim")
    op.execute("CREATE POLICY p_edge_alim ON edge_alim USING (tenant_id = current_setting('app.tenant_id')::uuid) WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT ON edge_alim TO pvq_app")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS edge_alim")
    op.execute("DROP TABLE IF EXISTS edge_toplayici")
    op.execute("ALTER TABLE canli_ornek DROP COLUMN IF EXISTS kanal")
    op.execute("ALTER TABLE canli_ornek DROP COLUMN IF EXISTS kisit_yuzde")
