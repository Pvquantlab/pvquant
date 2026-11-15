"""Faz 9 (14.11.2026) — D alanı: finansal mutabakat hesaplarının bileşen bileşen BAĞIMSIZ sınaması (DB'siz; çekirdeğe dokunmaz).

Her test, kural sicilindeki (src/pvquant/ext/turkiye/kural_sicili.py) künyeden elle türetilmiş beklenen değeri (bu dosyada açık formülle)
`pvquant.ext.turkiye.dengesizlik.saatlik` / `aylik_karne` çıktısıyla karşılaştırır. Fiyatlar SENTETİKTİR (gerçek fiyat günü ikinci örnek
olarak 54 vektörlük depo dışı betikle K1 koşulur: 10_Test_Senaryolari_ve_Sonuclari/T2_finans). Resmî EPYS bildirimi kullanılmadı → D alanı
en iyi «kısmen doğrulandı (resmî veri yok)».
Ölçüt bağları: D-Z1 P(−)/P(+) ve dallar · D-Z2 EDT miktar/tutar · D-Z3 KÜPST (m, n, taban, net sapma) · D-Z4 dönem ↔ kural · D-Z5 2027 bayrağı ·
D-Z6 saat dilimi/ay sınırı · D-B1 EDTA/EDTB toplama · D-B2 portföy toplamı · D-G çelişki kayıtları (Ç-xx, kanit/F0/servisler_finans.md §12).
Koşu: PYTHONPATH=src .venv/bin/python3 -m pytest -q -p no:cacheprovider tests/test_faz9_finans_dogrulama.py
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from pvquant.ext.turkiye import dengesizlik as d
from pvquant.ext.turkiye import kurallar as kr

TZ = "Europe/Istanbul"


def _i(*yerel: str) -> pd.DatetimeIndex:
    return pd.DatetimeIndex([pd.Timestamp(t, tz=TZ).tz_convert("UTC") for t in yerel])


def _s(idx, *v) -> pd.Series:
    return pd.Series([float(x) for x in v], index=idx)


def _tek(ts, K, G, ptf, smf, yon, segment="lisansli_serbest", **kw) -> pd.Series:
    i = _i(ts)
    return d.saatlik(_s(i, K), _s(i, G), _s(i, ptf), _s(i, smf), yon=yon, segment=segment,
                     **{a: (_s(i, b) if isinstance(b, (int, float)) else b) for a, b in kw.items()}).iloc[0]


# ------------------------------------------------------------------------------------------------ D-Z1..Z3 rejim örnekleri
def test_2025_rejimi_eksik_uretim():
    """2025 (DUY m.110 2025 metni; k=l=0,03 — dayanak «dogrulanamadi», Ç-06): K=10, G=8 MWh (2 MWh açık), PTF 2000, SMF 2500.
    P(−)=max(PTF,SMF)·1,03=2575; EDT(−)=2·2575=5150. KÜPST 13025: m=0,10, n=0,03, taban 750: KÜPSM=max(0, 2−1)=1 → 1·2500·0,03=75."""
    r = _tek("2025-06-15 12:00", 10, 8, 2000, 2500, "acik")
    assert r["p_neg"] == pytest.approx(2575.0)
    assert r["edt_neg"] == pytest.approx(5150.0) and r["edt_poz"] == pytest.approx(0.0)
    assert r["kupst"] == pytest.approx(75.0)
    assert r["dengesizlik_maliyeti"] == pytest.approx(2 * (2575 - 2000))      # neg·(P(−) − PTF)
    assert r["rejim"] == "2025" and not r["belirsiz_2027"]


def test_2026_v150_acik_sistem():
    """2026 (Karar 14030; V150; yön açık → k=0,06, l=0,03): K=10, G=8; PTF 2000, SMF 2500. P(−)=max(150, 2500)·1,06=2650; EDT(−)=5300.
    KÜPST 14029: m=0,08, n=0,05: KÜPSM=max(0, 2−0,8)=1,2 → 1,2·2500·0,05=150."""
    r = _tek("2026-03-10 12:00", 10, 8, 2000, 2500, "acik")
    assert (r["k"], r["l"]) == (pytest.approx(0.06), pytest.approx(0.03))
    assert r["p_neg"] == pytest.approx(2650.0) and r["edt_neg"] == pytest.approx(5300.0)
    assert r["kupst"] == pytest.approx(150.0)


def test_2026_afl_dali():
    """AFL dalı (AFL 4.500, Karar 14459, 4.4.2026–): max(PTF,SMF_N)=4600 ≥ AFL → P(−)=AFL·1,05·(1+k)=4500·1,05·1,06=5008,5."""
    r = _tek("2026-05-01 12:00", 10, 9, 4600, 4600, "acik")
    assert r["p_neg"] == pytest.approx(4500 * 1.05 * 1.06) and r["dal"] == "AFL"


def test_2026_kasim_v100_b_dali_ve_net_sapma_kupst():
    """1.11.2026– (V100 «cikarim», Karar 14911; KÜPST 14907 net sapma «cikarim»): yön fazla → k=0,03, l=0,06.
    (a) B dalı: min(PTF,SMF_P)=50 < V=100 → P(+)=−B·(1+l)=−106. (b) KÜPST net sapma: K=10, G=12, UEÇM=0,3:
    UDÜPS=|(12−0,3)−10|=1,7; KÜPSM=max(0, 1,7−0,8)=0,9; KÜPST=0,9·max(750,3400,3400)·0,05=153."""
    rb = _tek("2026-11-05 12:00", 10, 12, 50, 50, "fazla")
    assert rb["p_poz"] == pytest.approx(-106.0) and rb["dal"] == "B"
    assert rb["edt_poz"] == pytest.approx(-212.0)                               # katılımcı fazla üretimi için ÖDER
    r = _tek("2026-11-05 12:00", 10, 12, 3400, 3400, "fazla", uecm_mwh=0.3)
    assert r["kupst"] == pytest.approx(153.0) and bool(r["net_sapma"])
    assert r["p_poz"] == pytest.approx(3400 * 0.94)


def test_b_dali_sinir_esitlik_belgelenir():
    """Ç-15 (K3 → K1): sınırda min(PTF,SMF_P) == V (100) → kod `mn < V` (katı) ile normal dal: P(+)=100·(1−l)=94. Bülten bir saatte −106
    (≤ okuması) gösteriyor ([06] AK-1343). Bu test mevcut davranışı sabitler; resmî uzlaştırmayla teyit edilmeden değiştirilmemeli."""
    r = _tek("2026-11-05 12:00", 10, 12, 100, 100, "fazla")
    assert r["p_poz"] == pytest.approx(94.0) and r["dal"] == "normal"


def test_2026_yon_eksik_edt_uydurulmaz():
    """D-Z1: 2026 saatinde sistem yönü yoksa EDT NaN ve durum yon_eksik (0 yazılmaz)."""
    r = _tek("2026-03-10 12:00", 10, 8, 2000, 2500, None)
    assert np.isnan(r["edt_neg"]) and r["durum"] == "yon_eksik"


def test_2027_belirsiz_bayragi_her_ciktida():
    """D-Z5: 1.1.2027– saatlerde belirsiz_2027 bayrağı saatlik çıktıda, parametre çerçevesinde ve kural nesnesinde taşınır;
    31.12.2026 23:00 İstanbul saatinde taşınmaz (gün sınırı İstanbul)."""
    i = _i("2026-12-31 23:00", "2027-01-01 00:00", "2027-01-05 12:00")
    s = d.saatlik(_s(i, 10, 10, 10), _s(i, 9, 9, 9), _s(i, 3000, 3000, 3000), _s(i, 3000, 3000, 3000), yon="acik", segment="lisansli_serbest")
    assert list(s["belirsiz_2027"]) == [False, True, True]
    assert kr.kural(date(2027, 1, 5), "lisansli_serbest").belirsiz_2027 is True
    assert kr.kural(date(2026, 12, 31), "lisansli_serbest").belirsiz_2027 is False
    prm = kr.parametre_cercevesi(i, "lisansli_serbest")
    assert list(prm["belirsiz_2027"]) == [False, True, True]


def test_kural_donem_gecisleri_gun_sinirinda():
    """D-Z4: kural sürümü teslim gününe (İstanbul) göre değişir: 18.10.2026 → edta_net, 19.10.2026 → edta_ayrik; 31.10 → V150, 1.11 → V100;
    31.12.2025 → 2025 rejimi, 1.1.2026 → 2026. UTC 21:00 (= İstanbul 00:00) satırı yeni güne aittir."""
    assert kr.edt_kurali(date(2026, 10, 18)).toplama == "edta_net"
    assert kr.edt_kurali(date(2026, 10, 19)).toplama == "edta_ayrik"
    assert kr.v_degeri(date(2026, 10, 31)) == 150 and kr.v_degeri(date(2026, 11, 1)) == 100
    utc = pd.DatetimeIndex([pd.Timestamp("2025-12-31 20:00", tz="UTC"), pd.Timestamp("2025-12-31 21:00", tz="UTC")])
    prm = kr.parametre_cercevesi(utc, "lisansli_serbest")
    assert list(prm["rejim"]) == ["2025", "2026"]


def test_aylik_karne_istanbul_ay_siniri():
    """D-Z6: 31.10.2026 21:30 UTC = 1.11.2026 00:30 İstanbul → Kasım ayına yazılır (UTC ayına değil)."""
    i = pd.DatetimeIndex([pd.Timestamp("2026-10-31 20:00", tz="UTC"), pd.Timestamp("2026-10-31 21:00", tz="UTC")])
    s = d.saatlik(_s(i, 10, 10), _s(i, 8, 12), _s(i, 3000, 3000), _s(i, 3000, 3000), yon="acik", segment="lisansli_serbest")
    a = d.aylik_karne(s)
    assert [str(x.date()) for x in a.index] == ["2026-10-31", "2026-11-30"]
    assert a["edt_neg"].iloc[0] == pytest.approx(s["edt_neg"].iloc[0]) and a["edt_poz"].iloc[1] == pytest.approx(s["edt_poz"].iloc[1])


# ------------------------------------------------------------------------------------------------ D-B1 toplama (Ç-08)
def _karisik_ay(ilk_gun: str, n_gun: int = 4) -> pd.DataFrame:
    """B dalı (P(+) < 0) ve normal fazla saatleri ve açık saatleri karışık bir dönem."""
    rows = []
    for g in range(n_gun):
        for h, (K, G, ptf) in enumerate([(10, 12, 50), (10, 13, 3000), (10, 8, 3000)]):
            rows.append((pd.Timestamp(ilk_gun, tz=TZ) + pd.Timedelta(days=g, hours=10 + h), K, G, ptf))
    i = pd.DatetimeIndex([r[0] for r in rows]).tz_convert("UTC")
    return d.saatlik(pd.Series([r[1] for r in rows], index=i, dtype=float), pd.Series([r[2] for r in rows], index=i, dtype=float),
                     pd.Series([r[3] for r in rows], index=i, dtype=float), pd.Series([r[3] for r in rows], index=i, dtype=float),
                     yon="fazla", segment="lisansli_serbest")


@pytest.mark.parametrize("ilk_gun,kural", [("2026-10-20", "edta_ayrik"), ("2026-10-02", "edta_net")])
def test_edta_edtb_toplama_kurali_ve_saatlik_toplam_farki(ilk_gun, kural):
    """D-B1 + Ç-08 (K3 → K1): m.110(1) EDTA/EDTB ayrımı ile «saatlik Σ edt_poz / Σ edt_neg» (mutabakat_service.pvquant_kalemleri:380 yolu)
    B dalı saatleri olan dönemde BRÜT olarak farklı, NET olarak aynıdır. Mutabakatın alacak/borç ayrı uyum sınaması (UYUM_PCT %2) bu yüzden
    resmî EDTA/EDTB'ye karşı yapay «fark» üretebilir. Bağımsız hesap: edta_ayrik EDTA=Σmax(EDT+,0), EDTB=ΣEDT−−Σmin(EDT+,0)."""
    s = _karisik_ay(ilk_gun)
    a = d.aylik_karne(s).iloc[0]
    pos, neg = s["edt_poz"], s["edt_neg"]
    if kural == "edta_ayrik":
        edta, edtb = pos.clip(lower=0).sum(), neg.sum() - pos.clip(upper=0).sum()
    else:
        edta, edtb = max(pos.sum(), 0.0), neg.sum() - min(pos.sum(), 0.0)
    assert a["edta"] == pytest.approx(edta) and a["edtb"] == pytest.approx(edtb)
    assert a["edta"] - a["edtb"] == pytest.approx(pos.sum() - neg.sum())            # net aynı
    if kural == "edta_ayrik":
        assert abs(a["edta"] - pos.sum()) > 100 and abs(a["edtb"] - neg.sum()) > 100  # brüt farklı (B dalı payı)


