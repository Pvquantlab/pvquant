"""G5-P1 / F1-14 (D-9) — tahmin YAYIN SÜREKLİLİĞİ (25.11.2026).

13.11 15:44Z → 17.11 13:47Z arasında 94 saat hiçbir santrale tahmin yayımlanmadı (sunucu taşıması) ve hiçbir alarm çalmadı: işçi
ölüyken işçinin kendi alarmı da ölüdür. Çözüm «harici» izlemedir: kimliksiz `/v1/sureklilik` ucu son yayın koşusunun yaşını verir,
eşik aşıldığında 503 döner; dış bir çalışma süresi izleyicisi (healthz gibi) bunu dakikada bir sorar ve 503'te uyarır. Kiracı verisi
sızmaz: yalnız yaş (saat), eşik ve etkin santral sayıları. Hüküm saf fonksiyonda (`degerlendir`), DB okuması ayrı (`ozet`).

Kapsam: etkin kiracıların arşivlenmemiş santralleri; yalnız yayın koşuları (etiket yayin/gun_ici ya da eski NULL; geriye bakışlı
model/meteo ve deney etiketleri hariç — karne_kurali ile aynı sözlük). Yazma yok.
"""
from __future__ import annotations

import datetime as dt

from pvquant.services import karne_kurali as kk

ESIK_SAAT_VARSAYILAN = 30     # sabah 05:00 + gün içi 12:30/18:30 TSİ → en seyrek yayın aralığı ≈ 11 sa; 30 sa = bir gün + pay (gece turu/yedek eşiğiyle aynı)
DURUM_OK, DURUM_BAYAT, DURUM_YOK, DURUM_SANTRAL_YOK = "ok", "bayat", "yok", "santral_yok"


def degerlendir(son_yayin, simdi: dt.datetime, esik_saat: float = ESIK_SAAT_VARSAYILAN, etkin_santral: int | None = None,
                bayat_santral: int | None = None) -> dict:
    """SAF. son_yayin: en yeni yayın koşusunun run_at (UTC, tz'li) ya da None. Döner: durum, yas_saat, esik_saat, son_yayin, ok (bool)."""
    out = {"durum": DURUM_OK, "ok": True, "son_yayin": None, "yas_saat": None, "esik_saat": float(esik_saat),
           "etkin_santral": etkin_santral, "bayat_santral": bayat_santral,
           "aciklama": "son yayın koşusunun yaşı; eşik aşımı = tahmin yayını kesildi (F1-14)"}
    if etkin_santral == 0:
        out.update({"durum": DURUM_SANTRAL_YOK, "ok": True, "aciklama": "etkin santral yok; süreklilik hükmü yok"})
        return out
    if son_yayin is None:
        out.update({"durum": DURUM_YOK, "ok": False, "aciklama": "hiç yayın koşusu yok"})
        return out
    s = son_yayin if son_yayin.tzinfo else son_yayin.replace(tzinfo=dt.timezone.utc)
    yas = (simdi - s).total_seconds() / 3600.0
    out["son_yayin"] = s.isoformat(timespec="seconds")
    out["yas_saat"] = round(max(yas, 0.0), 1)
    if yas > esik_saat:
        out.update({"durum": DURUM_BAYAT, "ok": False})
    elif bayat_santral:
        out.update({"durum": DURUM_BAYAT, "ok": False, "aciklama": f"{bayat_santral} etkin santralde son yayın eşikten eski"})
    return out


def ozet(simdi: dt.datetime | None = None, esik_saat: float | None = None) -> dict:
    """DB (sistem bağlamı, yalnız SELECT): etkin kiracıların arşivlenmemiş santralleri için en yeni yayın koşusu ve santral başına bayatlık."""
    from sqlalchemy import text

    from pvquant.config import get_settings
    from pvquant.db import sistem_baglami
    simdi = simdi or dt.datetime.now(dt.timezone.utc)
    esik = float(esik_saat if esik_saat is not None else getattr(get_settings(), "sureklilik_esik_saat", ESIK_SAAT_VARSAYILAN))
    yayin = tuple(sorted({kk.ETIKET_YAYIN, kk.ETIKET_GUN_ICI}))
    sql = text(
        "WITH etkin AS (SELECT p.id FROM plants p JOIN tenants t ON t.id = p.tenant_id WHERE t.status = 'active' AND NOT p.archived), "
        "son AS (SELECT e.id, max(r.run_at) AS son FROM etkin e LEFT JOIN forecast_runs r ON r.plant_id = e.id "
        "  AND COALESCE(r.etiket, :yayin0) = ANY(:yayin) AND COALESCE(r.model, '') <> ALL(:gb_model) AND COALESCE(r.meteo_source, '') <> ALL(:gb_meteo) "
        "  GROUP BY e.id) "
        "SELECT count(*) AS etkin, max(son) AS son_yayin, "
        "count(*) FILTER (WHERE son IS NULL OR son < CAST(:simdi AS timestamptz) - make_interval(hours => CAST(:esik AS int))) AS bayat FROM son")
    with sistem_baglami() as s:
        r = s.execute(sql, {"yayin0": kk.ETIKET_YAYIN, "yayin": list(yayin), "gb_model": list(kk.GERIYE_BAKISLI_MODEL),
                            "gb_meteo": list(kk.GERIYE_BAKISLI_METEO), "simdi": simdi, "esik": round(esik)}).mappings().first()
    son = r["son_yayin"]
    if son is not None and son.tzinfo is None:
        son = son.replace(tzinfo=dt.timezone.utc)
    return degerlendir(son, simdi, esik, etkin_santral=int(r["etkin"] or 0), bayat_santral=int(r["bayat"] or 0))
