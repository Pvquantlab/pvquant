"""Dogruluk/Kalibrasyon sunum hesaplari. saat_profili: saat basina ortalama isaretli hata (v2.532; eski hata_matrisi kaldirildi).
Kurallar gece_skill ile ozdes (tek kural kitabi): flag='valid' eslesme,
ufuk = ts_utc - run_at, gunduz = power > %2 kapasite. Hesap hafif tutulur;
agir skorlar worker'da (tek uretici o), burada ham eslesme + pivot var."""
from __future__ import annotations
import pandas as pd
from sqlalchemy import text
from pvquant.db import tenant_baglami
from pvquant.services import santral_kunye_service as _sk   # v2.599 (F4-E)
from pvquant.services import kalite_sozlugu as _ks   # v2.598 (F4-C): flag süzgeci tek sözlükten
from pvquant.services import karne_kurali as _kk   # v2.568: karne kuralı tek yerde

_KOVALAR = {"0-24": (0, 24), "24-72": (24, 72),
            "72-168": (72, 168), "168+": (168, 999)}
_SAAT_ILK, _SAAT_SON = 5, 20          # rapor s06 ile ayni iskelet (05-20 yerel)


def saat_profili_hesapla(df: pd.DataFrame, kapasite_kwp: float, tz: str, gun: int, bugun=None) -> dict:
    """SAF (v2.532): eşleşmiş saatlik çiftlerden (ts_utc, p50_kw, power_kw) saat başına ortalama İŞARETLİ hata (p50 − gerçek, kW)
    ve ortalama mutlak hata; dünle biten N tam yerel gün, gündüz (> %2 kapasite), 05–20 yerel. Aynı saate birden çok gözlem düşerse
    önce saatlik ortalama (çoklu-koşu savunması, hata_dagilimi ile özdeş). `sistematik`: |ortalama işaretli hata| ≥ %5 kapasite ve
    n ≥ 5 olan saatler (yön: fazla | eksik). Eski saat × gün matrisi (v2.111 hata_matrisi) 04.11.2026'da kaldırıldı: müşteri için
    karar üretmiyordu; kalibrasyonun teşhis bilgisi olan saat profili Kalibrasyon sayfasına taşındı."""
    saatler = ["%02d\u2013%02d" % (h, h + 1) for h in range(_SAAT_ILK, _SAAT_SON)]
    esik = 0.05 * float(kapasite_kwp)
    bos = {"saatler": saatler, "profil": [{"saat": a, "ort_hata_kw": None, "ort_mutlak_kw": None, "n": 0} for a in saatler],
           "gun_sayisi": 0, "ilk_gun": None, "son_gun": None, "sistematik": [], "esik_kw": round(esik, 1),
           "metrik": "isaretli_hata", "birim": "kW", "tz": tz}
    if df is None or df.empty:
        return bos
    if df.ts_utc.dt.tz is None:
        yerel = df.ts_utc.dt.tz_localize("UTC").dt.tz_convert(tz)
    else:
        yerel = df.ts_utc.dt.tz_convert(tz)
    df = df.assign(y_gun=yerel.dt.date, y_saat=yerel.dt.hour)
    dun = ((bugun if bugun is not None else pd.Timestamp.now(tz=tz)) - pd.Timedelta(days=1)).date()
    ilk = dun - pd.Timedelta(days=gun - 1)
    df = df[(df.y_gun >= ilk) & (df.y_gun <= dun)]
    df = df[(df.y_saat >= _SAAT_ILK) & (df.y_saat < _SAAT_SON)]
    df = df[_kk.gunduz_maskesi(df.power_kw, float(kapasite_kwp))]   # v2.568: tek eşik
    if df.empty:
        return bos
    df = (df.groupby(["y_gun", "y_saat"], as_index=False).agg(p50_kw=("p50_kw", "mean"), power_kw=("power_kw", "mean")))
    df = df.assign(hata=df.p50_kw - df.power_kw, mutlak=(df.p50_kw - df.power_kw).abs())
    g = df.groupby("y_saat").agg(ort=("hata", "mean"), mut=("mutlak", "mean"), n=("hata", "size"))
    profil = []; sistematik = []
    for h, ad in zip(range(_SAAT_ILK, _SAAT_SON), saatler):
        if h in g.index:
            ort, mut, n = float(g.loc[h, "ort"]), float(g.loc[h, "mut"]), int(g.loc[h, "n"])
            profil.append({"saat": ad, "ort_hata_kw": round(ort, 1), "ort_mutlak_kw": round(mut, 1), "n": n})
            if n >= 5 and abs(ort) >= esik:
                sistematik.append({"saat": ad, "yon": "fazla" if ort > 0 else "eksik", "ort_hata_kw": round(ort, 1), "n": n})
        else:
            profil.append({"saat": ad, "ort_hata_kw": None, "ort_mutlak_kw": None, "n": 0})
    gunler = sorted(df.y_gun.unique())
    return {"saatler": saatler, "profil": profil, "gun_sayisi": len(gunler), "ilk_gun": gunler[0].isoformat(), "son_gun": gunler[-1].isoformat(),
            "sistematik": sistematik, "esik_kw": round(esik, 1), "metrik": "isaretli_hata", "birim": "kW", "tz": tz}