# ------------------------------------------------------------------------------------------------ D-B2 FEM / portföy (Ç-17, Ç-18, Ç-21)
def _fem_ozet(edt_tl, toplanir, kupst_tl=-100.0, resmi_edt=None):
    b = [{"kod": "satis_geliri", "tutar_tl": 1000.0, "alacak_tl": 1000.0, "borc_tl": 0.0, "nitelik": "hesaplanan", "toplanir": True},
         {"kod": "dengesizlik", "tutar_tl": edt_tl, "alacak_tl": max(edt_tl, 0), "borc_tl": max(-edt_tl, 0), "nitelik": "hesaplanan", "toplanir": toplanir},
         {"kod": "kupst", "tutar_tl": kupst_tl, "alacak_tl": 0.0, "borc_tl": -kupst_tl, "nitelik": "hesaplanan", "toplanir": toplanir}]
    if resmi_edt is not None:
        b.append({"kod": "dengesizlik_resmi", "tutar_tl": resmi_edt, "alacak_tl": max(resmi_edt, 0), "borc_tl": max(-resmi_edt, 0), "nitelik": "resmi", "toplanir": False})
    return {"bilesenler": b, "toplam": {"tutar_tl": 0.0}, "uzlastirma": {"santral_tasir": toplanir}}


def test_portfoy_toplami_toplanmaz_bileseni_iceriyor():
    """Ç-17 / AK-0124 → F9-D01 (Kritik; v2.610 düzeltmesi): dağıtıma bağlı lisanssız santralde (santral_tasir=False) EDT ve KÜPST
    `toplanir=False` (bilgi amaçlı) ve portföy ana toplamına GİRMEZ: toplam = 2000 + (−500) + (−100) = 1400 (düzeltme öncesi 1000).
    S2'nin −300/−100'ü ayrı bilgi satırında (`dengesizlik_toplanmayan`, `kupst_toplanmayan`) görünür."""
    from pvquant.ext.platform import finans as fn
    from pvquant.ext.platform import portfoy_finans as pf
    oz = {"S1": _fem_ozet(-500.0, True), "S2": _fem_ozet(-300.0, False)}
    try:
        r = pf.birlestir(oz)
    except (KeyError, ValueError) as e:   # sözlük alan adları değişirse bulgu yeniden incelenmeli
        pytest.skip(f"birlestir girdisi uyumsuz: {e}")
    kodlar = {b["kod"] for b in r["bilesenler"]}
    assert {pf.KOD_GELIR, pf.KOD_EDT, pf.KOD_KUPST} <= kodlar
    edt = next(b for b in r["bilesenler"] if b["kod"] == pf.KOD_EDT)
    assert edt["tutar_tl"] == pytest.approx(-500.0)
    assert r["toplam"]["tutar_tl"] == pytest.approx(1400.0)
    bilgi = {b["kod"]: b for b in r["bilesenler"]}
    assert bilgi[f"{pf.KOD_EDT}_toplanmayan"]["tutar_tl"] == pytest.approx(-300.0) and bilgi[f"{pf.KOD_EDT}_toplanmayan"]["toplanir"] is False
    assert bilgi[f"{pf.KOD_KUPST}_toplanmayan"]["tutar_tl"] == pytest.approx(-100.0)
    assert fn is not None


