"""v2.572 (Faz 1 paketi F1-A, Stage 2 tahmin arşivi) — koşu künyesi: her tahmin koşusu hangi kalibrasyon, hangi öğrenilmiş
model, hangi konformal ayar, hangi NWP yayını, hangi yazılım sürümü ve hangi kapasiteyle üretildiğini kendi satırında taşır.

forecast_runs yeni sütunlar (hepsi NULL olabilir; eski koşular için boşluk UYDURULMAZ):
  kalibrasyon_id UUID          koşu anında aktif calibrations.id (Mod B/C), yoksa NULL
  ml_model_id UUID             koşu anında yüklenen ml_models.id (Mod C, artefakt diskte bulunduysa), yoksa NULL
  konformal_hesap_zamani       uygulanan konformal ayarın hesap zamanı (q̂ sürümü), yoksa NULL
  nwp_kosu_zamani              kullanılan NWP koşusunun yayın zamanı (meteo_arsiv.kosu_zamani), Open-Meteo yolunda NULL
  ufuk_saat INT                koşunun yazılan saat sayısı
  kapasite_kwp NUMERIC         koşu anındaki plants.capacity_kwp (sonradan değişirse karne normalizasyonu bu değeri kullanır)
  yazilim_surumu TEXT          PVQ_SURUM ortam değişkeni (imaj kurulurken git describe), yoksa NULL
  etiket TEXT                  meteo_ozet_json->>'etiket' sütun hâli: NULL (gece/program) | 'gun_ici' | 'elle'
Mevcut satırlarda yalnız `etiket` JSON'dan türetilerek doldurulur (bilgi zaten kayıttaydı; başka alan geriye dönük yazılmaz).
Koşu ve değer satırları yine UPDATE/DELETE edilmez; değişmezlik tetikleyicisi bu göçte YOK (ayrı karar).

Revision ID: v2572_kosu_kunyesi
Revises: v2570_sir_kasasi
"""
from alembic import op

revision = "v2572_kosu_kunyesi"
down_revision = "v2570_sir_kasasi"
branch_labels = None
depends_on = None

SUTUNLAR = (
    ("kalibrasyon_id", "UUID"), ("ml_model_id", "UUID"), ("konformal_hesap_zamani", "TIMESTAMPTZ"),
    ("nwp_kosu_zamani", "TIMESTAMPTZ"), ("ufuk_saat", "INT"), ("kapasite_kwp", "NUMERIC"),
    ("yazilim_surumu", "TEXT"), ("etiket", "TEXT"),
)


def upgrade() -> None:
    for ad, tip in SUTUNLAR:
        op.execute(f"ALTER TABLE forecast_runs ADD COLUMN IF NOT EXISTS {ad} {tip}")
    op.execute("UPDATE forecast_runs SET etiket = meteo_ozet_json->>'etiket' WHERE etiket IS NULL AND meteo_ozet_json->>'etiket' IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_forecast_runs_plant_etiket ON forecast_runs(plant_id, etiket)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_forecast_runs_plant_etiket")
    for ad, _ in reversed(SUTUNLAR):
        op.execute(f"ALTER TABLE forecast_runs DROP COLUMN IF EXISTS {ad}")
