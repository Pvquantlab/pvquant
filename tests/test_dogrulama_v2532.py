"""03.11.2026 doğrulama arşivi (~/Desktop/PVQuant_Kapsamli_Dogrulama_Arastirmasi, 04.11.2026 kapanışı) A kanıtlı bulguların koda yansıması — v2.532.
DK-016: AFL zinciri Karar 6851 halkası (7.1.2017–28.2.2017 teslim günleri 500 TL/MWh). DK-306/DK-304: CK 2949 grubu (1.1–30.6.2021 giriş) son yıl 2030.
DK-287/DK-285: YEK fiyatı destek süresi dolunca üretilmez. DK-294: 7189 rejiminde ¢ × kur yedek dalı yok. DK-301: m.23(6) KGÜP = 0 okuması sayıyla.
DK-180/DK-195: sayaç çekişi UEÇM olarak net sapmaya girer; yoksa 0 varsayımı etikette."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from pvquant.ext.turkiye import dengesizlik as d
from pvquant.ext.turkiye import kurallar as kr
from pvquant.ext.turkiye import takvim as tk
from pvquant.services import dengesizlik_service as ds
from pvquant.services import piyasa_service as ps
from pvquant.services import tarife_service as ts
from pvquant.services import yekdem_service as ys


def test_afl_2017_karar_6851_halkasi():
    assert kr.afl(date(2017, 1, 6)) == 2000.0 and kr.afl(date(2017, 1, 7)) == 500.0
    assert kr.afl(date(2017, 2, 28)) == 500.0 and kr.afl(date(2017, 3, 1)) == 2000.0 and kr.afl(date(2019, 12, 31)) == 2000.0
    assert "6851" in kr.afl_dayanak(date(2017, 2, 1)) and "7.1.2017" in kr.afl_dayanak(date(2017, 2, 1)) and "6851" in kr.afl_dayanak(date(2017, 3, 1))
    assert "6851" not in kr.afl_dayanak(date(2017, 1, 6))


def test_yekdem_suresi_ck_2949_grubu():
    y = tk.yekdem_suresi(date(2021, 3, 15))
    assert y["rejim"] == "2949" and y["ilk_yil"] == 2022 and y["son_yil"] == 2030 and "2949" in y["kaynak"]
    assert tk.yekdem_suresi(date(2021, 1, 1))["son_yil"] == 2030 and tk.yekdem_suresi(date(2021, 6, 30))["son_yil"] == 2030
    assert tk.yekdem_suresi(date(2020, 12, 31))["rejim"] == "5905-27" and tk.yekdem_suresi(date(2020, 12, 31))["son_yil"] == 2031
    assert tk.yekdem_suresi(date(2021, 7, 1))["rejim"] == "7189"
    assert "2949" in ys.rejim_turet({"isletmeye_giris": "2021-03-15", "tarife": {"tip": "yekdem"}})["kaynak"]


def test_yek_fiyati_sure_dolunca_yok():
    # Cetvel I, elle kur: giriş 1.5.2010 → 5905-27 grubu 2011–2020; 31.12.2020 fiyat var, 1.1.2021 yok
    pj = {"isletmeye_giris": "2010-05-01", "tarife": {"tip": "yekdem", "rejim": "cetvel1", "kur_tl_usd": 40}}
    s = ys.gunluk_fiyat_serisi(pj, date(2020, 12, 31), date(2021, 1, 1))
    assert s["yek_tl_mwh"].iloc[0] == 5320.0 and np.isnan(s["yek_tl_mwh"].iloc[1]) and s["kaynak"].iloc[1] == "sure_doldu" and s["kaynak"].iloc[0] != "sure_doldu"
    assert ys.gun_fiyati(pj, date(2021, 1, 1))["toplam_tl_mwh"] is None
    # kullanıcı başlangıç yılı 2015 → son yıl 2024
    s2 = ys.gunluk_fiyat_serisi({**pj, "yekdem_baslangic_yili": 2015}, date(2024, 12, 31), date(2025, 1, 1))
    assert list(s2["kaynak"] == "sure_doldu") == [False, True]
    # CK 2949 grubu: 31.12.2030'a kadar
    s3 = ys.gunluk_fiyat_serisi({**pj, "isletmeye_giris": "2021-03-15"}, date(2030, 12, 31), date(2031, 1, 1))
    assert list(s3["kaynak"] == "sure_doldu") == [False, True]
    # 7189: işletmeye girişten 10 yıl
    pj7 = {"isletmeye_giris": "2022-03-01", "tarife": {"tip": "yekdem"}}
    s7 = ys.gunluk_fiyat_serisi(pj7, date(2032, 2, 29), date(2032, 3, 1))   # 2032 artık yıl
    assert s7["kaynak"].iloc[0] != "sure_doldu" and s7["kaynak"].iloc[1] == "sure_doldu" and np.isnan(s7["yek_tl_mwh"].iloc[1])
    assert "sure_doldu" in ys.KAYNAK_ETIKET


def test_tarife_7189_yedek_dal_kapali():
    t = {"tip": "yekdem", "usd_cent_kwh": 13.3, "kur_tl_usd": 40}
    with pytest.raises(ValueError, match="7189"):
        ts._yekdem_tarife(t, {"params_json": {"isletmeye_giris": "2022-03-01"}}, date(2020, 1, 1), date(2020, 1, 2))   # ilan öncesi dönem
    y = ts._yekdem_tarife(t, {"params_json": {"isletmeye_giris": "2010-05-01"}}, date(2015, 1, 1), date(2015, 1, 2))      # Cetvel I: elle kur yedek kalır
    assert y is not None
    assert ts._yekdem_tarife(t, None, None, None) is not None                                                              # plant yok: eski yol


def _pv():
    idx = pd.date_range("2026-10-20 06:00", periods=7, freq="h", tz="UTC")
    return pd.DataFrame({"ptf": [50, 50, 2000, 50, 50, 50, 10], "smf": [40, 40, 1900, 40, 40, 40, 5], "yon": ["fazla", "acik", "fazla", "fazla", "fazla", "fazla", "fazla"],
                         "kgup": [5.0] * 7, "gerceklesen": [6, 6, 6, 4, 6, 6, 7], "program_kaynak": ["bildirilen", "oneri", "oneri", "oneri", "oneri", "oneri", "oneri"]}, index=idx)


def test_m23_6_kgup_sifir_okumasi():
    pv = _pv(); yek = pd.Series([3000.0, 3000.0, 3000.0, 3000.0, 40.0, np.nan, 3000.0], index=pv.index)
    e = ys.m23_6_isaretle(pv, yek)
    assert e["yekdem_disi_mwh"].tolist() == [1.0, 0, 0, 0, 0, 0, 2.0]                   # program okuması değişmedi
    assert e["kgup0_mwh"].tolist() == [0.0, 0, 0, 4.0, 0, 0, 7.0]                       # bildirilen saat hariç; program altı saat (4 < 5) da girer
    assert abs(e["kgup0_tl"].iloc[3] - 4.0 * (3000 - 0.98 * 50)) < 1e-9 and e["kgup0_tl"].iloc[0] == 0.0
    o = ys.m23_6_ozeti(pv, e, 30)
    assert o["kgup0_saat"] == 2 and o["kgup0_mwh"] == 11.0 and o["kgup0_tl"] > o["yekdem_disi_tl"] and "KGÜP = 0 okuması" in o["not"]
    assert ys.m23_6_isaretle(pv.drop(columns=["program_kaynak"]), yek)["kgup0_mwh"].sum() == 0.0


def _df_saat(bas: str, n: int, cekis_kw):
    ix = pd.date_range(bas, periods=n, freq="h", tz="UTC")
    return pd.DataFrame({"ts_utc": ix, "gercek_kw": 1000.0, "kgup_kw": 1000.0, "naif_kw": np.nan, "cekis_kw": cekis_kw})


def test_uecm_sayac_cekisinden_net_sapma():
    f = ps.senaryo_fiyat(pd.DatetimeIndex(_df_saat("2026-11-05 06:00", 6, 300.0)["ts_utc"]))
    pv0, *_ = ds.saatlik_hesap(_df_saat("2026-11-05 06:00", 6, np.nan), f, segment="lisansli_serbest")
    pv1, *_ = ds.saatlik_hesap(_df_saat("2026-11-05 06:00", 6, 300.0), f, segment="lisansli_serbest")
    assert pv0["net_sapma"].all() and pv0["uecm"].isna().all() and (pv0["kupsm"] == 0).all()               # çekiş yok → UEÇM 0, sapma 0
    assert (pv1["uecm"] == 0.3).all() and np.allclose(pv1["kupsm"], 0.3 - 0.08 * 1.0)                       # |(1,0 − 0,3) − 1,0| − m·BUDÜP
    r = ds.hesapla_df(_df_saat("2026-11-05 06:00", 6, 300.0), f, segment="lisansli_serbest")
    assert r["program"]["uecm_saat"] == 6 and r["program"]["net_sapma_saat"] == 6 and "sayaç çekişinden" in r["program"]["uecm_etiketi"]
    r0 = ds.hesapla_df(_df_saat("2026-11-05 06:00", 6, np.nan), f, segment="lisansli_serbest")
    assert r0["program"]["uecm_saat"] == 0 and "0 varsayıldı" in r0["program"]["uecm_etiketi"]
    # 1.11.2026 öncesi brüt sapma: çekiş KÜPSM'e girmez, etiket yok
    fo = ps.senaryo_fiyat(pd.DatetimeIndex(_df_saat("2026-10-05 06:00", 6, 300.0)["ts_utc"]))
    pvo, *_ = ds.saatlik_hesap(_df_saat("2026-10-05 06:00", 6, 300.0), fo, segment="lisansli_serbest")
    assert (~pvo["net_sapma"]).all() and (pvo["kupsm"] == 0).all()
    assert ds.hesapla_df(_df_saat("2026-10-05 06:00", 6, 300.0), fo, segment="lisansli_serbest")["program"]["uecm_etiketi"] is None
    assert "UEÇM" in ds.DOKUM_NOTU_SAYAC and "Geçici m.1" in ds.teminat_gostergesi(pd.DataFrame(), None)["not"]
    # motor: uecm_mwh verilmeyince eski davranış
    idx = pd.date_range("2026-11-05 06:00", periods=3, freq="h", tz="UTC")
    pv = d.saatlik(pd.Series(1.0, index=idx), pd.Series(1.0, index=idx), pd.Series(2000.0, index=idx), pd.Series(2000.0, index=idx), yon="dengede", segment="lisansli_serbest")
    assert (pv["uecm"] == 0).all() and pv["net_sapma"].all()


def test_saat_profili_hesapla_saf():
    """04.11 v2.532: saat × gün hata haritası kaldırıldı; saat profili (işaretli ortalama, sistematik saatler) SAF çekirdek."""
    from pvquant.services import accuracy_service as acc
    bugun = pd.Timestamp("2026-10-24 12:00", tz="Europe/Istanbul")
    satirlar = []
    for g in range(10):                                        # 14–23 Ekim yerel günler
        gun = pd.Timestamp("2026-10-14", tz="Europe/Istanbul") + pd.Timedelta(days=g)
        for h in range(6, 19):
            ts = (gun + pd.Timedelta(hours=h)).tz_convert("UTC")
            ger = 1000.0 if 8 <= h <= 16 else 150.0                     # %2 eşiği 100 kW (dâhil değil) — 150 gündüz sayılır
            hata = 300.0 if 11 <= h <= 13 else (-5.0 if h == 7 else 10.0)    # öğle 3 saat sistematik fazla; 07 gece eşiği altı
            satirlar.append({"ts_utc": ts, "p50_kw": ger + hata, "run_at": ts - pd.Timedelta(hours=12), "power_kw": ger})
    df = pd.DataFrame(satirlar)
    r = acc.saat_profili_hesapla(df, 5000.0, "Europe/Istanbul", 30, bugun=bugun)
    assert r["gun_sayisi"] == 10 and r["ilk_gun"] == "2026-10-14" and r["son_gun"] == "2026-10-23" and r["esik_kw"] == 250.0
    pr = {x["saat"]: x for x in r["profil"]}
    assert pr["12–13"]["ort_hata_kw"] == 300.0 and pr["12–13"]["n"] == 10 and pr["09–10"]["ort_hata_kw"] == 10.0
    assert pr["05–06"]["n"] == 0 and pr["05–06"]["ort_hata_kw"] is None                      # veri yok
    assert pr["07–08"]["ort_hata_kw"] == -5.0 and pr["07–08"]["n"] == 10                       # eşik altı sapma: sistematik değil
    assert [x["saat"] for x in r["sistematik"]] == ["11–12", "12–13", "13–14"] and {x["yon"] for x in r["sistematik"]} == {"fazla"}
    bos = acc.saat_profili_hesapla(df.iloc[0:0], 5000.0, "Europe/Istanbul", 30, bugun=bugun)
    assert bos["gun_sayisi"] == 0 and len(bos["profil"]) == 15 and bos["sistematik"] == []
    # dünden sonraki gün pencere dışı; 5 günden az gözlem sistematik sayılmaz
    r5 = acc.saat_profili_hesapla(df[df.ts_utc >= pd.Timestamp("2026-10-20", tz="Europe/Istanbul")], 5000.0, "Europe/Istanbul", 30, bugun=bugun)
    assert r5["gun_sayisi"] == 4 and r5["sistematik"] == []