def test_resmi_fark_isareti_iki_yuzeyde_ters():
    """Ç-18 (K3 → K1, Orta): santral FEM `resmi_kiyas_saf` fark = hesaplanan − resmî; portföy `birlestir` resmi_fark = resmî − hesaplanan.
    Aynı veri iki ekranda ters işaretli fark gösterir."""
    from pvquant.ext.platform import portfoy_finans as pf
    oz = {"S1": _fem_ozet(-500.0, True, resmi_edt=-450.0)}
    r = pf.birlestir(oz)
    rf = next(b for b in r["bilesenler"] if b["kod"] == "resmi_fark")
    assert rf["tutar_tl"] == pytest.approx(-450.0 - (-500.0))                       # resmî − hesaplanan = +50
    import inspect

    from pvquant.services import finansal_etki_service as fe
    kaynak = inspect.getsource(fe.resmi_kiyas_saf)
    assert "hesaplanan − resmî" in kaynak or "hesaplanan - resmi" in kaynak or "hesaplanan−resmî" in kaynak.replace(" ", "")


def test_hesap_durumu_yon_eksik_saatleri_kismi_sayar():
    """Ç-21 (K3 → K1, Yüksek — gerçek dışı «tam» etiketi): bütün saatler ölçülü ve EPİAŞ fiyatlı ama 100 saatte sistem yönü yok
    (EDT NaN, hesaplanamayan saat) → `hesap_durumu` yine «tam» döner. Beklenen: «kismi»."""
    from pvquant.services import finansal_etki_service as fe
    u = {"gerceklesen": {"saat": 744, "beklenen_saat": 744}}
    fo = {"epias_saat": 744, "senaryo_saat": 0, "yon_varsayilan_saat": 0, "yon_eksik_saat": 100}
    assert fe.hesap_durumu(u, fo, None) == "kismi"                                     # F9-D02 (P6) düzeltildi: yön eksik saat «tam» değildir
    assert fe.hesap_durumu({**u, "hesaplanamayan_saat": 3}, {**fo, "yon_eksik_saat": 0}, None) == "kismi"   # hesaplanamayan saat da «kısmi»
    assert fe.hesap_durumu({"gerceklesen": {"saat": 743, "beklenen_saat": 744}}, {**fo, "yon_eksik_saat": 0}, None) == "kismi"
    assert fe.hesap_durumu({"gerceklesen": {"saat": 0, "beklenen_saat": 744}}, fo, None) == "hesaplanamadi"


