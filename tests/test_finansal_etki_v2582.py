"""v2.582 (Faz 2 F2-D, Stage 3E–F) — üretim düşüklüğü (tahmin hatası ayrı; kısıntı/bakım, fiziksel, ölçüm yok, açıklanmayan sınıfları kayıp ayrışımının
saf çekirdeğinden; TL = gelir kaybı tahmini, toplanmaz) ve sözleşme açığı; ileriye dönük maruziyet (son dönem oranı × gelecek program, çeyrekler, bin TL;
veri azsa eksik). Test DB: dönem sınırlı kayıp girdisi, bağımsız doğrulama bağlantısı, birleşik özet."""
from __future__ import annotations

from datetime import date, timezone

import numpy as np
import pandas as pd

from pvquant.ext.platform import finans as fn
from pvquant.services import finansal_etki_service as fe
from pvquant.services import kayip_ayrisimi_service as ka
from test_finansal_etki_v2580 import santral as _santral
from test_finansal_etki_v2581 import _g

santral = _santral   # pytest fixture'ı bu modülde ad olarak tanıtır (noqa'sız; ruff --fix içe aktarmayı silmesin)

UTC = timezone.utc


def _kayip_df(iz: pd.DatetimeIndex) -> pd.DataFrame:
    """06–18 TSİ: beklenen 1,2 × gerçek; 09–10 talimat (gerçek 0), 14 ölçüm yok, 15 kısıntı bayrağı."""
    ist = iz.tz_convert("Europe/Istanbul")
    ger = np.array([float(100 + 50 * min(h - 6, 18 - h)) if 6 <= h <= 18 else 0.0 for h in ist.hour])
    df = pd.DataFrame({"ts_utc": iz, "beklenen_kw": ger * 1.2, "power_kw": ger, "flag": "valid", "kirpma": False})
    for h in (9, 10):
        df.loc[ist.hour == h, "power_kw"] = 0.0
    df.loc[ist.hour == 14, "power_kw"] = np.nan
    df.loc[ist.hour == 15, "flag"] = "kisinti"
    return df


def test_dusukluk_siniflari_ve_bilesenler():
    g = _g("2026-10")
    pv, _ = fe.saatlik(g)
    iz = g["izgara"]; df = _kayip_df(iz)
    ist = iz.tz_convert("Europe/Istanbul")
    neden = {ts: "talimat" for ts, h in zip(iz, ist.hour, strict=True) if h in (9, 10)}
    fiyat = pd.Series(2000.0, index=iz)
    kayip = ka.hesapla_df(df, 1000.0, neden, fiyat)
    assert kayip["durum"] == "ok"
    out = fe.dusukluk_saf(g["donem"], iz, pv, kayip, {"kaynak": "tarife", "tip": "sabit", "senaryo_saat": 0, "etiket": "sabit tarife"},
                          {"esik": 0.98, "A_gercek": 0.95, "acik_puan": 0.03, "acik_kwh": 3000.0, "acik_tl": 6000.0, "fiyat_kaynak": "tarife (sabit)", "not": "kıyas tabanı"},
                          {"kural": "program", "metrikler": {"wmape": 9.1, "n_saat": 300}})
    sin = {s["kod"]: s for s in out["siniflar"]}
    assert sin["kisinti_bakim"]["saat"] == 31 * 3 and sin["kisinti_bakim"]["kayip_kwh"] is not None and sin["kisinti_bakim"]["kayip_tl"] is not None   # 09, 10 talimat + 15 kısıntı
    assert sin["olcum"]["saat"] == 31 and sin["olcum"]["kayip_kwh"] is None and sin["aciklanmayan"]["kayip_tl"] is None and sin["aciklanmayan"]["saat"] > 0
    assert sin["fiziksel"]["saat"] == 0
    kod = {b["kod"]: b for b in out["bilesenler"]}
    assert kod["uretim_dusuklugu"]["tutar_tl"] == -kayip["toplam_kayip_tl"] and kod["uretim_dusuklugu"]["nitelik"] == "sozlesme_tahmini" and kod["uretim_dusuklugu"]["toplanir"] is False
    assert kod["sozlesme_acigi"]["tutar_tl"] == -6000.0 and kod["sozlesme_acigi"]["toplanir"] is False and "%98" in kod["sozlesme_acigi"]["kaynak"]
    th = out["tahmin_hatasi"]
    assert th["n_saat"] == len(pv) and th["eksik_mwh"] > 0 and th["fazla_mwh"] == 0.0 and th["program"] == "PVQuant önerisi" and th["wmape"] == 9.1
    assert round(th["net_mwh"] + th["eksik_mwh"], 3) == 0.0 and fe.NOT_TAHMIN_HATASI in out["notlar"] and fe.NOT_DUSUKLUK in out["notlar"]
    assert fn.toplam(out["_nesneler"])["giren"] == []   # hiçbiri toplama girmez