def saat_profili(tenant_id, plant_id, gun: int = 30, kova: str = "0-24"):
    """Saat başına ortalama işaretli hata (Kalibrasyon sayfası). Kurallar hata_dagilimi ile özdeş: flag='valid' eşleşme, ufuk kovası,
    gündüz > %2 kapasite, dünle biten N tam yerel gün."""
    if kova not in _KOVALAR:
        raise ValueError("bilinmeyen kova: %s" % kova)
    lo, hi = _KOVALAR[kova]
    with tenant_baglami(tenant_id) as s:
        p = s.execute(text(
            "SELECT tz, capacity_kwp FROM plants WHERE id=:p"),
            {"p": plant_id}).mappings().first()
        if p is None:
            raise LookupError("santral yok: %s" % plant_id)
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.p50_kw, r.run_at, s.power_kw, "
            " r.model, r.meteo_source, COALESCE(r.etiket, r.meteo_ozet_json->>'etiket') AS etiket "
            "FROM forecast_values f "
            "JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc"
            f" AND {_ks.sql_kosulu('karne', 's')} "
            "WHERE f.plant_id=:p "
            "AND f.ts_utc >= now() - ((:g + 2) * INTERVAL '1 day')"),
            s.connection(), params={"p": plant_id, "g": gun},
            parse_dates=["ts_utc", "run_at"])
    df = _kk.ana_kovalar(_kk.karne_secimi(df)) if not df.empty else df   # v2.568: karneyle aynı seçim (geriye bakışlı ve gün içi dışarıda, saat başına en erken koşu)
    tz = p["tz"] or "UTC"
    if not df.empty:
        ufuk = (df.ts_utc - df.run_at).dt.total_seconds() / 3600
        df = df[(ufuk > lo) & (ufuk <= hi)]
    return saat_profili_hesapla(df, float(p["capacity_kwp"]), tz, gun)


_KUTU_125 = (1.0, 2.0, 5.0)


def _yuvarla_125(w: float) -> float:
    """1-2-5 dizisine (… 0,01 0,02 0,05 0,1 0,2 0,5 1 2 5 …) log uzayında en yakın değer."""
    import math
    if w <= 0:
        return 0.01
    e = math.floor(math.log10(w))
    adaylar = [m * 10 ** k for k in (e - 1, e, e + 1) for m in _KUTU_125]
    return float(min(adaylar, key=lambda a: abs(math.log10(a / w))))