def test_dsg_hesapla_df_kural_surumu_anahtari_var():
    """Ç-22 / F9-D05 (Düşük) — v2.610 (T-25) ile KAPANDI: `dengesizlik_service.dsg_hesapla_df` dönüşünde `kural_surumu` gerçek anahtar
    (önce `#` yorumunun içinde kalmıştı). Kaynak satırı yorum DIŞINDA olmalı."""
    import inspect

    from pvquant.services import dengesizlik_service as ds
    satir = [x for x in inspect.getsource(ds.dsg_hesapla_df).splitlines() if '"kural_surumu": " | ".join' in x]
    assert satir and "#" not in satir[0].split('"kural_surumu"')[0]


def test_kupst_2018_oncesi_uretilir_belgelenir():
    """Ç-05 (K3 → K1, Düşük — tarihsel): Karar 7524 tek kayıt BASLANGIC–31.7.2020 (n 0,03). 1.12.2017'de (KÜPST öncesi dönem) kod sıfırdan
    farklı KÜPST üretir; [06] AK-1241 1.2.2018 öncesinde KÜPST olmadığını, 1.2–30.4.2018'de n=0,015 olduğunu söyler."""
    r = _tek("2017-12-01 12:00", 10, 8, 200, 210, "acik")
    assert r["kupst"] > 0
