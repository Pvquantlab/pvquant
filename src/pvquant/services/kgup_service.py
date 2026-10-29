"""v2.260 — Dalga 4.13: KGÜP bildirim dosyası (saatlik program) — teslim edilebilir koşudan. 29.10.2026 (F-05/F-06):
eksik saatte 0 yazılmaz (422 + saat listesi), EAK MW, 15 dk yalnız dengeleme birimi, P25/P75, şablon eşlemesi, SHA-256 + kaynak künyesi.

Program günü D için kaynak koşu: D-1 15:30 (İstanbul) öncesinde verilmiş son koşu (dengesizlik simülatörüyle aynı
kural); bugün için henüz 15:30 geçmediyse en son koşu. Kantil: p50 (varsayılan) | p10 | p25 | p75 | p90.
Dosya: pvquant.ext.turkiye.kgup (KGÜP ≤ EAK ≤ kurulu güç; 15 dk dilimleme yalnız params_json.dengeleme_birimi=true ve ≥200 MWh
sıçramada; TPYS CSV — kolonlar params_json.kgup_sablon ile eşlenir; resmî şablon teyit edilemedi). Koşu yoksa 409; eksik saat → 422.
Sürüm arşivi (F-06, kgup_surum tablosu) bu sürümde YOK — göç taslağı alembic/taslak/; yanıt SHA-256 ve kaynak künyesini zaten taşır.
"""
from __future__ import annotations

import hashlib
import io
from datetime import date

import pandas as pd

from pvquant.ext.turkiye import kgup as kg

IST = "Europe/Istanbul"


