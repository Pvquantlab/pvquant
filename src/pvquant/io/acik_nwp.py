"""v2.268 — Dalga 0: açık kaynak NWP yolu (ECMWF Open Data IFS + DWD ICON-EU), koşu arşivi.

Ücretsiz Open-Meteo katmanı ticari üründe uyumluluk borcuydu; profesyonel abonelik reddedildi (6 Eyl 2026).
Bu modül aynı MeteoData sözleşmesini iki CC BY 4.0 kaynaktan üretir:
  • ECMWF IFS (0.25°, 15 gün; 0–144 s 3 saatlik, sonra 6 saatlik) — ssrd/2t/10u/10v/tcc/tp
  • ICON-EU (0.0625°, +120 s saatlik; Türkiye alan içinde) — aswdir_s/aswdifd_s/t_2m/u_10m/v_10m/clct
Harman: örtüşen saatlerde gök açıklığı endeksi (kt) uzayında eşit ağırlık (pvquant.ext.kaynak.harman);
ICON'un bitiminden sonra yalnız ECMWF. Yağış ECMWF'den (tp). Kar yağışı açık veride yok → None (kar modeli
'—'). GRIB'ler ham hâlde tutulmaz (koşu başına yüz MB'lar): nokta serileri `meteo_arsiv` tablosuna yazılır,
GRIB'ler son `nwp_kosu_tut` koşu dışında silinir. Arşiv aynı zamanda eğitim/servis kayma denetiminin ve
kalibrasyonun (v2.269) 'servis meteosu' kaynağıdır — eğitim ve servis aynı NWP'den beslenir.
Bağımlılık: ecmwf-opendata, xarray, cfgrib, eccodes (pip; eccodes wheel'i kütüphaneyi bindirir).
Çekirdek modele DOKUNMAZ; yalnız meteoroloji girdisi üretir (KIRMIZI ÇİZGİ).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from pvquant.config import get_settings

KAYNAK = "acik-nwp"                      # forecast_runs.meteo_source metni
KAYNAK_ETIKET = "ECMWF IFS + ICON-EU"   # nwp_model alanı (künye/atıf bu ikisini sayar)
ECMWF_PARAM = ["ssrd", "2t", "10u", "10v", "tcc", "tp"]
ECMWF_ADIMLAR = list(range(0, 145, 3)) + list(range(150, 361, 6))
KOLONLAR = ["ghi", "dni", "dhi", "temp_air", "wind_speed_10m", "cloud_cover", "precipitation"]


def _nokta_anahtar(lat: float, lon: float) -> tuple[float, float]:
    return round(float(lat), 3), round(float(lon), 3)


def _dizin() -> Path:
    d = Path(get_settings().nwp_dizin); d.mkdir(parents=True, exist_ok=True); return d


# ----------------------------------------------------------------------------- ECMWF ---------------------------
def ecmwf_indir(dizin: Path | None = None, kosu: pd.Timestamp | None = None) -> tuple[Path, pd.Timestamp]:
    """Son (ya da verilen) IFS koşusunun ihtiyaç duyulan alanlarını indirir; dosya varsa yeniden indirmez."""
    from ecmwf.opendata import Client
    dizin = dizin or _dizin()
    c = Client(source="ecmwf", model="ifs")
    istek = dict(param=ECMWF_PARAM, step=ECMWF_ADIMLAR, type="fc", stream="oper")
    if kosu is None:
        kosu = pd.Timestamp(c.latest(**istek))
    kosu = kosu.tz_localize("UTC") if kosu.tz is None else kosu.tz_convert("UTC")
    dosya = dizin / f"ecmwf_ifs_{kosu.strftime('%Y%m%d%H')}.grib2"
    gecici = dosya.with_suffix(".part")
    _baskasi_indiriyorsa_bekle(dosya, gecici)
    if not dosya.exists():
        c.retrieve(target=str(gecici), date=kosu.strftime("%Y%m%d"), time=int(kosu.hour), **istek)
        gecici.rename(dosya)
    return dosya, kosu


def _baskasi_indiriyorsa_bekle(dosya: Path, gecici: Path, taze_sn: float = 900.0, azami_sn: float = 3600.0) -> None:
    """Başka bir süreç (worker gece_meteo ↔ API tetiklemesi) aynı koşuyu indiriyorsa (.part son 15 dk'da büyüdüyse)
    bitmesini bekler; ECMWF 503 'Slow Down' yüzünden indirme uzun sürebilir. Bayat .part ise silinip yeniden başlanır."""
    import time
    bas = time.time()
    while gecici.exists() and not dosya.exists() and time.time() - bas < azami_sn:
        if time.time() - gecici.stat().st_mtime > taze_sn:
            gecici.unlink(missing_ok=True); return
        time.sleep(15)
    if gecici.exists() and not dosya.exists():
        gecici.unlink(missing_ok=True)


def ecmwf_noktalar(dosya: Path, noktalar: list[tuple[float, float]]) -> dict[tuple[float, float], pd.DataFrame]:
    """GRIB'i BİR kez açar; her nokta için saatlik çerçeve (ghi/temp/wind/cloud/precipitation)."""
    import cfgrib
    from pvquant.ext.kaynak.ortak import biriktirilmisten_saatlik, kaba_adimi_saatlige_indir, ruzgar_hizi, saatlik_utc_index
    dss = cfgrib.open_datasets(str(dosya), backend_kwargs={"indexpath": ""})
    degisken: dict[str, object] = {}
    for ds in dss:
        for v in ds.data_vars:
            degisken[v] = ds[v]
    eksik = [v for v in ("ssrd", "t2m", "u10", "v10", "tcc") if v not in degisken]
    if eksik:
        raise ValueError(f"ECMWF GRIB eksik alan: {eksik}")
    gecerli = pd.DatetimeIndex(pd.to_datetime(degisken["ssrd"].valid_time.values)).tz_localize("UTC")
    # adım süresi saat cinsinden — pandas 2 datetime64[s] çözünürlüğünde de doğru (int64/ns varsayımı tuzak)
    adim = pd.Series(np.r_[3.0, np.asarray((gecerli[1:] - gecerli[:-1]) / pd.Timedelta(hours=1), dtype=float)], index=gecerli)
    hedef = saatlik_utc_index(gecerli[0], int((gecerli[-1] - gecerli[0]) / pd.Timedelta(hours=1)) + 1)
    out = {}
    for lat, lon in noktalar:
        def seri(ad):
            da = degisken[ad]
            lon_ds = lon % 360 if float(da.longitude.max()) > 180 else lon
            n = da.sel(latitude=lat, longitude=lon_ds, method="nearest")
            return pd.Series(np.asarray(n.values, dtype=float).ravel()[: len(gecerli)], index=gecerli)
        ssrd_W = biriktirilmisten_saatlik(seri("ssrd"), adim)
        df = pd.DataFrame(index=hedef)
        df["ghi"] = kaba_adimi_saatlige_indir(ssrd_W, lat, lon, hedef)
        df["temp_air"] = (seri("t2m") - 273.15).reindex(hedef).interpolate(limit_direction="both")
        df["wind_speed_10m"] = ruzgar_hizi(seri("u10"), seri("v10")).reindex(hedef).interpolate(limit_direction="both")
        df["cloud_cover"] = (seri("tcc") * 100.0).reindex(hedef).interpolate(limit_direction="both")
        if "tp" in degisken:
            tp = seri("tp"); fark = tp.diff(); fark.iloc[0] = tp.iloc[0]
            mm_saat = (fark * 1000.0 / adim).clip(lower=0.0)          # m/adım → mm/saat
            df["precipitation"] = mm_saat.reindex(hedef).bfill().fillna(0.0)
        out[_nokta_anahtar(lat, lon)] = df
    return out


# ----------------------------------------------------------------------------- ICON-EU -------------------------
def icon_indir(dizin: Path | None = None, kosu: pd.Timestamp | None = None) -> tuple[Path, pd.Timestamp]:
    from pvquant.ext.kaynak import nwp_icon
    dizin = dizin or _dizin()
    kosu = kosu or nwp_icon.son_kosu()
    nwp_icon.indir(dizin, kosu=kosu, timeout=120.0)
    return dizin / f"icon_eu_{kosu.strftime('%Y%m%d%H')}", kosu


def icon_noktalar(kosu_dizini: Path, noktalar: list[tuple[float, float]]) -> dict[tuple[float, float], pd.DataFrame]:
    """Her GRIB dosyasını BİR kez açıp tüm noktaları çıkarır (santral başına 558 açılış yerine 558 toplam)."""
    import xarray as xr
    from pvquant.ext.kaynak.nwp_icon import PARAMLAR, ortalamadan_aralik
    from pvquant.ext.kaynak.ortak import gunes_konumu, ruzgar_hizi
    seriler: dict[tuple, dict[str, dict]] = {_nokta_anahtar(*n): {k: {} for k in PARAMLAR} for n in noktalar}
    for kucuk, buyuk in PARAMLAR.items():
        for f in sorted(Path(kosu_dizini).glob(f"*_{buyuk}.grib2")):
            ds = xr.open_dataset(f, engine="cfgrib", backend_kwargs={"indexpath": ""})
            var = list(ds.data_vars)[0]
            gecerli = pd.Timestamp(ds.valid_time.values).tz_localize("UTC")
            for lat, lon in noktalar:
                n = ds[var].sel(latitude=lat, longitude=lon, method="nearest")
                seriler[_nokta_anahtar(lat, lon)][kucuk][gecerli] = float(n.values)
            ds.close()
    out = {}
    for (lat, lon), S0 in seriler.items():
        S = {k: pd.Series(v).sort_index() for k, v in S0.items()}
        if S["aswdir_s"].empty:
            continue
        idx = S["aswdir_s"].index
        df = pd.DataFrame(index=idx)
        dir_ = ortalamadan_aralik(S["aswdir_s"]); dif = ortalamadan_aralik(S["aswdifd_s"].reindex(idx).ffill())
        df["ghi"] = (dir_ + dif).clip(lower=0.0); df["dhi"] = dif
        z = np.radians(gunes_konumu(idx, lat, lon)["apparent_zenith"].values)
        cosz = np.clip(np.cos(z), 0.0872, None)
        df["dni"] = np.where(np.degrees(z) < 88, dir_.values / cosz, 0.0)
        df["temp_air"] = S["t_2m"].reindex(idx) - 273.15
        df["wind_speed_10m"] = ruzgar_hizi(S["u_10m"].reindex(idx), S["v_10m"].reindex(idx))
        df["cloud_cover"] = S["clct"].reindex(idx)
        df = df.resample("h").interpolate(limit=3)
        out[(lat, lon)] = df
    return out


# ----------------------------------------------------------------------------- Harman --------------------------
def harmanla(ecmwf: pd.DataFrame | None, icon: pd.DataFrame | None, lat: float, lon: float) -> pd.DataFrame:
    """Örtüşen saatlerde kt-uzayında eşit ağırlıklı harman; ICON bitince ECMWF; tek kaynak varsa o."""
    from pvquant.ext.kaynak.atif import KAYNAKLAR
    from pvquant.ext.kaynak.harman import harmanla as _h
    from pvquant.ext.kaynak.ortak import MeteoCerceve
    if ecmwf is None and icon is None:
        raise ValueError("harmanlanacak NWP yok")
    if ecmwf is None or icon is None or ecmwf.index.intersection(icon.index).empty:
        tek = ecmwf if icon is None else icon
        c = MeteoCerceve(tek[[k for k in tek.columns if k != "precipitation"]].copy(), lat, lon,
                         KAYNAKLAR["ecmwf" if tek is ecmwf else "icon"])
        df = c.df
        if ecmwf is not None and "precipitation" in ecmwf:
            df["precipitation"] = ecmwf["precipitation"].reindex(df.index)
        return df
    ce = MeteoCerceve(ecmwf[[k for k in ecmwf.columns if k != "precipitation"]].copy(), lat, lon, KAYNAKLAR["ecmwf"])
    # ICON'da eksik adım (DWD'de bazı dosyalar 404) → o saatlerde ECMWF değeri; harman NaN üretmesin
    icon = icon.copy()
    for kol in ("ghi", "temp_air", "wind_speed_10m", "cloud_cover"):
        if kol in icon and kol in ecmwf:
            icon[kol] = icon[kol].fillna(ecmwf[kol].reindex(icon.index))
    icon = icon.dropna(subset=["ghi"])
    ci = MeteoCerceve(icon, lat, lon, KAYNAKLAR["icon"])
    ortak = _h({"ecmwf": ce, "icon": ci}).df
    # ICON koşusu ECMWF'den geç başlayabilir (06z vs 00z): baştaki ve sondaki saatler yalnız ECMWF'den
    bas = ce.df.loc[ce.df.index < ortak.index.min()]
    kuyruk = ce.df.loc[ce.df.index > ortak.index.max()]
    df = pd.concat([bas, ortak, kuyruk]).sort_index()
    if "precipitation" in ecmwf:
        df["precipitation"] = ecmwf["precipitation"].reindex(df.index)
    for kol in ("temp_air", "wind_speed_10m", "cloud_cover"):      # son bekçi: zorunlu kolonlarda NaN kalmasın
        if kol in df:
            df[kol] = df[kol].fillna(ecmwf[kol].reindex(df.index) if kol in ecmwf else np.nan).interpolate(limit_direction="both")
    return df[[k for k in KOLONLAR if k in df.columns]]


# ----------------------------------------------------------------------------- Arşiv (DB) ----------------------
def satirlar_uret(df: pd.DataFrame, kaynak: str, kosu: pd.Timestamp, lat: float, lon: float) -> list[dict]:
    la, lo = _nokta_anahtar(lat, lon)
    out = []
    for ts, r in df.iterrows():
        if pd.isna(r.get("ghi")):
            continue
        out.append({"k": kaynak, "z": kosu.to_pydatetime(), "la": la, "lo": lo, "ts": ts.to_pydatetime(),
                    **{c: (None if pd.isna(r.get(c)) else float(r.get(c))) for c in KOLONLAR}})
    return out


def _arsive_yaz(satirlar: list[dict]) -> int:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    if not satirlar:
        return 0
    with sistem_baglami() as s:
        s.execute(text(
            "INSERT INTO meteo_arsiv(kaynak,kosu_zamani,lat,lon,ts_utc,ghi,dni,dhi,temp_air,wind_speed_10m,cloud_cover,precipitation) "
            "VALUES(:k,:z,:la,:lo,:ts,:ghi,:dni,:dhi,:temp_air,:wind_speed_10m,:cloud_cover,:precipitation) "
            "ON CONFLICT (kaynak,kosu_zamani,lat,lon,ts_utc) DO NOTHING"), satirlar)
    return len(satirlar)


def kosu_cek_ve_arsivle(noktalar: list[tuple[float, float]], dizin: Path | None = None,
                        ecmwf: bool = True, icon: bool = True) -> dict:
    """Gecelik iş: iki koşuyu indir, noktaları çıkar, harmanı arşive yaz, eski GRIB'leri temizle.
    Kaynaklardan biri düşerse öteki yeter; ikisi de düşerse yükseltir (koşu meteosuz kalmaz — 'başsız run' ilkesi)."""
    dizin = dizin or _dizin()
    noktalar = sorted({_nokta_anahtar(*n) for n in noktalar})
    rapor: dict = {"noktalar": len(noktalar), "ecmwf": None, "icon": None, "satir": 0, "hata": []}
    e_df = i_df = None; e_kosu = i_kosu = None
    if ecmwf:
        try:
            dosya, e_kosu = ecmwf_indir(dizin); e_df = ecmwf_noktalar(dosya, noktalar); rapor["ecmwf"] = e_kosu.isoformat()
        except Exception as ex:   # noqa: BLE001
            rapor["hata"].append(f"ecmwf: {type(ex).__name__}: {ex}")
    if icon:
        try:
            kd, i_kosu = icon_indir(dizin); i_df = icon_noktalar(kd, noktalar); rapor["icon"] = i_kosu.isoformat()
        except Exception as ex:   # noqa: BLE001
            rapor["hata"].append(f"icon: {type(ex).__name__}: {ex}")
    if e_df is None and i_df is None:
        raise RuntimeError("açık NWP: iki kaynak da alınamadı — " + "; ".join(rapor["hata"]))
    kosu = max(k for k in (e_kosu, i_kosu) if k is not None)
    satirlar = []
    for lat, lon in noktalar:
        e = e_df.get((lat, lon)) if e_df else None
        i = i_df.get((lat, lon)) if i_df else None
        if e is None and i is None:
            continue
        satirlar += satirlar_uret(harmanla(e, i, lat, lon), KAYNAK, kosu, lat, lon)
    rapor["satir"] = _arsive_yaz(satirlar); rapor["kosu"] = kosu.isoformat()
    eski_temizle(dizin, get_settings().nwp_kosu_tut)
    return rapor


def eski_temizle(dizin: Path, tut: int = 2) -> list[str]:
    """Kaynak başına son `tut` koşu kalır; gerisi silinir (GRIB'ler büyüktür; arşiv DB'dedir)."""
    silinen = []
    for kalip in ("ecmwf_ifs_*.grib2", "icon_eu_*"):
        adaylar = sorted(dizin.glob(kalip), key=lambda p: p.name)
        for p in adaylar[:-tut] if tut > 0 else adaylar:
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True); silinen.append(p.name)
    for p in dizin.glob("*.part"):
        p.unlink(missing_ok=True)
    return silinen