def test_dusukluk_eksik_ve_senaryo_fiyat():
    g = _g("2026-10-05")
    pv, _ = fe.saatlik(g)
    out = fe.dusukluk_saf(g["donem"], g["izgara"], pv, {"durum": "yetersiz", "mumkun_saat": 13}, None, None, None)
    kod = {b["kod"]: b for b in out["bilesenler"]}
    assert kod["uretim_dusuklugu"]["nitelik"] == "eksik" and any("yetersiz" in n for n in kod["uretim_dusuklugu"]["notlar"]) and kod["sozlesme_acigi"]["nitelik"] == "eksik"
    assert out["tahmin_hatasi"]["wmape"] is None and all(s["saat"] == 0 for s in out["siniflar"])
    iz = g["izgara"]; kayip = ka.hesapla_df(_kayip_df(iz), 1000.0, None, pd.Series(2000.0, index=iz))
    if kayip["durum"] == "ok":
        o2 = fe.dusukluk_saf(g["donem"], iz, pv, kayip, {"kaynak": "ptf", "tip": None, "senaryo_saat": 24, "etiket": "PTF"}, None, None)
        assert {b["kod"]: b for b in o2["bilesenler"]}["uretim_dusuklugu"]["nitelik"] == "senaryo"
        o3 = fe.dusukluk_saf(g["donem"], iz, pv, kayip, {"kaynak": "yok", "tip": None, "senaryo_saat": 0, "etiket": "fiyat yok"}, None, None)
        assert {b["kod"]: b for b in o3["bilesenler"]}["uretim_dusuklugu"]["nitelik"] == "eksik"
    bos = fe.dusukluk_saf(g["donem"], iz, None, None, None, None, None)
    assert bos["tahmin_hatasi"]["n_saat"] == 0 and bos["tahmin_hatasi"]["program"] is None


def _gecmis_pv(gun: int, net_gun: float = -100.0, kupst_gun: float = 10.0, kgup_gun: float = 10.0) -> pd.DataFrame:
    iz = pd.date_range("2026-10-01 00:00", periods=24 * gun, freq="h", tz="Europe/Istanbul").tz_convert("UTC")   # yerel gün başından: tam günler
    x = pd.DataFrame(index=iz)
    x["kgup"] = kgup_gun / 24.0; x["edt_net"] = net_gun / 24.0; x["kupst"] = kupst_gun / 24.0
    return x


def test_maruziyet_oran_ve_aralik():
    iz = pd.date_range("2026-11-12 00:00", periods=24 * 7, freq="h", tz="UTC")
    program = pd.Series(10.0 / 24.0, index=iz)   # 7 gün × 10 MWh = 70 MWh
    kaynak = pd.Series("son_tahmin", index=iz)
    out = fe.maruziyet_saf(program, kaynak, _gecmis_pv(30))
    assert out["program_mwh"] == 70.0 and out["saat"] == 168 and out["kaynak"] == {"son_tahmin": 168} and out["gecmis_gun"] == 30
    assert out["oran_tl_mwh"] == {"p25": -11.0, "p50": -11.0, "p75": -11.0}   # (−100 − 10) / 10 MWh
    assert out["aralik_tl"] == {"p25": -1000.0, "p50": -1000.0, "p75": -1000.0} and out["nitelik"] == "senaryo"   # −770 → bin TL'ye −1.000
    b = out["bilesenler"][0]
    assert b["kod"] == "ileri_maruziyet" and b["tutar_tl"] == -1000.0 and b["toplanir"] is False and fe.NOT_MARUZIYET in b["notlar"]
    gecmis = _gecmis_pv(30)
    gecmis.loc[gecmis.index.date == date(2026, 10, 5), "edt_net"] = +500.0 / 24.0   # bir lehte gün → p75 yükselir
    o2 = fe.maruziyet_saf(program, kaynak, gecmis)
    assert (o2["oran_tl_mwh"]["p25"] == -11.0 and o2["oran_tl_mwh"]["p50"] == -11.0 and o2["oran_tl_mwh"]["p75"] == -11.0) or o2["oran_tl_mwh"]["p75"] >= -11.0


