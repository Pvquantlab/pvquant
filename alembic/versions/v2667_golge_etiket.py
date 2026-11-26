"""v2667 — forecast_runs etiket sözlüğüne 'golge' (Faz 1 G1 gölge depolama; 26.11.2026, kısıtlı kapsam onayı).

NE: `forecast_runs_etiket_check` CHECK kısıtı düşürülüp sözlüğe 'golge' EKLENMİŞ hâliyle yeniden kurulur. Yalnız genişletme:
kolon, varsayılan ('yayin'), NOT NULL ve mevcut kayıtlar değişmez; eski 8 etiket aynen geçerli kalır. Başka tablo/kısıt yok.

NEDEN: gölge Mod A/B/C paralel koşuları (golge_service) müşteri koşusundan ayrı, AÇIK etiketle arşivlensin; müşteri yüzeyleri
(son koşu, yayımlanmış koşu, karne, program, portföy, bağımsız doğrulama, koşu geçmişi, damga, kullanım sayacı) bu etiketi
karne_kurali.DISLANAN_ETIKET / golge_disi_sql ile dışlar. Göç olmadan arsive_yaz 'golge'yi reddediyordu (G1 BLOCKED).

UYUMLULUK: canlıdaki uygulama (v2.661) 'golge' yazmaz; kısıtın genişlemesi onu etkilemez. Ancak eski kodun yayin_kosu_sql'i gölgeyi
tanımaz (yayın sayar) → gölge satırı yalnız G3 dışlamasını içeren kod canlıya çıktıktan SONRA yazılabilir (yazan tek yol
golge_service.golge_arsivle, yeni kod). Sıra: göç → kod; ters sıra da veri kaybı yaratmaz (gölge satırı henüz yoktur).

GERİ DÖNÜŞ: downgrade eski 8'li kısıtı geri kurar; 'golge' satırı VARSA sessizce silmez/çevirmez — hata verip durur (operatör
kararı: satırları taşı/sil, sonra downgrade). Mevcut kısıt global olarak KAPATILMAZ; yalnız sözlük değişir.

Revision ID: v2667_golge_etiket
Revises: v2650_ens_ham_bant
"""
from sqlalchemy import text

from alembic import op

revision = "v2667_golge_etiket"
down_revision = "v2650_ens_ham_bant"
branch_labels = None
depends_on = None

ESKI_ETIKETLER = ("yayin", "gun_ici", "elle", "backtest", "simulasyon", "sentetik", "demo", "yeniden_kurma")   # v2597 sözlüğü
ETIKET_GOLGE = "golge"
ETIKETLER = (*ESKI_ETIKETLER, ETIKET_GOLGE)   # karne_kurali.ETIKETLER ile birebir (test pini)
KISIT = "forecast_runs_etiket_check"


def _kisit_sql(etiketler) -> str:
    return "ALTER TABLE forecast_runs ADD CONSTRAINT {} CHECK (etiket IN ({}))".format(KISIT, ", ".join(f"'{e}'" for e in etiketler))


def golge_satir_kontrol(baglanti) -> int:
    """Downgrade bekçisi: 'golge' etiketli koşu sayısı; >0 ise eski kısıt geri kurulamaz → RuntimeError (sessiz silme/çevirme YOK)."""
    n = int(baglanti.execute(text("SELECT count(*) FROM forecast_runs WHERE etiket = :e"), {"e": ETIKET_GOLGE}).scalar() or 0)
    if n:
        raise RuntimeError(f"downgrade durdu: {n} 'golge' etiketli forecast_runs satırı var; eski sözlük bunları kabul etmez. "
                           "Satırları ayrı kararla taşıyın/silin, sonra tekrar deneyin.")
    return n


def upgrade() -> None:
    op.execute(f"ALTER TABLE forecast_runs DROP CONSTRAINT IF EXISTS {KISIT}")
    op.execute(_kisit_sql(ETIKETLER))   # mevcut satırlar eski sözlüğün alt kümesinde → doğrulama geçer, veri dokunulmaz


def downgrade() -> None:
    golge_satir_kontrol(op.get_bind())
    op.execute(f"ALTER TABLE forecast_runs DROP CONSTRAINT IF EXISTS {KISIT}")
    op.execute(_kisit_sql(ESKI_ETIKETLER))