def kaynak_kosu_df(tenant_id, plant_id, gun: date, kantil: str = "p50", tum_kantiller: bool = False) -> tuple[pd.DataFrame, dict | None]:
    """DB: D-1 15:30 IST öncesi son koşunun D günü saatleri (UTC). Döner (df[ts_utc, kw], koşu bilgisi)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    kol = {"p50": "p50_kw", "p10": "p10_kw", "p25": "p25_kw", "p75": "p75_kw", "p90": "p90_kw"}[kantil]
    d0 = pd.Timestamp(gun, tz=IST); d1 = d0 + pd.Timedelta(days=1)
    kesim = d0 - pd.Timedelta(hours=8, minutes=30)   # D-1 15:30 IST
    simdi = pd.Timestamp.now(tz=IST)
    if kesim > simdi:
        kesim = simdi
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT id, run_at, mode FROM forecast_runs WHERE plant_id=:p AND run_at <= :k "
                           "AND EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id=forecast_runs.id AND v.ts_utc >= :a AND v.ts_utc < :b) "
                           "ORDER BY run_at DESC LIMIT 1"),
                      {"p": plant_id, "k": kesim.to_pydatetime(), "a": d0.tz_convert("UTC").to_pydatetime(), "b": d1.tz_convert("UTC").to_pydatetime()}).first()
        if r is None:
            return pd.DataFrame(columns=["ts_utc", "kw"]), None
        secim = "ts_utc, p50_kw, p10_kw, p25_kw, p75_kw, p90_kw" if tum_kantiller else f"ts_utc, {kol} AS kw"   # v2.275: toplayıcı çıktısı bandı da ister
        df = pd.read_sql(text(f"SELECT {secim} FROM forecast_values WHERE run_id=:r AND plant_id=:p AND ts_utc >= :a AND ts_utc < :b ORDER BY ts_utc"),
                         s.connection(), params={"r": r.id, "p": plant_id, "a": d0.tz_convert("UTC").to_pydatetime(), "b": d1.tz_convert("UTC").to_pydatetime()}, parse_dates=["ts_utc"])
    df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    return df, {"run_id": str(r.id), "run_at": r.run_at.isoformat(), "mode": r.mode, "kesim": kesim.isoformat()}


def eak_etkin(plant: dict, gun: date) -> dict:
    """v2.275 — EAK (emre amade kapasite, MW) o gün için: geçici kısıt (bakım/arıza, bitiş tarihine kadar) > kalıcı EAK alanı
    > AC tavanı > kurulu güç. Kaynak açıkça söylenir."""
    import json as _j
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        pj = _j.loads(pj)
    kap = float(plant["capacity_kwp"]) / 1000.0
    ac = (float(plant["ac_limit_kw"]) / 1000.0) if plant.get("ac_limit_kw") else None
    g = pj.get("eak_gecici") or {}
    try:
        if g.get("kw") and g.get("bitis") and date.fromisoformat(str(g["bitis"])) >= gun and float(g["kw"]) > 0:
            return {"eak_mw": round(min(float(g["kw"]) / 1000.0, ac or kap), 3), "kaynak": "gecici", "bitis": str(g["bitis"])}
    except (TypeError, ValueError):
        pass
    if pj.get("eak_kw"):
        return {"eak_mw": round(min(float(pj["eak_kw"]) / 1000.0, kap), 3), "kaynak": "eak_alani"}
    if ac:
        return {"eak_mw": round(ac, 3), "kaynak": "ac_tavani"}
    return {"eak_mw": round(kap, 3), "kaynak": "kurulu_guc"}


KANTILLER = ("p10", "p25", "p50", "p75", "p90")


def _pj(pj) -> dict:
    import json as _j
    return _j.loads(pj) if isinstance(pj, str) else (pj or {})


def sablon_ozeti(pj, sab=None) -> dict:
    """29.10 (v2.506): dışa aktarma şablonunun durumu — müşteri dosyasından öğrenildiyse kaynağı söyler, yoksa «karşılaştırılmadı» notu."""
    from pvquant.ext.turkiye import kgup as kg
    pj = _pj(pj) if not isinstance(pj, dict) else pj
    sab = sab or kg.Sablon.params_json_dan(pj)
    kaynak = pj.get("kgup_sablon_kaynak") or None
    durum = (f"müşteri dosyasından öğrenildi: {kaynak.get('dosya', '?')} ({str(kaynak.get('zaman', ''))[:10]})" if kaynak else kg.SABLON_DURUMU)
    return {"durum": durum, "kolonlar": [getattr(sab, r) for r in sab.roller()], "ayrac": sab.ayrac, "ondalik": sab.ondalik, "kaynak": kaynak}


def uret(tenant_id, plant: dict, gun: date, kantil: str = "p50", uevcb: str | None = None) -> dict:
    """Program tablosu + doğrulama + TPYS CSV metni. Koşu yoksa {'hata': ..., 'kod': 409}; eksik saat varsa {'hata', 'kod': 422, 'eksik_saatler'}."""
    import json as _j
    df, kosu = kaynak_kosu_df(tenant_id, plant["id"], gun, kantil)
    if kosu is None:
        return {"hata": "bu gün için teslim penceresi öncesinde verilmiş koşu yok", "gun": gun.isoformat(), "kod": 409}
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        pj = _j.loads(pj)
    seri = pd.Series(df["kw"].values, index=pd.DatetimeIndex(df["ts_utc"])) / 1000.0   # kW → MW
    kap = float(plant["capacity_kwp"]) / 1000.0
    eak_bilgi = eak_etkin(plant, gun); eak = eak_bilgi["eak_mw"]   # v2.275: EAK alanı / geçici kısıt
    son = kg.program_uret(seri, gun.isoformat(), uevcb or plant.get("uevcb") or str(plant["id"])[:8].upper(), kap, eak_mw=eak, kantil=None)
    if son.eksik_saatler:
        return {"hata": f"tahmini olmayan saat var (saat {', '.join(map(str, son.eksik_saatler))}); KGÜP 0 yazılmaz, dosya üretilmedi",
                "gun": gun.isoformat(), "kod": 422, "eksik_saatler": son.eksik_saatler, "kosu": kosu}
    hatalar = kg.dogrula(son, kap)
    dengeleme_birimi = bool(pj.get("dengeleme_birimi"))
    tablo = kg.ceyrek_dilimle(son) if (son.sicrama_saatleri and dengeleme_birimi) else son.tablo
    sab = kg.Sablon.params_json_dan(pj)
    baytlar = kg.csv_baytlari(tablo, sab)
    uyarilar = son.uyarilar + hatalar + [kg.SABLON_DURUMU]
    if son.sicrama_saatleri and not dengeleme_birimi:
        uyarilar.append(f"≥200 MWh saatlik değişim var (saat {', '.join(map(str, son.sicrama_saatleri))}); santral dengeleme birimi değil, 15 dk satırı üretilmedi (DUY m.69(3))")
    # v2.287: gün içi revizyon kapısı (md. 69(1)) — öğlen örneğiyle; öneri kantili dengesizlik servisinden
    ogle = kg.gun_ici_revizyon_penceresi(pd.Timestamp(gun).tz_localize("Europe/Istanbul") + pd.Timedelta(hours=12))
    gip = {"kural": "Her teslimat saatinin gün içi piyasa kapısı 1 saat önce kapanır; KGÜP revizyonu kapanış + 30 dakikaya kadar.",
           "ornek_teslimat": "12:00", "ornek_kapi": str(ogle["gip_kapi_kapanis"].time())[:5], "ornek_revizyon_son": str(ogle["kgup_revizyon_son"].time())[:5]}
    oneri = None
    try:
        from pvquant.services import dengesizlik_service, piyasa_service
        idx = pd.date_range(pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=30), periods=30 * 24, freq="h")
        oneri = dengesizlik_service.oneri_kantili(piyasa_service.fiyatlar(idx), dengesizlik_service.katsayilar(plant.get("params_json")))
    except Exception:   # noqa: BLE001 — öneri süsleme; KGÜP üretimi düşmez
        oneri = None
    return {"gun": gun.isoformat(), "kantil": kantil, "kosu": kosu, "uyarilar": uyarilar, "sicrama_saatleri": son.sicrama_saatleri,
            "dengeleme_birimi": dengeleme_birimi, "gip": gip, "oneri": oneri,
            "toplam_mwh": round(float(son.tablo["kgup_mwh"].sum()), 3), "eak": eak_bilgi,   # v2.275
            "satirlar": [{"saat": int(r.saat), "kgup_mwh": float(r.kgup_mwh), "eak_mw": float(r.eak_mw), "eak_mwh": float(r.eak_mw)}   # eak_mwh: eski alan adı (aynı değer, MW); yeni istemciler eak_mw okur
                         for r in son.tablo.itertuples()],
            "csv": baytlar.decode("utf-8-sig"), "dosya_adi": f"KGUP_{(uevcb or 'UEVCB')}_{gun.isoformat()}_{kantil}.csv",
            "sha256": hashlib.sha256(baytlar).hexdigest(), "sablon": sablon_ozeti(plant.get("params_json"), sab),
            "takvim": kg.TAKVIM, "teslim": kg.teslim_durumu(),
            "bildirim": "Dosya PVQuant'ta üretildi; TPYS'ye gönderim ve kabul müşterinin sisteminden yapılır — indirilen dosya teslim edilmiş sayılmaz."}
