"""G5-P3 (26.11.2026) — koşu YENİDEN KURULABİLİRLİK denetimi (Faz 1 G5 «yeniden_kurma»; salt okunur, yazma yolu yok).

Soru: arşivdeki bir yayın koşusu (run_id) bugün elimizdeki künye ve arşiv girdileriyle AYNI değere yeniden üretilebilir mi?
Bu modül yeniden üretmeyi YAPMAZ; yalnız ön koşulları sayar ve dürüstçe sınıflar:
  * kurulabilir — Mod A, spec_json + NWP koşu zamanı var, harmanlanmış meteo arşivi (meteo_arsiv) ufku kapsıyor, katman parametreleri
    künyede (ufuk σ / sapma oranı), bant model ya da GEFS üyeleri (meteo_uye) hâlâ arşivde.
  * kısmi — P50 kurulabilir ama bant/katman için girdi eksik (üye arşivi saklama süresi dışında, katman JSON'u boş) ya da Mod B/C
    (kalibrasyon parametresi / ML artefaktı ayrıca gerekir; bu denetim onları saymaz).
  * kurulamaz — spec_json ya da NWP koşu zamanı yok, ya da arşiv meteo ufkun %90'ından azını kapsıyor.
Hüküm saf fonksiyonda (`degerlendir`), DB okuması ayrı (`kunye_ve_arsiv_oku`). Sayı uydurulmaz: her eksik adıyla listelenir.
"""
from __future__ import annotations

import datetime as dt

METEO_ASGARI_KAPSAMA = 0.90
DURUM_KURULABILIR, DURUM_KISMI, DURUM_KURULAMAZ = "kurulabilir", "kismi", "kurulamaz"


def degerlendir(kunye: dict, arsiv: dict) -> dict:
    """SAF. kunye: forecast_runs satırı (+ ufuk_saat, bant_json, mode…); arsiv: {meteo_satir, beklenen_saat, uye_satir, uye_sayisi}.
    Döner: {run_id, durum, eksik[], notlar[], kapsama}."""
    eksik, notlar = [], []
    run_id = str(kunye.get("id") or kunye.get("run_id") or "")
    if not kunye.get("spec_json"):
        eksik.append("spec_json yok (santral özelliği künyede değil)")
    if kunye.get("nwp_kosu_zamani") is None:
        eksik.append("nwp_kosu_zamani yok (hangi NWP koşusu kullanıldı bilinmiyor)")
    beklenen = int(arsiv.get("beklenen_saat") or 0)
    satir = int(arsiv.get("meteo_satir") or 0)
    kapsama = (satir / beklenen) if beklenen > 0 else 0.0
    if kunye.get("nwp_kosu_zamani") is not None and kapsama < METEO_ASGARI_KAPSAMA:
        eksik.append(f"arşiv meteo ufku kapsamıyor ({satir}/{beklenen} saat, %{kapsama * 100:.0f})")
    kismi = []
    mode = str(kunye.get("mode") or "A")
    if mode != "A":
        kismi.append(f"mod {mode}: kalibrasyon parametresi/ML artefaktı bu denetimin dışında")
    bant = kunye.get("bant_json") or {}
    if isinstance(bant, dict) and bant.get("kaynak") == "gefs":
        if kunye.get("ensemble_kosu_zamani") is None:
            kismi.append("GEFS bandı var ama ensemble_kosu_zamani künyede yok")
        elif int(arsiv.get("uye_satir") or 0) == 0:
            kismi.append("GEFS üye arşivi (meteo_uye) bu koşu için yok — saklama süresi dışında; bant yeniden kurulamaz")
        elif int(arsiv.get("uye_sayisi") or 0) < int(bant.get("uye") or 0):
            kismi.append(f"üye arşivi eksik ({arsiv.get('uye_sayisi')}/{bant.get('uye')} üye)")
    for alan, ad in (("ufuk_sigma_json", "ufuk σ"), ("sapma_oran_json", "sapma oranı")):
        if kunye.get(alan) in (None, "", {}):
            kismi.append(f"{ad} künyede yok — varsayılanla kurulur, birebir değil")
    if not kunye.get("yazilim_surumu"):
        notlar.append("yazilim_surumu boş: hangi kod sürümüyle üretildiği bilinmiyor (11.11 öncesi koşular)")
    if kunye.get("mode") == "C" and not kunye.get("artefakt_sha16"):
        notlar.append("mod C artefakt sha yok")
    durum = DURUM_KURULAMAZ if eksik else (DURUM_KISMI if kismi else DURUM_KURULABILIR)
    return {"run_id": run_id, "durum": durum, "eksik": eksik, "kismi": kismi, "notlar": notlar,
            "kapsama": round(kapsama, 3), "mode": mode, "bant_kaynak": bant.get("kaynak") if isinstance(bant, dict) else None}


def kunye_ve_arsiv_oku(tenant_id, run_id) -> tuple[dict, dict] | None:
    """DB (yalnız SELECT): koşu künyesi (kiracı bağlamı) + meteo_arsiv / meteo_uye sayımları (sistem bağlamı)."""
    from sqlalchemy import text

    from pvquant.db import sistem_baglami, tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text(
            "SELECT r.id, r.run_at, r.mode, r.model, r.etiket, r.meteo_source, r.nwp_kosu_zamani, r.ensemble_kosu_zamani, r.yazilim_surumu, "
            "r.ufuk_saat, r.spec_json, r.bant_json, r.ufuk_sigma_json, r.sapma_oran_json, r.artefakt_sha16, p.lat, p.lon "
            "FROM forecast_runs r JOIN plants p ON p.id = r.plant_id WHERE r.id = CAST(:r AS uuid)"), {"r": str(run_id)}).mappings().first()
    if r is None:
        return None
    k = dict(r)
    arsiv = {"meteo_satir": 0, "beklenen_saat": int(k.get("ufuk_saat") or 0), "uye_satir": 0, "uye_sayisi": 0}
    if k.get("nwp_kosu_zamani") is not None:
        from pvquant.io.acik_nwp import _nokta_anahtar
        la, lo = _nokta_anahtar(float(k["lat"]), float(k["lon"]))
        ra = k["run_at"]
        bas = (ra if ra.tzinfo else ra.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
        bit = bas + dt.timedelta(hours=arsiv["beklenen_saat"])
        with sistem_baglami() as s:
            arsiv["meteo_satir"] = int(s.execute(text(
                "SELECT count(*) FROM meteo_arsiv WHERE kaynak=:k AND lat=:la AND lon=:lo AND kosu_zamani=:z AND ts_utc >= :a AND ts_utc < :b"),
                {"k": k.get("meteo_source"), "la": la, "lo": lo, "z": k["nwp_kosu_zamani"], "a": bas, "b": bit}).scalar() or 0)
            if k.get("ensemble_kosu_zamani") is not None:
                u = s.execute(text("SELECT count(*) AS n, count(DISTINCT uye) AS uye FROM meteo_uye WHERE lat=:la AND lon=:lo AND kosu_zamani=:z"),
                              {"la": la, "lo": lo, "z": k["ensemble_kosu_zamani"]}).mappings().first()
                arsiv["uye_satir"], arsiv["uye_sayisi"] = int(u["n"] or 0), int(u["uye"] or 0)
    return k, arsiv


def kurulabilirlik(tenant_id, run_id) -> dict | None:
    out = kunye_ve_arsiv_oku(tenant_id, run_id)
    return None if out is None else degerlendir(*out)
