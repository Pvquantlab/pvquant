"""Açık Konular Kapanışı (14.11.2026) → entegrasyon Kulvar A testleri (15.11.2026). DB'siz, saf katman.
Her test araştırmanın T-id / AK kimliğini taşır; TL tutarları araştırmanın örnek hesap satırlarından (sentetik girdiler, OLGU: formül)."""
from datetime import date

import httpx
import pandas as pd
import pytest

from pvquant.ext.turkiye import depolama, dengesizlik as d, epias, kural_sicili as ks, kurallar as kr, takvim as tk


# ---- T-04 (AK-0247): naif damga UTC sayılır, İstanbul gününe çevrilir (parametre_cercevesi ile aynı sözleşme)
def test_t04_naif_damga_utc_sayilir():
    assert kr.kural(pd.Timestamp("2025-12-31 21:30")).edt.rejim == "2026"          # 21:30 UTC = 01.01.2026 00:30 İstanbul
    assert kr.kural(pd.Timestamp("2026-10-31 22:00")).edt.V == 100.0              # 22:00 UTC = 01.11.2026 01:00 İstanbul → V100
    assert kr.kural(pd.Timestamp("2026-10-31 20:00")).edt.V == 150.0              # 23:00 İstanbul, hâlâ 31.10
    assert kr.kural(pd.Timestamp("2026-10-31 22:00", tz="UTC")).edt.V == 100.0   # tz'li yol değişmedi
    assert kr.kural(date(2026, 10, 31)).edt.V == 150.0                            # date yolu değişmedi
    idx = pd.DatetimeIndex([pd.Timestamp("2025-12-31 21:30")])
    assert kr.parametre_cercevesi(idx)["rejim"].iloc[0] == "2026"                 # iki yol artık aynı günü görüyor


# ---- T-08 (AK-0020): GİP üst limiti = AFL × (1 + min(k, l)) — DUY m.66/C(6)
def test_t08_gip_ust_limit():
    assert kr.gip_ust_limit(date(2026, 11, 10)) == pytest.approx(4635.00)          # 4.500 × 1,03 (G1-075)
    assert kr.gip_ust_limit(date(2026, 3, 1)) == pytest.approx(3400 * 1.03)        # AFL 3.400 dönemi
    assert kr.gip_ust_limit(pd.Timestamp("2026-11-10 09:00", tz="Europe/Istanbul")) == pytest.approx(4635.00)


# ---- T-15 (AK-1343, AK-0016 B1): V sınırı «<» korunur; bilinen sapma 03.11.2026 12:00 bültende −106 (çeyrek SMF gerekir)
def _bf(ts, ptf, smf, yon):
    idx = pd.DatetimeIndex([pd.Timestamp(ts, tz="Europe/Istanbul")])
    return d.birim_fiyatlar(pd.Series([ptf], index=idx), pd.Series([smf], index=idx), yon)


def test_t15_v_siniri_kucuktur_korunur():
    r = _bf("2026-11-03 12:00", 2000.01, 100.00, "fazla")
    assert float(r["p_poz"].iloc[0]) == pytest.approx(94.00)                       # min = 100 = V → «<» sağlanmaz → 100·(1−0,06) (G1-061; bülten −106: BİLİNEN SAPMA)
    r2 = _bf("2026-04-05 05:00", 2000.00, 150.00, "fazla")
    assert float(r2["p_poz"].iloc[0]) == pytest.approx(141.00)                     # V = 150 döneminde min = V → 150·0,94 (G1-062)
    r3 = _bf("2026-11-03 12:00", 2000.01, 99.99, "fazla")
    assert float(r3["p_poz"].iloc[0]) == pytest.approx(-106.00)                    # min < V → B dalı −100·1,06


# ---- T-53 (AK-0792 B1): depolama yıl sayacı takvim yılıyla
def test_t53_depolama_yil_sayaci():
    assert depolama.emre_amadelik(date(2024, 3, 1), bugun=date(2029, 2, 28))["yil"] == 5
    assert depolama.emre_amadelik(date(2024, 3, 1), bugun=date(2029, 3, 1))["yil"] == 6
    assert depolama.emre_amadelik(date(2024, 3, 1), bugun=date(2024, 3, 1))["yil"] == 1
    assert depolama.emre_amadelik(date(2024, 3, 1), bugun=date(2024, 2, 1))["yil"] == 0