def kutu_genisligi(sapma, kapasite_kwp: float | None, *, en_az: int = 6, en_cok: int = 20) -> dict:
    """G4-C2 (UAT 21.11 G4-7) — SAF: günlük sapma dizisinden (MWh/gün) kutu genişliği. Freedman–Diaconis (2·IQR·n^-1/3); IQR 0 ise Scott
    (3,49·sd·n^-1/3); sd 0 / az örnek (n<4) ise santral tabanı. Taban = kapasiteye ölçekli (kWp/1000 · 0,01 MWh, en az 0,01): küçük santralde
    0,01, 4,8 MWp'de 0,05 — iki santral aynı sabitle (0,5) tek çubuğa sıkışmaz. Kutu sayısı [en_az, en_cok] bandına kıskaçlanır, sonuç 1-2-5
    dizisine yuvarlanır (eksen okunur). Uç değer kutu sayısını değil genişliği büyütür (veri atılmaz). Döner: {kutu_mwh, kaynak, n}."""
    import numpy as np
    v = np.asarray([float(x) for x in sapma], dtype=float)
    v = v[np.isfinite(v)]
    n = int(len(v))
    taban = _yuvarla_125(max(0.01, (float(kapasite_kwp or 0.0) / 1000.0) * 0.01))
    if n == 0:
        return {"kutu_mwh": taban, "kaynak": "taban", "n": 0}
    aralik = float(v.max() - v.min())
    if n < 4 or aralik == 0.0:
        return {"kutu_mwh": taban, "kaynak": "taban", "n": n}
    q75, q25 = (float(np.percentile(v, q)) for q in (75, 25))
    iqr = q75 - q25
    sd = float(v.std(ddof=1))
    if iqr > 0:
        w, kaynak = 2.0 * iqr * n ** (-1.0 / 3.0), "fd"
    elif sd > 0:
        w, kaynak = 3.49 * sd * n ** (-1.0 / 3.0), "scott"
    else:
        return {"kutu_mwh": taban, "kaynak": "taban", "n": n}
    import math
    w = max(w, aralik / en_cok, taban)       # çok kutu → genişlet (uç değer), taban altına inme
    if aralik / w < en_az:
        w = max(aralik / en_az, taban)       # az kutu → daralt (taban altına inmeden)
    w = _yuvarla_125(w)

    def _n_kutu(wk: float) -> int:           # QA Ö-1: gerçek kutu sayısı (kenar hizalaması dahil) ile ölç
        alt = math.floor(float(v.min()) / wk + 1e-9) * wk
        return max(1, int(math.ceil((float(v.max()) - alt) / wk - 1e-9)))
    if _n_kutu(w) > en_cok + 4:              # 1-2-5 yuvarlaması bandı aşırı aşarsa bir basamak büyüt
        w = _yuvarla_125(w * 2.0)
    if w <= taban + 1e-12:                   # QA Ö-2: taban bağlayıcıysa kaynak «taban» (şeffaflık)
        kaynak = "taban"
    return {"kutu_mwh": float(w), "kaynak": kaynak, "n": n}


def hata_dagilimi(tenant_id, plant_id, gun: int = 120, kova: str = "0-24",
                  kutu_mwh: float | None = None):
    """Gunluk sapma dagilimi (F - A, MWh/gun) — rapor s08 tanimiyla ozdes.
    Saatlik ciftler (gece_skill kurallari) yerel gune toplanir; gunde >= 3
    eslesmis gunduz saati yoksa gun dagilima girmez. Kutu genisligi: None →
    veriden (`kutu_genisligi`, G4-C2); sayi verilirse eski sabit davranis
    (geri uyumluluk). Sinirlar veriden. Yuzdelikler ham gunluk sapmalardan
    (interpolasyonsuz numpy percentile, linear)."""
    if kova not in _KOVALAR:
        raise ValueError("bilinmeyen kova: %s" % kova)
    lo, hi = _KOVALAR[kova]
    with tenant_baglami(tenant_id) as s:
        p = s.execute(text(
            "SELECT tz, capacity_kwp FROM plants WHERE id=:p"),
            {"p": plant_id}).mappings().first()
        if p is None:
            raise LookupError("santral yok: %s" % plant_id)
        df = pd.read_sql(text(
            "SELECT f.ts_utc, f.p50_kw, r.run_at, s.power_kw, "
            " r.model, r.meteo_source, COALESCE(r.etiket, r.meteo_ozet_json->>'etiket') AS etiket "
            "FROM forecast_values f "
            "JOIN forecast_runs r ON r.id=f.run_id "
            "JOIN scada_hourly s ON s.plant_id=f.plant_id AND s.ts_utc=f.ts_utc"
            f" AND {_ks.sql_kosulu('karne', 's')} "
            "WHERE f.plant_id=:p "
            "AND f.ts_utc >= now() - ((:g + 2) * INTERVAL '1 day')"),
            s.connection(), params={"p": plant_id, "g": gun},
            parse_dates=["ts_utc", "run_at"])
    df = _kk.ana_kovalar(_kk.karne_secimi(df)) if not df.empty else df   # v2.568: karneyle aynı seçim (geriye bakışlı ve gün içi dışarıda, saat başına en erken koşu)
    tz = p["tz"] or "UTC"
    bos = {"kutular": [], "mu": None, "sd": None, "ndays": 0,
           "p10": None, "p50": None, "p90": None,
           "birim": "MWh/gun", "kova": kova, "tz": tz,
           "kutu_mwh": None, "kutu_kaynak": None}   # G4-C2
    if df.empty:
        return bos
    ufuk = (df.ts_utc - df.run_at).dt.total_seconds() / 3600
    df = df[(ufuk > lo) & (ufuk <= hi)]
    if df.empty:
        return bos
    if df.ts_utc.dt.tz is None:
        yerel = df.ts_utc.dt.tz_localize("UTC").dt.tz_convert(tz)
    else:
        yerel = df.ts_utc.dt.tz_convert(tz)
    df = df.assign(y_gun=yerel.dt.date)
    dun = (pd.Timestamp.now(tz=tz) - pd.Timedelta(days=1)).date()
    ilk = dun - pd.Timedelta(days=gun - 1)
    df = df[(df.y_gun >= ilk) & (df.y_gun <= dun)]
    df = df[_kk.gunduz_maskesi(df.power_kw, _sk.guc_tanimlari(p)["dc_kwp"])]      # gunduz (v2.568: tek eşik; v2.599: payda tek kaynak)
    if df.empty:
        return bos
    # coklu-kosu savunmasi: ayni saate birden cok gozlem duserse ortala
    # (saat profilinin mean'iyle ozdes — iki panel ayni sayiyi soyler)
    df = (df.groupby(["y_gun", "ts_utc"], as_index=False)
            .agg(p50_kw=("p50_kw", "mean"), power_kw=("power_kw", "mean")))
    g = df.groupby("y_gun").agg(n=("power_kw", "size"),
                                f=("p50_kw", "sum"), a=("power_kw", "sum"))
    g = g[g.n >= 3]                                              # gecerli gun
    if g.empty:
        return bos
    sapma = ((g.f - g.a) / 1000.0).astype(float)                 # kWh -> MWh
    return kutu_dagilimi(sapma, kutu_mwh, float(p["capacity_kwp"] or 0.0), kova=kova, tz=tz)


