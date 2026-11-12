"""v2.599 (Faz 4 paketi F4-E, Stage 6 santral kimliği) — tarihli `santral_kunye`.

Santralın kimlik ve güç tanımları (DC/AC/EAK, bağlantı türü, gerilim, segment, lisans durumu, UEVÇB/EIC/EPİAŞ kimlikleri, sayaç
kimliği, ölçüm sınırı) tarihli sürümlerle tutulur: her değişiklik yeni satır, eski satır `gecerli_bit` ile kapanır; geçmiş dönem
hesapları o tarihteki künyeyi okur. `plants` «güncel görünüm» olarak kalır; `capacity_kwp`/`ac_limit_kw` ve `params_json` kimlik
anahtarları (eak_kw, segment, uevcb, epias_santral_id) ÇİFT yazılır (geriye uyum: eski okuyucular bozulmaz), yeni okuma
`santral_kunye`'den (services/santral_kunye_service).

Tek seferlik doldurma: her santral için bir satır (`gecerli_bas` = 2000-01-01 «başlangıçtan beri», kayıt günü notta, `kaynak='goc'`, `dogrulama='beyan'`) mevcut
`plants` + `params_json` değerleriyle; bilinmeyen alan NULL (uydurma yok).

Revision ID: v2599_santral_kunye
Revises: v2598_kalite
"""
from alembic import op

revision = "v2599_santral_kunye"
down_revision = "v2598_kalite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS santral_kunye (
        id BIGSERIAL PRIMARY KEY,
        tenant_id UUID NOT NULL,
        plant_id UUID NOT NULL REFERENCES plants(id),
        gecerli_bas DATE NOT NULL,
        gecerli_bit DATE,
        dc_kwp NUMERIC,
        ac_kw NUMERIC,
        eak_kw NUMERIC,
        baglanti_turu TEXT CHECK (baglanti_turu IS NULL OR baglanti_turu IN ('iletim', 'dagitim')),
        gerilim_kv NUMERIC,
        segment TEXT,
        lisans_durumu TEXT CHECK (lisans_durumu IS NULL OR lisans_durumu IN ('lisansli', 'lisanssiz', 'muaf')),
        uevcb_kod TEXT,
        eic TEXT,
        epias_santral_id TEXT,
        sayac_kimligi TEXT,
        olcum_siniri TEXT CHECK (olcum_siniri IS NULL OR olcum_siniri IN ('inverter_ac', 'plant_gross_ac', 'pcc_net', 'settlement')),
        kaynak TEXT NOT NULL DEFAULT 'beyan' CHECK (kaynak IN ('kayit', 'beyan', 'belge', 'goc', 'epias')),
        dogrulama TEXT NOT NULL DEFAULT 'beyan' CHECK (dogrulama IN ('beyan', 'belgeli', 'dogrulandi')),
        belge_adi TEXT,
        notlar TEXT,
        olusturan UUID,
        olusturma TIMESTAMPTZ NOT NULL DEFAULT now(),
        CHECK (gecerli_bit IS NULL OR gecerli_bit > gecerli_bas),
        UNIQUE (plant_id, gecerli_bas)
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_santral_kunye_plant_gecerli ON santral_kunye(plant_id, gecerli_bas DESC)")
    op.execute("ALTER TABLE santral_kunye ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE santral_kunye FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS p_santral_kunye ON santral_kunye")
    op.execute("CREATE POLICY p_santral_kunye ON santral_kunye USING (tenant_id = current_setting('app.tenant_id')::uuid) "
               "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT, UPDATE ON santral_kunye TO pvq_app")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE santral_kunye_id_seq TO pvq_app")
    op.execute("GRANT SELECT ON santral_kunye TO pvq_api")
    op.execute("REVOKE INSERT, UPDATE, DELETE ON santral_kunye FROM pvq_api")   # doğrudan yetki yok; pvq_api pvq_app üyesi olduğundan kalıtla S/I/U edinir (uygulama rolü yazar), DELETE kimsede yok
    # tek seferlik doldurma — yalnız bilinen değerler
    op.execute("""
    INSERT INTO santral_kunye(tenant_id, plant_id, gecerli_bas, dc_kwp, ac_kw, eak_kw, segment, lisans_durumu, uevcb_kod, epias_santral_id, kaynak, dogrulama, notlar)
    SELECT p.tenant_id, p.id, DATE '2000-01-01', p.capacity_kwp, p.ac_limit_kw,
           NULLIF(p.params_json->>'eak_kw', '')::numeric,
           NULLIF(p.params_json->>'segment', ''),
           CASE WHEN p.params_json->>'segment' LIKE 'lisansli%' OR p.params_json->>'segment' = 'yeka' THEN 'lisansli'
                WHEN p.params_json->>'segment' LIKE 'lisanssiz%' OR p.params_json->>'segment' = 'oz_tuketim_saatlik' THEN 'lisanssiz'
                ELSE NULL END,
           NULLIF(p.params_json->>'uevcb', ''), NULLIF(p.params_json->>'epias_santral_id', ''),
           'goc', 'beyan', 'v2.599 göçü: plants + params_json değerlerinden tek seferlik doldurma; başlangıçtan beri (kayıt: ' || CAST(p.created_at AT TIME ZONE 'UTC' AS date) || ')'
    FROM plants p
    WHERE NOT EXISTS (SELECT 1 FROM santral_kunye k WHERE k.plant_id = p.id)""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS santral_kunye")