# ---- T-42 (AK-0040 B1): itiraz son anı kaydırılmaz
def test_t42_itiraz_son_kaydirma_yok():
    o = tk.donem_takvimi(2026, 11)
    i = next(x for x in o if x["kod"] == "itiraz_son")
    assert i["tarih"] == "2026-12-12" and i["kaydirma"] == "yok" and "kaydırma yok" in i["not"]


# ---- T-55 (AK-1340, AK-0054 B1): eski YEKDEM dengesizlik ucu 30.04.2016 sonrası istek atmaz
def test_t55_yek_dengesizlik_ucu_kilitli():
    kayit = []
    def h(req: httpx.Request):
        if "cas/v1/tickets" in str(req.url):
            return httpx.Response(201, text="TGT-sahte")
        kayit.append(req.url.path)
        return httpx.Response(200, json={"items": []})
    c = epias.Istemci(kullanici="u", sifre="p", transport=httpx.MockTransport(h))
    with pytest.raises(ValueError, match=r"30\.04\.2016"):
        c.ham("yek_dengesizlik", "2026-11-01", "2026-11-02")
    assert kayit == []                                                             # veri ucu hiç çağrılmadı


# ---- T-05 / T-06: sicil metinleri (hesap değişmez; sha16 dinamik)
def test_t05_t06_sicil_metinleri():
    assert "01.11.2026 12:00" in ks.V100_DAYANAK and "94,00" in ks.V100_DAYANAK
    assert "hukuki dayanağı olmayan varsayım" in kr.BELIRSIZ_2027_GEREKCE and "14.11.2026" in kr.BELIRSIZ_2027_GEREKCE
    assert kr.BELIRSIZ_2027_GEREKCE is ks.BELIRSIZ_2027_GEREKCE
    v100 = next(k for k in ks.SICIL if k.surum == "V100"); assert v100.dogrulama == "cikarim"   # durum değişmedi
    assert len(ks.sicil_sha16()) == 16


# ---- T-29 (AK-0248): LÜY istisna notu yalnız istisnanın uygulandığı saatlerde (Karar 14907 Md.5, 1.11.2026'dan)
def test_t29_luy_istisna_notu_kosullu():
    from pvquant.services import dengesizlik_service as ds
    from pvquant.services import finansal_etki_service as fe
    from test_finansal_etki_v2580 import _df, _fiyat, _izgara
    def _g(kod):
        dn, iz = _izgara(kod); pj = {"segment": "lisanssiz_iletim"}
        return {"donem": dn, "izgara": iz, "df": _df(iz), "fiyat": _fiyat(iz), "kat": ds.katsayilar(pj), "segment": "lisanssiz_iletim", "ariza_sayisi": 0,
                "luy_istisna": True, "bildirilen": None, "pozisyon": {"kaynak": "program", "sabit_mwh": None}, "pj": pj, "uretim": "scada", "pencere_gun": 45}
    def _not(kod):
        g = _g(kod); pv, fo = fe.saatlik(g)
        out = fe.uzlastirma_bilesenleri_saf(g["donem"], g["izgara"], pv, fo, ds.segment_bilgisi(g["pj"]), g["kat"], True, None, fe.dayanaklar(g["donem"], "lisanssiz_iletim", luy_istisna=True))
        k = next(b for b in out["bilesenler"] if b["kod"] == "kupst")
        return k, " ".join(k.get("notlar") or [])
    _, n_eki = _not("2026-10")                     # Ekim 2026: 14907 henüz yok → istisna uygulanamaz
    assert "sapma tutarı 0." not in n_eki and "uygulanabilir saat yok" in n_eki
    _, n_kas = _not("2026-11")                     # Kasım 2026: istisna bütün saatlerde → tutar 0 notu
    assert "sapma tutarı 0." in n_kas