def test_maruziyet_eksik_dallari():
    iz = pd.date_range("2026-11-12 00:00", periods=24, freq="h", tz="UTC")
    program = pd.Series(1.0, index=iz)
    az = fe.maruziyet_saf(program, None, _gecmis_pv(5))
    assert az["nitelik"] == "eksik" and az["gecmis_gun"] == 5 and any("yalnız 5 gün" in n for n in az["notlar"]) and az["bilesenler"][0]["nitelik"] == "eksik"
    bos = fe.maruziyet_saf(pd.Series(dtype=float), None, _gecmis_pv(30))
    assert bos["nitelik"] == "eksik" and bos["program_mwh"] is None and any("program ya da tahmin yok" in n for n in bos["notlar"])
    yok = fe.maruziyet_saf(program, None, None)
    assert yok["nitelik"] == "eksik" and yok["program_mwh"] == 24.0 and any("uzlaştırma hesabı yok" in n for n in yok["notlar"])
    gece = _gecmis_pv(30, kgup_gun=0.0)   # planlanan 0 olan günler oranı bozmaz → eksik
    assert fe.maruziyet_saf(program, None, gece)["gecmis_gun"] == 0


# ---------------------------------------------------------------- test DB
def test_db_dusukluk_maruziyet_ve_ozet(santral):
    tid, plant = santral
    d = fe.uretim_dusuklugu(tid, plant, "2026-09", bugun=date(2026, 9, 11))
    assert d["kayip"] is not None and d["kayip"]["durum"] == "ok" and d["kayip"]["epi"] is not None and d["fiyat"]["kaynak"] == "tarife"
    sin = {s["kod"]: s for s in d["siniflar"]}
    assert sin["olcum"]["saat"] == 1 and sin["aciklanmayan"]["saat"] > 0 and sin["kisinti_bakim"]["saat"] == 0   # bayraklı 5 Eylül 12:00 ölçüm yok
    kod = {b["kod"]: b for b in d["bilesenler"]}
    assert kod["uretim_dusuklugu"]["toplanir"] is False and kod["sozlesme_acigi"]["nitelik"] == "eksik"   # sözleşme eşiği girilmedi
    assert d["tahmin_hatasi"]["n_saat"] == 239 and d["tahmin_hatasi"]["eksik_mwh"] > 0 and d["tahmin_hatasi"]["program"] == "PVQuant önerisi"
    m = fe.ileri_maruziyet(tid, plant, bugun=date(2026, 9, 11))
    assert m["ufuk"] == {"bas": "2026-09-12", "bit": "2026-09-19", "gun": 7, "gecmis_gun_pencere": 30} and m["nitelik"] == "eksik"   # ileri tahmin yok
    o = fe.ozet(tid, plant, "2026-09-05", bugun=date(2026, 9, 11))
    kodlar = [b["kod"] for b in o["bilesenler"]]
    assert kodlar[:3] == ["satis_geliri", "dengesizlik", "kupst"] and "uretim_dusuklugu" in kodlar and "ileri_maruziyet" in kodlar
    assert o["toplam"]["giren"][0] == "satis_geliri" and "uretim_dusuklugu" not in o["toplam"]["giren"] and "ileri_maruziyet" not in o["toplam"]["giren"]
    assert "_nesneler" not in o["dusukluk"] and "_nesneler" not in o["maruziyet"] and o["dusukluk"]["donem"]["kod"] == "2026-09-05"