def _cerceve_to_meteodata(df: pd.DataFrame, lat: float, lon: float, nwp_model: str = KAYNAK_ETIKET):
    from pvquant.io.meteo import MeteoData
    df = df.sort_index()
    return MeteoData(ghi=df["ghi"], temp_air=df["temp_air"], wind_speed_10m=df["wind_speed_10m"],
                     relative_humidity=None, cloud_cover=df["cloud_cover"] if "cloud_cover" in df else None,
                     latitude=float(lat), longitude=float(lon), timezone="UTC",
                     precipitation=df["precipitation"] if "precipitation" in df else None, snowfall=None,
                     kaynak=KAYNAK, nwp_model=nwp_model)


def arsivden_tahmin(lat: float, lon: float, days: int, past_days: int = 0, azami_yas_saat: float = 36.0):
    """Arşivdeki en taze koşudan ileri `days` gün; `past_days` için her saat en taze (≤24 s öncü) koşudan.
    Koşu yoksa ya da bayatsa None (çağıran indirmeyi tetikler)."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    la, lo = _nokta_anahtar(lat, lon)
    simdi = pd.Timestamp.now(tz="UTC")
    with sistem_baglami() as s:
        kosu = s.execute(text("SELECT max(kosu_zamani) FROM meteo_arsiv WHERE kaynak=:k AND lat=:la AND lon=:lo"),
                         {"k": KAYNAK, "la": la, "lo": lo}).scalar()
        if kosu is None or (simdi - pd.Timestamp(kosu).tz_convert("UTC")) > pd.Timedelta(hours=azami_yas_saat):
            return None
        bas = simdi.floor("D")
        ileri = pd.read_sql(text(
            "SELECT ts_utc, ghi, dni, dhi, temp_air, wind_speed_10m, cloud_cover, precipitation FROM meteo_arsiv "
            "WHERE kaynak=:k AND lat=:la AND lon=:lo AND kosu_zamani=:z AND ts_utc >= :a AND ts_utc < :b ORDER BY ts_utc"),
            s.connection(), params={"k": KAYNAK, "la": la, "lo": lo, "z": kosu, "a": bas, "b": bas + pd.Timedelta(days=days)},
            index_col="ts_utc", parse_dates=["ts_utc"])
        gecmis = pd.DataFrame()
        if past_days:
            gecmis = pd.read_sql(text(
                "SELECT DISTINCT ON (ts_utc) ts_utc, ghi, dni, dhi, temp_air, wind_speed_10m, cloud_cover, precipitation "
                "FROM meteo_arsiv WHERE kaynak=:k AND lat=:la AND lon=:lo AND ts_utc >= :a AND ts_utc < :b "
                "AND ts_utc - kosu_zamani BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' ORDER BY ts_utc, kosu_zamani DESC"),
                s.connection(), params={"k": KAYNAK, "la": la, "lo": lo, "a": bas - pd.Timedelta(days=past_days), "b": bas},
                index_col="ts_utc", parse_dates=["ts_utc"])
    df = pd.concat([gecmis, ileri]).sort_index()
    if df.empty:
        return None
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return _cerceve_to_meteodata(df, la, lo)


def arsivden_gecmis(lat: float, lon: float, start_date: str, end_date: str, asgari_kapsama: float = 0.9):
    """Kalibrasyon için 'servis meteosu' geçmişi: her saat en taze ≤24 s öncülü koşudan. Kapsama yetersizse None."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    la, lo = _nokta_anahtar(lat, lon)
    a = pd.Timestamp(start_date, tz="UTC"); b = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
    with sistem_baglami() as s:
        df = pd.read_sql(text(
            "SELECT DISTINCT ON (ts_utc) ts_utc, ghi, dni, dhi, temp_air, wind_speed_10m, cloud_cover, precipitation "
            "FROM meteo_arsiv WHERE kaynak=:k AND lat=:la AND lon=:lo AND ts_utc >= :a AND ts_utc < :b "
            "AND ts_utc - kosu_zamani BETWEEN INTERVAL '0 hour' AND INTERVAL '24 hour' ORDER BY ts_utc, kosu_zamani DESC"),
            s.connection(), params={"k": KAYNAK, "la": la, "lo": lo, "a": a, "b": b}, index_col="ts_utc", parse_dates=["ts_utc"])
    beklenen = int((b - a) / pd.Timedelta(hours=1))
    if df.empty or len(df) < asgari_kapsama * beklenen:
        return None
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return _cerceve_to_meteodata(df, la, lo)


def arsiv_durumu() -> dict:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        r = s.execute(text("SELECT kaynak, max(kosu_zamani) AS son, count(DISTINCT (lat,lon)) AS nokta, count(*) AS satir, "
                           "min(ts_utc) AS ilk, max(ts_utc) AS son_ts FROM meteo_arsiv GROUP BY kaynak")).mappings().all()
    return {x["kaynak"]: {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(x).items() if k != "kaynak"} for x in r}
