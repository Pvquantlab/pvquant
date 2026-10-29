"""F-07 kabul (F_PRD): C geri testinin yeniden üretimi — ürün motoru (saatlik / dsg_saatlik) C iş kolunun bağımsız modeliyle ±1 TL.
Hedef 12 ay (27.10.2025–26.10.2026, seg ≥ 2025-10b), yürürlükteki kural saat bazında; yıllaştırma seg ölçeğiyle (V6)."""
from pathlib import Path

import pandas as pd
import pytest

from pvquant.ext.turkiye import dengesizlik as d

MW = 5.0
HEDEF_T1 = {5: (288220, 144805, 130541, 12874), 8: (470805, 227963, 207344, 35498), 12: (720368, 337437, 310135, 72796),
            15: (911844, 420732, 388115, 102997), 20: (1234852, 562445, 516847, 155559)}


@pytest.fixture(scope="module")
def c():
    df = pd.read_csv(Path(__file__).parent / "data" / "c_geri_test_senaryolar.csv")
    df["ts"] = pd.to_datetime(df["tarih"].astype(str) + " " + df["saat"].astype(int).astype(str) + ":00").dt.tz_localize("Europe/Istanbul").dt.tz_convert("UTC")
    df = df.set_index("ts")
    df["agir"] = df["gec"].fillna(0) * df["olcek"]
    df["hedef"] = df["seg"].map(lambda s: s >= "2025-10b" or s.startswith("2026"))
    return df


@pytest.mark.parametrize("w", [5, 8, 12, 15, 20])
def test_t1_s1_yillik(c, w):
    s = d.saatlik(c[f"F{w}"] * MW, c["A"] * MW, c["PTF"], c["SMF"], yon=c["yon"], segment="lisansli_serbest").reindex(c.index)
    eksik = ((-s["sapma"]).clip(lower=0) * (s["p_neg"] - s["ptf"])).fillna(0)
    fazla = (s["sapma"].clip(lower=0) * (s["ptf"] - s["p_poz"])).fillna(0)
    kup = s["kupst"].fillna(0); m = c["hedef"]
    top = float(((eksik + fazla + kup) * c["agir"])[m].sum())
    hedef = HEDEF_T1[w]
    assert top == pytest.approx(hedef[0], abs=1.0), (w, top)
    assert float((eksik * c["agir"])[m].sum()) == pytest.approx(hedef[1], abs=1.0)
    assert float((fazla * c["agir"])[m].sum()) == pytest.approx(hedef[2], abs=1.0)
    assert float((kup * c["agir"])[m].sum()) == pytest.approx(hedef[3], abs=1.0)
    assert (s["durum"] == "ok").all()                     # bülten yönü her saatte var; KÜPST katsayısı tarihli tablodan


def test_t6_s3_dsg_w15(c):
    prog = {f"u{i}": (c["A"] - c[f"d15_{i}"]) * MW for i in (1, 2, 3, 4)}
    ger = {f"u{i}": c["A"] * MW for i in (1, 2, 3, 4)}
    r = d.dsg_saatlik(prog, ger, c["PTF"], c["SMF"], yon=c["yon"], segmentler={u: "lisansli_serbest" for u in prog})
    sa = r["saatlik"].reindex(c.index); m = c["hedef"]
    dsg = float((sa["kayip_dsg"].fillna(0) * c["agir"])[m].sum()); tek = float((sa["kayip_tek"].fillna(0) * c["agir"])[m].sum())
    ku = float((sa["kupst_uye"].fillna(0) * c["agir"])[m].sum())
    assert dsg + ku == pytest.approx(3202845, abs=1.0)    # DSG eşikli toplam
    assert tek + ku == pytest.approx(3483043, abs=1.0)    # 4 santral tek başına
    assert ku == pytest.approx(414994, abs=1.0)           # KÜPST netleşmez
    assert tek - dsg == pytest.approx(280198, abs=1.0)    # eşikli netleşme farkı


def _toplam(c, m, karsi_olgu=None):
    s = d.saatlik(c["F15"] * MW, c["A"] * MW, c["PTF"], c["SMF"], yon=c["yon"], segment="lisansli_serbest", karsi_olgu=karsi_olgu).reindex(c.index)
    return float(((s["dengesizlik_maliyeti"].fillna(0) + s["kupst"].fillna(0)) * c["agir"])[m].sum())


def test_t1_karsi_olgu_sutunlari(c):
    """T1 W15: 2025 yılı yürürlük 634.526; 2025 yılı «2026 kuralı olsaydı» 805.767; hedef «2026 kuralı tüm döneme» 949.292 (C Yillik)."""
    y25 = c["seg"].str.startswith("2025")
    assert _toplam(c, y25) == pytest.approx(634526, abs=1.0)
    assert _toplam(c, y25, "2026") == pytest.approx(805767, abs=1.0)
    assert _toplam(c, c["hedef"], "2026") == pytest.approx(949292, abs=1.0)
    assert _toplam(c, c["hedef"], "2026_V100") < _toplam(c, c["hedef"], "2026")   # V=100 B dalını daraltır → daha düşük kayıp
