import numpy as np, pandas as pd, pytest, httpx
from pvquant.ext.turkiye import dengesizlik as d, epias, kgup, segment

IST = "Europe/Istanbul"


def _ay(seed=0, hata=0.1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-07-01", "2025-07-31 23:00", freq="h", tz=IST).tz_convert("UTC")
    g = np.clip(np.sin((idx.tz_convert(IST).hour - 6) / 12 * np.pi), 0, None)
    gercek = pd.Series(10 * g * rng.uniform(0.5, 1.0, len(idx)), index=idx)
    prog = gercek * (1 + rng.normal(0, hata, len(idx)))
    ptf = pd.Series(2650.0, index=idx); smf = pd.Series(2500.0, index=idx)
    return idx, gercek, prog, ptf, smf


def test_duy_formulu_isaretleri():
    idx, gercek, _, ptf, smf = _ay()
    kg = gercek.copy(); kg.iloc[12] += 1.0; kg.iloc[13] -= 1.0        # saat 12: 1 MWh eksik üretim; saat 13: 1 MWh fazla
    s = d.saatlik(kg, gercek, ptf, smf)
    assert s.dengesizlik_maliyeti.iloc[12] == pytest.approx(2650 * 1.03 - 2650)   # negatif: max(PTF,SMF)·1,03 − PTF
    assert s.dengesizlik_maliyeti.iloc[13] == pytest.approx(2650 - 2500 * 0.97)   # pozitif: PTF − min·0,97
    assert s.dengesizlik_maliyeti.drop(s.index[[12, 13]]).abs().max() < 1e-9
    assert s.kupst.isna().all() and (s.durum == "kupst_hesaplanamaz").all()     # segment yok → KÜPST 0 DEĞİL, hesaplanamaz
    k2 = d.Katsayilar(kupst_n=0.03, kupst_tolerans=0.0)
    s2 = d.saatlik(kg, gercek, ptf, smf, k2); assert s2.kupst.iloc[12] == pytest.approx(2650 * 0.03) and s2.kupst.iloc[0] == 0


def test_karne_ve_kiyas_kurtarir():
    idx, gercek, pvq, ptf, smf = _ay(hata=0.08)
    naif = gercek.shift(24).fillna(gercek.mean())
    k = d.kiyas(naif, pvq, gercek, ptf, smf, segment="lisansli_serbest")      # 2025 Temmuz → 2025 rejimi, KÜPST 13025
    assert len(k) == 1 and k.kurtarilan_tl.iloc[0] > 0 and 0 < k.kurtarilan_oran.iloc[0] < 1
    a = d.aylik_karne(d.saatlik(pvq, gercek, ptf, smf, segment="lisansli_serbest")); assert 0 < a.maliyet_gelir_orani.iloc[0] < 0.05
    assert d.teminat(d.saatlik(pvq, gercek, ptf, smf, segment="lisansli_serbest")) > 0


def test_dsg_netlesme_maliyeti_dusurur():
    idx, g1, p1, ptf, smf = _ay(seed=1); _, g2, p2, _, _ = _ay(seed=2)
    # GÖSTERGE: yalnız EDT (dengesizlik_maliyeti); KÜPST netleşmez ve %5 eşik uygulanmaz (F-08 sonraki paket)
    ayri = d.saatlik(p1, g1, ptf, smf).dengesizlik_maliyeti.sum() + d.saatlik(p2, g2, ptf, smf).dengesizlik_maliyeti.sum()
    K, G = d.dsg_netlestir({"a": p1, "b": p2}, {"a": g1, "b": g2})
    assert d.saatlik(K, G, ptf, smf).dengesizlik_maliyeti.sum() < ayri


def test_optimal_kantil_ve_spread():
    tau = d.optimal_teklif_kantili(2650, 3400, 2500)          # açık pahalı → daha düşük program → τ < 0,5
    assert 0.05 <= tau < 0.5
    assert d.optimal_teklif_kantili(2650, 2650, 2650) == pytest.approx(0.5, abs=0.01)
    ptf = pd.Series(1000.0, index=pd.date_range("2025-01-01", periods=1000, freq="h", tz="UTC"))
    s = d.senaryo_spread(ptf, 0.2); assert set(np.round(s.unique())) == {800, 1200}


def test_segment_kurallari_ve_gelir():
    idx, gercek, _, ptf, _ = _ay()
    st = segment.Santral("A", segment.Segment.LISANSSIZ_DAGITIM, 1.0, yekdem_fiyat_tl_mwh=3684.0)
    assert not st.kgup_gerekli_mi() and not st.dengesizlik_tasir_mi()
    assert segment.dengesizlik_paylastir(st, pd.Series(100.0, index=idx)).sum() == 0
    g = segment.gelir(st, gercek); assert g.gelir_tl.sum() == pytest.approx(gercek.sum() * 3684)
    sb = segment.Santral("B", segment.Segment.LISANSLI_SERBEST, 10.0)
    assert sb.kgup_gerekli_mi() and segment.gelir(sb, gercek, ptf).gelir_tl.sum() == pytest.approx((gercek * ptf).sum())
    oz = segment.Santral("C", segment.Segment.OZ_TUKETIM_SAATLIK, 0.5)
    tuk = pd.Series(0.2, index=idx)
    r = segment.gelir(oz, gercek / 20, tuketim_mwh=tuk, gts_fiyat_tl_mwh=2000, tarife_tl_mwh=4000)
    assert (r.net_mwh == gercek / 20 - 0.2).all() and r.gelir_tl.sum() > 0
    y = segment.Santral("D", segment.Segment.LISANSLI_YEKDEM, 5.0, yekdem_fiyat_tl_mwh=3684.0, yekdem_dengesizlik_payi=0.5)
    assert segment.dengesizlik_paylastir(y, pd.Series(100.0, index=idx)).iloc[0] == 50.0


def test_epias_sahte_tasiyici_ve_utc():
    items = [{"date": "2025-07-01T00:00:00+03:00", "price": 2600.0}, {"date": "2025-07-01T01:00:00+03:00", "price": 2700.0}]
    c = epias.Istemci("u", "p", transport=epias.sahte_tasiyici({"/v1/markets/dam/data/mcp": items}))
    s = c.ptf("2025-07-01", "2025-07-01")
    assert c.tgt() == "TGT-TEST" and str(s.index.tz) == "UTC" and s.index[0] == pd.Timestamp("2025-06-30 21:00", tz="UTC") and s.iloc[1] == 2700.0
    a = epias.gerceklesen_adaptoru(pd.Series([5.0, 12.0, -1.0], index=s.index.append(pd.DatetimeIndex([s.index[-1] + pd.Timedelta(hours=1)]))), 10.0)
    assert list(a.bayrak) == ["", "tavan_asimi", "negatif"]


def test_epias_onbellek(tmp_path):
    items = [{"date": "2025-07-01T00:00:00+03:00", "price": 2600.0}]
    sayac = {"n": 0}
    def handler(req):
        if req.url.path.endswith("/cas/v1/tickets"): return httpx.Response(201, text="T")
        sayac["n"] += 1; return httpx.Response(200, json={"items": items})
    c = epias.Istemci("u", "p", onbellek_dizin=tmp_path, transport=httpx.MockTransport(handler))
    c.ptf("2025-07-01", "2025-07-01"); c.ptf("2025-07-01", "2025-07-01")
    assert sayac["n"] == 1


def test_kgup_program_ve_dosya(tmp_path):
    idx, gercek, pvq, _, _ = _ay()
    son = kgup.program_uret(pvq, "2025-07-15", "UEVCB-1", 10.0, eak_mw=9.0, bakim_saatleri=[3])
    assert kgup.dogrula(son, 10.0) == [] and len(son.tablo) == 24 and son.tablo.kgup_mwh.max() <= 9.0 and son.tablo.kgup_mwh.iloc[3] == 0
    buyuk = pvq * 60                                                     # 600 MW: sıçramalar ≥200 MWh
    s2 = kgup.program_uret(buyuk, "2025-07-15", "UEVCB-2", 600.0); assert len(s2.sicrama_saatleri) >= 1
    c = kgup.ceyrek_dilimle(s2); assert len(c) == 24 + 3 * len(s2.sicrama_saatleri)
    yol = kgup.tpys_csv(c, tmp_path / "kgup.csv"); metin = yol.read_text(encoding="utf-8")
    assert metin.splitlines()[0] == "Saat,Miktar,Ceyrek" and metin.splitlines()[1].startswith("00:00,")   # v2.512: TPYS KGUP.csv biçimi
    assert not yol.read_bytes().startswith(b"\xef\xbb\xbf") and yol.read_bytes() == kgup.csv_baytlari(c)   # BOM yok, SHA bu baytlarla
    # çeyrek satırlarda EAK bölünmez (güç), KGÜP çeyreğe bölünür
    sic = s2.sicrama_saatleri[0]; q = c[(c["saat"] == sic) & c["ceyrek"].notna()]
    assert len(q) == 4 and (q["eak_mw"] == s2.tablo.loc[s2.tablo["saat"] == sic, "eak_mw"].iloc[0]).all()
    # eksik saat: 0 yazılmaz, eksik listesi döner
    eksik = kgup.program_uret(pvq.iloc[:-30], "2025-07-31", "UEVCB-3", 10.0)
    assert eksik.eksik_saatler and "dosya üretilmez" in eksik.uyarilar[0]


def test_teslim_ve_revizyon():
    assert kgup.teslim_durumu(pd.Timestamp("2025-07-14 15:05", tz=IST))["durum"] == "pencere_acik"
    assert kgup.teslim_durumu(pd.Timestamp("2025-07-14 16:00", tz=IST))["durum"] == "gecikti"
    e = kgup.teslim_durumu(pd.Timestamp("2025-07-14 09:00", tz=IST)); assert e["durum"] == "erken" and e["hedef_gun"] == "2025-07-15"
    r = kgup.gun_ici_revizyon_penceresi(pd.Timestamp("2025-07-15 13:00", tz=IST))
    assert r["kgup_revizyon_son"] == pd.Timestamp("2025-07-15 12:30", tz=IST)
