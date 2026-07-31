"""v2.77-A — aylik iklim beklentisi (Kitap KUTU-2 / Sartname yontemi).

Yontem: 20 yillik saatlik GHI arsivi -> yil-ay toplamlari -> her ayin
yillar-arasi dagilimindan P10/50/90. Iki SAF fonksiyon (DB'siz/agsiz test)
+ bir ince ag sargisi. Olcum (arsiv probu, 31 Tem): 20 yil tek cagri,
175.320 satir / 3,2 sn / %0 bosluk — parcalama gerekmez.
"""
from __future__ import annotations

import pandas as pd


def aylik_toplamlar(df: pd.DataFrame, tz: str | None = None) -> pd.DataFrame:
    """Saatlik GHI (W/m2, 'ghi' kolonu) -> yil-ay toplamlari (kWh/m2).

    tz verilirse ay siniri o takvimle cizilir (aylik_ozet emsali: 31 Mart
    21:00 UTC, Istanbul'da 1 Nisan'dir). Saatlik seri: W/m2 x 1h = Wh/m2.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["yil", "ay", "ghi_kwh_m2"])
    idx = df.index.tz_convert(tz) if tz else df.index
    idx = idx.tz_localize(None)
    g = df["ghi"].groupby([idx.year, idx.month]).sum() / 1000.0
    out = g.rename("ghi_kwh_m2").reset_index()
    out.columns = ["yil", "ay", "ghi_kwh_m2"]
    return out


def aylik_beklenti(toplamlar: pd.DataFrame) -> pd.DataFrame:
    """Yil-ay toplamlari -> ay basina P10/50/90 + yil_sayisi.

    Kuantil, ayni ayin YILLAR-ARASI dagilimindan (sartname: NWP aya
    uzatilmaz; beklenti iklimden gelir).
    """
    if toplamlar is None or toplamlar.empty:
        return pd.DataFrame(columns=["ay", "p10", "p50", "p90", "yil_sayisi"])
    g = toplamlar.groupby("ay")["ghi_kwh_m2"]
    out = pd.DataFrame({
        "p10": g.quantile(0.10), "p50": g.quantile(0.50),
        "p90": g.quantile(0.90), "yil_sayisi": g.count().astype(int),
    }).reset_index()
    return out.round({"p10": 1, "p50": 1, "p90": 1})


def tam_yillar(toplamlar: pd.DataFrame, ilk_yil: int,
               son_yil: int) -> pd.DataFrame:
    """Pencere disi yillari atar. tz kaydirmasi yil sinirinda saatlik
    kiymik uretir (31 Ara 21:00 UTC -> 1 Oca, sonraki yil); 0'a yakin bu
    sahte ay toplami kuantili zehirler — dagilima yalniz TAM yillar girer."""
    if toplamlar is None or toplamlar.empty:
        return toplamlar
    return toplamlar[(toplamlar["yil"] >= ilk_yil)
                     & (toplamlar["yil"] <= son_yil)].reset_index(drop=True)


def iklim_hesapla(lat: float, lon: float, yil_sayisi: int = 20,
                  tz: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ince ag sargisi: arsivden cek -> saf fonksiyonlardan gecir.
    Doner: (toplamlar, beklenti) — serpili katmani (v2.78) toplamlari da ister.

    Son TAM yila kadar `yil_sayisi` yil ceker (icinde bulunulan yil eksik
    oldugundan dagilimi egmesin diye disarida birakilir).
    """
    import datetime as dt

    from pvquant.io.meteo import OpenMeteoClient

    son_tam_yil = dt.date.today().year - 1
    baslangic = f"{son_tam_yil - yil_sayisi + 1}-01-01"
    bitis = f"{son_tam_yil}-12-31"
    ilk_yil = son_tam_yil - yil_sayisi + 1
    df = OpenMeteoClient(timeout=180).get_historical(
        lat, lon, baslangic, bitis).to_dataframe()
    t = tam_yillar(aylik_toplamlar(df, tz=tz), ilk_yil, son_tam_yil)
    return t, aylik_beklenti(t)


