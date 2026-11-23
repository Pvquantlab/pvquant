"""v2650 — ensemble HAM PV bandının değiştirilemez arşivi (Faz 1 A1, 24.11.2026; g2/A_HAM_GEFS_ARSIV_TASARIM.md).

NE: `forecast_values`'a beş NULL'lanabilir kolon — `ens_p10_kw`, `ens_p25_kw`, `ens_p75_kw`, `ens_p90_kw`, `ens_yayilim_kw` (kW) —
ve `forecast_runs`'a `bant_json` (jsonb). DEFAULT yok, geri doldurma yok: hypertable'da metadata-only ALTER, eski satırlar NULL kalır.

ADLANDIRMA (yanıltmamak için): bu kolonlar HAM GEFS METEOROLOJİSİ DEĞİLDİR. Ham üye meteosu (ghi/temp/wind/cloud, üye × saat)
`meteo_uye` tablosundadır ve 45 gün sonra silinir. Buradaki değerler ensemble üyelerinden TÜRETİLEN PV güç kantilleridir:
`ensemble_service.uye_kantilleri` çıktısı — üye başına fizik koşusu (kW), hibrit oranıyla ölçeklenmiş, P50 ile tutarlı
(p10 ≤ p25 ≤ p50 ≤ p75 ≤ p90), ≥ 0 kırpılmış; `ens_yayilim_kw` üye güçlerinin standart sapması. Ufuk σ / sapma / konformal
katmanlarından ÖNCEKİ hâl (servis edilen p10…p90 bu katmanlardan SONRAKİ hâldir). Bant kaynağı model ise ya da saat üye ufku
dışındaysa NULL ("yoktu", 0 değil). `bant_json` = koşunun `sonuc.bant` meta'sı ({kaynak, uye, yayilim_ort_kw} | {kaynak:'model', not}).

GERİ DÖNÜŞ: önce uygulama geri alımı (eski kod yeni kolonları görmez, NULL birikir — veri kaybı yok); kolon düşürme ayrı, kontrollü
adım (downgrade yalnız bu arşiv kolonlarını kaldırır; servis kantilleri ve künye etkilenmez). Göç HER ZAMAN koddan önce uygulanır:
yeni kod eski şemada INSERT'te düşer (koşu rollback — tek işlem sözleşmesi).

Revision ID: v2650_ens_ham_bant
Revises: v2642_platform_kurtarma
"""
from alembic import op

revision = "v2650_ens_ham_bant"
down_revision = "v2642_platform_kurtarma"
branch_labels = None
depends_on = None

ENS_KOLONLAR = ("ens_p10_kw", "ens_p25_kw", "ens_p75_kw", "ens_p90_kw", "ens_yayilim_kw")


def upgrade() -> None:
    for k in ENS_KOLONLAR:
        op.execute(f"ALTER TABLE forecast_values ADD COLUMN IF NOT EXISTS {k} DOUBLE PRECISION")
    op.execute("ALTER TABLE forecast_runs ADD COLUMN IF NOT EXISTS bant_json JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE forecast_runs DROP COLUMN IF EXISTS bant_json")
    for k in reversed(ENS_KOLONLAR):
        op.execute(f"ALTER TABLE forecast_values DROP COLUMN IF EXISTS {k}")