def kutu_dagilimi(sapma, kutu_mwh: float | None, kapasite_kwp: float | None, *, kova: str = "0-24", tz: str = "UTC") -> dict:
    """G4-C2 — SAF kuyruk (DB'siz test): kutular + istatistikler. kutu_mwh None → `kutu_genisligi`; verilirse sabit (eski davranış)."""
    import numpy as np
    import pandas as pd
    sapma = pd.Series([float(x) for x in sapma], dtype=float)
    sapma = sapma[np.isfinite(sapma)].reset_index(drop=True)   # QA Ö-3: NaN/inf sayılmaz, hata da vermez (kutu_genisligi ile aynı süzgeç)
    if sapma.empty:
        return {"kutular": [], "mu": None, "sd": None, "ndays": 0, "p10": None, "p50": None, "p90": None, "birim": "MWh/gun", "kova": kova, "tz": tz,
                "kutu_mwh": None, "kutu_kaynak": None}
    if kutu_mwh is None:
        kg = kutu_genisligi(sapma, kapasite_kwp)
        kutu_mwh, kutu_kaynak = kg["kutu_mwh"], kg["kaynak"]
    else:
        kutu_kaynak = "sabit"
    import numpy as np
    mu, sd = float(sapma.mean()), float(sapma.std(ddof=1)) if len(sapma) > 1 else 0.0
    p10, p50, p90 = (float(np.percentile(sapma, q)) for q in (10, 50, 90))
    import math
    # G4-C2: tam sayı kutu dizini ile sayım — eski kayan noktalı sınır döngüsü kutu kenarındaki en büyük değeri ve 0,7/0,01 gibi
    # tam bölünen değerleri düşürüyordu (ör. [0,1 0,2 0,3] → 2 sayım; 20×0,7 → 0 sayım). Son kutu sağdan kapalı; toplam sayım = n.
    v = sapma.to_numpy(dtype=float)
    alt = math.floor(float(v.min()) / kutu_mwh + 1e-9) * kutu_mwh
    n_kutu = max(1, int(math.ceil((float(v.max()) - alt) / kutu_mwh - 1e-9)))
    idx = np.clip(np.floor((v - alt) / kutu_mwh + 1e-9).astype(int), 0, n_kutu - 1)
    sayim = np.bincount(idx, minlength=n_kutu)
    kutular = [{"lo": round(alt + k * kutu_mwh, 3), "hi": round(alt + (k + 1) * kutu_mwh, 3), "adet": int(sayim[k])} for k in range(n_kutu)]   # 0,01 MWh kutu için 3 hane
    hane = 2 if kutu_mwh >= 0.1 else 3
    return {"kutular": kutular, "mu": round(mu, hane), "sd": round(sd, hane),
            "ndays": int(len(sapma)), "p10": round(p10, hane),
            "p50": round(p50, hane), "p90": round(p90, hane),
            "birim": "MWh/gun", "kova": kova, "tz": tz,
            "kutu_mwh": float(kutu_mwh), "kutu_kaynak": kutu_kaynak}   # G4-C2: şeffaflık (veri | sabit)