def iklim_beklentisi(lat: float, lon: float, yil_sayisi: int = 20,
                     tz: str | None = None) -> pd.DataFrame:
    """Geriye uyum: yalniz beklenti isteyenler icin (test/kapi)."""
    return iklim_hesapla(lat, lon, yil_sayisi, tz)[1]


def iklim_kaydet(tenant_id, plant_id, beklenti: pd.DataFrame) -> int:
    """Beklentiyi hazir-sonuc tablosuna upsert eder (KUTU-2: zamanlayici
    hesaplar). Upsert kalibi worker'in skill_daily yazimiyla ayni
    (ON CONFLICT DO UPDATE). Doner: yazilan satir sayisi."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami

    if beklenti is None or beklenti.empty:
        return 0
    satirlar = [
        {"t": str(tenant_id), "p": str(plant_id), "a": int(r["ay"]),
         "p10": float(r["p10"]), "p50": float(r["p50"]),
         "p90": float(r["p90"]), "y": int(r["yil_sayisi"])}
        for _, r in beklenti.iterrows()]
    with tenant_baglami(tenant_id) as s:
        s.execute(text(
            "INSERT INTO iklim_beklenti(tenant_id,plant_id,ay,"
            " ghi_p10_kwh_m2,ghi_p50_kwh_m2,ghi_p90_kwh_m2,"
            " yil_sayisi,hesap_zamani)"
            " VALUES(:t,:p,:a,:p10,:p50,:p90,:y,now())"
            " ON CONFLICT (plant_id,ay) DO UPDATE SET"
            " ghi_p10_kwh_m2=EXCLUDED.ghi_p10_kwh_m2,"
            " ghi_p50_kwh_m2=EXCLUDED.ghi_p50_kwh_m2,"
            " ghi_p90_kwh_m2=EXCLUDED.ghi_p90_kwh_m2,"
            " yil_sayisi=EXCLUDED.yil_sayisi,"
            " hesap_zamani=now()"), satirlar)
    return len(satirlar)


def iklim_oku(tenant_id, plant_id) -> pd.DataFrame:
    """Ekranin okudugu taraf — ham okuma, hesap yok."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami

    with tenant_baglami(tenant_id) as s:
        return pd.read_sql(text(
            "SELECT ay, ghi_p10_kwh_m2, ghi_p50_kwh_m2, ghi_p90_kwh_m2,"
            " yil_sayisi, hesap_zamani FROM iklim_beklenti"
            " WHERE plant_id=:p ORDER BY ay"),
            s.connection(), params={"p": str(plant_id)})


def iklim_yil_kaydet(tenant_id, plant_id, toplamlar: pd.DataFrame) -> int:
    """20 yil serpilisinin hazir-sonuc katmani (v2.78-A). Upsert kalibi ayni."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami

    if toplamlar is None or toplamlar.empty:
        return 0
    satirlar = [
        {"t": str(tenant_id), "p": str(plant_id), "y": int(r["yil"]),
         "a": int(r["ay"]), "g": float(r["ghi_kwh_m2"])}
        for _, r in toplamlar.iterrows()]
    with tenant_baglami(tenant_id) as s:
        s.execute(text(
            "INSERT INTO iklim_yil(tenant_id,plant_id,yil,ay,"
            " ghi_kwh_m2,hesap_zamani)"
            " VALUES(:t,:p,:y,:a,:g,now())"
            " ON CONFLICT (plant_id,yil,ay) DO UPDATE SET"
            " ghi_kwh_m2=EXCLUDED.ghi_kwh_m2, hesap_zamani=now()"), satirlar)
    return len(satirlar)


def iklim_yil_oku(tenant_id, plant_id) -> pd.DataFrame:
    """Serpilinin okuyan yolu — ham okuma, hesap yok."""
    from sqlalchemy import text

    from pvquant.db import tenant_baglami

    with tenant_baglami(tenant_id) as s:
        return pd.read_sql(text(
            "SELECT yil, ay, ghi_kwh_m2 FROM iklim_yil"
            " WHERE plant_id=:p ORDER BY yil, ay"),
            s.connection(), params={"p": str(plant_id)})
