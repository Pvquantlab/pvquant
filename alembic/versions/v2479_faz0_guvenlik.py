"""v2.479 — Faz 0 güvenlik tabanı (24.10.2026, docs/YONETICI-PANELI-YOL-HARITASI-2026-10-24.md §1):

1) report_stats / report_log RLS politikaları. v2.103 tabloları tenant_id ile kurmuş ama politika YAZMAMIŞTI
   (kendi notu: «politika YAZILMADI — açık madde»). Kalıp v2.264 (webhooks) ile aynı: ENABLE + FORCE +
   USING/WITH CHECK tenant_id = app.tenant_id. Yazanlar zaten tenant_baglami kullanıyor (worker report_stats,
   report_service report_log) → davranış değişmez, yalnız sızıntı kapısı kapanır. GRANT'lar v2.103'te verilmişti.
2) users.oturum_surumu — jeton iptali. JWT'ye `sv` iddiası eklenir; pasifleştirme, rol değişimi, parola
   değişimi/sıfırlama ve yönetici 2FA sıfırlaması sürümü artırır; gecerli_kullanici DB'deki sürümle kıyaslar
   (60 sn önbellek). Eski jetonlarda `sv` yok → 0 sayılır; sürüm 0 olan kullanıcıda geçerli kalır (geriye uyumlu).

Revision ID: v2479_faz0_guvenlik
Revises: v2338_iki_adim
"""
from alembic import op

revision = "v2479_faz0_guvenlik"
down_revision = "v2338_iki_adim"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for tablo in ("report_stats", "report_log"):
        op.execute(f"ALTER TABLE {tablo} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tablo} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS p_{tablo} ON {tablo}")
        op.execute(f"CREATE POLICY p_{tablo} ON {tablo} "
                   "USING (tenant_id = current_setting('app.tenant_id')::uuid) "
                   "WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS oturum_surumu INTEGER NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS oturum_surumu")
    for tablo in ("report_stats", "report_log"):
        op.execute(f"DROP POLICY IF EXISTS p_{tablo} ON {tablo}")
        op.execute(f"ALTER TABLE {tablo} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tablo} DISABLE ROW LEVEL SECURITY")
