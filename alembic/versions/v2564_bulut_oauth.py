"""v2.564 (Aşama 3 K3/K4 dış girdi hazırlığı) — sahip OAuth onayı için tek kullanımlık durum defteri.

bulut_oauth_durum: sahibin «sağlayıcı sayfasında onay» akışı başlatılınca üretilen rastgele `state` değerinin yalnız SHA-256 özeti saklanır;
satır santrala, sağlayıcıya, bölgeye ve sahibin iki onayına bağlıdır, 15 dakikada sona erer ve tek kez kullanılır (geri dönüşte atomik işaretlenir).
Geri dönüş ucu kimliksiz gelir (sağlayıcı yönlendirir); kiracı/santral bu satırdan bulunur. Yetkilendirme kodu ve belirteçler bu tabloya YAZILMAZ;
belirteçler `bulut_kimlik`'e zarf şifreli iner. `sonuc` yalnız gizli içermeyen özet (durum, sağlayıcı santral listesi: kimlik/ad/kapasite).
RLS'li; kiracı bağlamı kendi satırlarını okur; geri dönüş sistem bağlamıyla özetten bulur (edge_toplayici deseni).

v2.565: bulut_kimlik.birim_kanit (jsonb) — portal dışa aktarımıyla birim kıyası özeti; «birim doğrulandı» yalnız belge yorumu uyumluysa.

Revision ID: v2564_bulut_oauth
Revises: v2558_edge_kisit
"""
from alembic import op

revision = "v2564_bulut_oauth"
down_revision = "v2558_edge_kisit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS bulut_oauth_durum (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES tenants(id),
      plant_id UUID NOT NULL REFERENCES plants(id),
      saglayici TEXT NOT NULL,
      bolge TEXT,
      state_hash TEXT NOT NULL UNIQUE,
      onay_json JSONB NOT NULL,
      aktor_id TEXT,
      olusturma TIMESTAMPTZ NOT NULL DEFAULT now(),
      bitis TIMESTAMPTZ NOT NULL,
      kullanildi BOOLEAN NOT NULL DEFAULT FALSE,
      kullanim_zamani TIMESTAMPTZ,
      sonuc JSONB
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS bulut_oauth_durum_plant ON bulut_oauth_durum(plant_id, olusturma DESC)")
    op.execute("ALTER TABLE bulut_oauth_durum ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE bulut_oauth_durum FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_bulut_oauth_durum ON bulut_oauth_durum")
    op.execute("CREATE POLICY p_bulut_oauth_durum ON bulut_oauth_durum USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON bulut_oauth_durum TO pvq_app")
    op.execute("ALTER TABLE bulut_kimlik ADD COLUMN IF NOT EXISTS birim_kanit JSONB")   # v2.565: birim kıyası özeti (ham referans yok)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bulut_oauth_durum")
    op.execute("ALTER TABLE bulut_kimlik DROP COLUMN IF EXISTS birim_kanit")
