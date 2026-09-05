import numpy as np, pandas as pd, pytest
from datetime import datetime, timedelta, timezone
from pvquant.ext.platform import alarm, api_anahtar, paylasim, portfoy, rapor_sablon, tarife, tazeleme


def _p():
    idx = pd.date_range("2025-07-01", periods=24 * 10, freq="h", tz="UTC"); rng = np.random.default_rng(0)
    g = np.clip(np.sin((idx.hour + 3 - 6) / 12 * np.pi), 0, None)
    P = portfoy.Portfoy({f"S{i}": portfoy.SantralKaydi(f"S{i}", f"Santral {i}", 5.0 * i, "Konya" if i < 3 else "Adana") for i in (1, 2, 3)})
    ger = {k: pd.Series(s.kurulu_guc_mw * g * rng.uniform(0.5, 1, len(idx)), index=idx) for k, s in P.santraller.items()}
    return idx, g, P, ger


def test_portfoy_toplama_ve_kpi():
    idx, g, P, ger = _p()
    t = portfoy.topla(ger); assert np.allclose(t, sum(ger.values()))
    ger2 = dict(ger); ger2["S2"] = ger2["S2"].copy(); ger2["S2"].iloc[5] = np.nan
    assert np.isnan(portfoy.topla(ger2).iloc[5]) and portfoy.eksik_haritasi(ger2).loc[:, "S2"].iloc[0] > 0
    assert P.kapasite() == 30 and P.gruplar()["Konya"] == ["S1", "S2"]
    k = portfoy.agirlikli_kpi({"S1": {"wmape": 0.10}, "S3": {"wmape": 0.05}}, P)
    assert k.wmape == pytest.approx((0.10 * 5 + 0.05 * 15) / 20) and k.kapsanan_kapasite_mw == 20
    oz = portfoy.gunluk_ozet(ger, ger, P); assert (oz.sapma_mwh.abs() < 1e-9).all() and 0 < oz.kapasite_faktoru.mean() < 1
    al = pd.DataFrame([{"plant_id": "S1", "severity": "kritik", "rule": "x", "acknowledged": False}, {"plant_id": "S1", "severity": "uyari", "rule": "y", "acknowledged": True}])
    o = portfoy.alarm_ozeti(al, P); assert o.set_index("id").loc["S1", "acik"] == 1 and o.set_index("id").loc["S2", "acik"] == 0


def test_tazeleme_etag_ve_politika():
    d = tazeleme.DegisimDamgasi(); sayac = {"n": 0}
    def uret(): sayac["n"] += 1; return {"v": sayac["n"]}
    kod, b, g = tazeleme.kosullu_yanit(d, "a", None, uret); assert kod == 200 and sayac["n"] == 1
    kod2, b2, g2 = tazeleme.kosullu_yanit(d, "a", b["ETag"], uret); assert kod2 == 304 and g2 is None and sayac["n"] == 1
    d.guncelle("a", "yeni"); kod3, _, _ = tazeleme.kosullu_yanit(d, "a", b["ETag"], uret); assert kod3 == 200 and sayac["n"] == 2
    p = tazeleme.YoklamaPolitikasi(); assert p.sonraki_sn(True) == 60 and p.sonraki_sn(False) == 300
    assert p.sonraki_sn(True, hata=True) == 30 and p.sonraki_sn(True, hata=True) == 60 and p.sonraki_sn(True) == 60
    olaylar = []
    gen = tazeleme.sse_akisi(d, ["a"], {}, bekleme_sn=0, azami_sn=0.5, uyku=lambda s: None)
    olaylar.append(next(gen)); assert olaylar[0].startswith("event: degisti")
    assert "useTazeleme" in tazeleme.USE_TAZELEME_JS


def test_alarm_motoru_histerezis_eskalasyon():
    m = alarm.AlarmMotoru()                                     # varsayılan: 2 kural
    t0 = datetime(2025, 7, 1, tzinfo=timezone.utc)
    yeni = m.tara("S1", {"son_scada_saat_once": 60, "skill_7g": -0.2, "pr_30g": 0.5}, t0)
    assert {a.kural for a in yeni} == {"veri_gelmedi", "skill_dustu"}   # pr_dustu kapalı
    assert m.tara("S1", {"son_scada_saat_once": 61, "skill_7g": -0.2}, t0 + timedelta(hours=1)) == []   # tekrar üretmez
    m.tara("S1", {"son_scada_saat_once": 62, "skill_7g": 0.02}, t0 + timedelta(hours=2))                  # skill 0,02 < 0,05 → kapanmaz (histerezis)
    assert len(m.acik_liste("S1")) == 2
    m.tara("S1", {"son_scada_saat_once": 62, "skill_7g": 0.10}, t0 + timedelta(hours=3)); assert len(m.acik_liste("S1")) == 1
    m.tara("S1", {"son_scada_saat_once": 70, "skill_7g": 0.10}, t0 + timedelta(hours=30))
    a = m.acik_liste("S1")[0]; assert a.eskale and a.siddet == "kritik"
    m.okundu(a.id, "ops"); m.ata(a.id, "saha"); assert a.durum == "atandi" and a.okuyan == "ops"
    m.kapat(a.id); assert m.acik_liste("S1") == []
    m2 = alarm.AlarmMotoru(alarm.Ayar(acik_kurallar=tuple(alarm.KUTUPHANE)))
    assert len(m2.tara("S2", {"son_ping_dk_once": 90, "kgup_gecikti": True, "clipping_orani_7g": 0.3}, t0)) == 3


def test_api_anahtar_dogrulama_oran_webhook():
    depo = api_anahtar.Depo(); duz, k = api_anahtar.uret(depo, "T1", {"tahmin:oku"})
    assert duz.startswith("pvq_") and api_anahtar.dogrula(depo, duz, "tahmin:oku").tenant_id == "T1"
    with pytest.raises(PermissionError): api_anahtar.dogrula(depo, duz, "santral:yaz")
    with pytest.raises(PermissionError): api_anahtar.dogrula(depo, duz[:-3] + "xyz")
    with pytest.raises(PermissionError): api_anahtar.dogrula(depo, "bozuk")
    yeni, k2 = api_anahtar.dondur(depo, k.prefix, grace_saat=1)
    assert api_anahtar.dogrula(depo, duz).prefix == k.prefix and api_anahtar.dogrula(depo, yeni).prefix == k2.prefix
    with pytest.raises(PermissionError): api_anahtar.dogrula(depo, duz, simdi=k.gecerlilik_sonu + 10)
    api_anahtar.iptal_et(depo, k2.prefix)
    with pytest.raises(PermissionError): api_anahtar.dogrula(depo, yeni)
    kova = api_anahtar.TokenBucket(3, 1.0); t = 1000.0
    assert all(kova.izin("p", t) for _ in range(3)) and kova.izin("p", t) is False and kova.izin("p", t + 1.0) is True
    b = api_anahtar.webhook_imzala("gizli", b'{"a":1}', 1000); assert api_anahtar.webhook_dogrula("gizli", b'{"a":1}', b, simdi=1100)
    assert not api_anahtar.webhook_dogrula("gizli", b'{"a":2}', b, simdi=1100) and not api_anahtar.webhook_dogrula("gizli", b'{"a":1}', b, simdi=2000)


def test_paylasim_politikasi():
    pol = paylasim.Politika(); admin = paylasim.Kullanici("u1", "A", "admin"); viewer_a = paylasim.Kullanici("u2", "A", "viewer")
    dsg = paylasim.Kullanici("u9", "DSG", "viewer"); t0 = datetime(2025, 7, 1, tzinfo=timezone.utc)
    assert pol.izin_var_mi(viewer_a, "tahmin:oku", "S1", "A") and not pol.izin_var_mi(viewer_a, "santral:yaz", "S1", "A")
    assert not pol.izin_var_mi(dsg, "tahmin:oku", "S1", "A", t0)
    with pytest.raises(PermissionError): pol.paylas(viewer_a, "DSG", "S1", {"tahmin:oku"})
    with pytest.raises(ValueError): pol.paylas(admin, "DSG", "S1", {"santral:yaz"})
    p = pol.paylas(admin, "DSG", "S1", {"tahmin:oku"}, bitis=t0 + timedelta(days=30), takma_ad="α", simdi=t0)
    assert pol.izin_var_mi(dsg, "tahmin:oku", "S1", "A", t0 + timedelta(days=1)) and not pol.izin_var_mi(dsg, "karne:oku", "S1", "A", t0 + timedelta(days=1))
    assert not pol.izin_var_mi(dsg, "tahmin:oku", "S1", "A", t0 + timedelta(days=31))
    assert pol.takma_ad(dsg, "S1", "Gerçek", t0 + timedelta(days=1)) == "α"
    pol.iptal_et(admin, p.id); assert not pol.izin_var_mi(dsg, "tahmin:oku", "S1", "A", t0 + timedelta(days=1))
    assert any(d["sonuc"] == "ret" for d in pol.denetim) and any(d["eylem"] == "paylas" for d in pol.denetim)


def test_tarife_yapilari():
    idx = pd.date_range("2025-07-01", periods=48, freq="h", tz="UTC"); uretim = pd.Series(1.0, index=idx)
    tou = tarife.CokZamanli(fiyatlar={"gunduz": 2400, "puant": 3300, "gece": 2000}); f = tou.fiyat(idx)
    ist = idx.tz_convert("Europe/Istanbul"); assert f[ist.hour == 18].iloc[0] == 3300 and f[ist.hour == 3].iloc[0] == 2000 and f[ist.hour == 10].iloc[0] == 2400
    with pytest.raises(ValueError): tarife.CokZamanli(dilimler={"a": (0, 12)}, fiyatlar={"a": 1}).dogrula()
    ptf = pd.Series(2650.0, index=idx); pe = tarife.PtfEndeksli(0.05, 50, tavan=2800); assert pe.fiyat(idx, ptf=ptf).iloc[0] == 2800
    y = tarife.Yekdem(7.0, 40.0); assert y.fiyat(idx).iloc[0] == pytest.approx(2800)
    es = tarife.Eskalasyon(0.10, 2025); idx26 = pd.date_range("2026-03-01", periods=2, freq="h", tz="UTC"); assert es.carpan(idx26).iloc[0] == pytest.approx(1.1)
    y1 = tarife.TarifeYapisi("ToU", tou, pd.Timestamp("2025-07-01", tz="UTC"), pd.Timestamp("2025-07-02", tz="UTC"))
    y2 = tarife.TarifeYapisi("PTF", pe, pd.Timestamp("2025-07-02", tz="UTC"))
    g = tarife.gelir(uretim, [y1, y2], ptf=ptf); assert set(g.tarife.unique()) == {"ToU", "PTF"} and g.gelir_tl.notna().all()
    with pytest.raises(ValueError): tarife.gelir(uretim, [y1, tarife.TarifeYapisi("X", tarife.Sabit(1), pd.Timestamp("2025-07-01", tz="UTC"))])
    assert len(tarife.aylik(g)) == 1


def test_rapor_sablonlari():
    idx, g, P, ger = _p()
    poa = pd.Series(950 * g, index=idx); ta = pd.Series(28.0 + 5 * g, index=idx); v = pd.Series(2.0, index=idx)
    guc = 5000 * poa / 1000 * (1 - 0.004 * (ta - 25))
    rp, s = rapor_sablon.kapasite_testi(guc, poa, ta, v, beklenen_fn=lambda rc: 5000 * rc["E"] / 1000 * (1 - 0.004 * (rc["T"] - 25)), santral="S1", donem="Tem 2025")
    assert 0.9 < s["oran"] < 1.05 and s["r2"] > 0.99 and "Kapasite testi" in rp.markdown() and "<h1>" in rp.html()
    rp2, ay = rapor_sablon.beklenen_gerceklesen(ger["S1"] * 1000, ger["S1"] * 950, santral="S1"); assert ay.loc["Toplam", "Fark (%)"] == pytest.approx(-5.0)
    rp3, f = rapor_sablon.fatura(ger["S1"], ger["S1"] * 2650, ger["S1"] * 50, kdv=0.2)
    ara = f[f.Kalem == "Ara toplam"]["Tutar (TL)"].iloc[0]; assert f[f.Kalem == "Genel toplam"]["Tutar (TL)"].iloc[0] == pytest.approx(ara * 1.2)
    rp4 = rapor_sablon.kullanilabilirlik_raporu({"A_t": 0.99, "saat_ariza": 5, "saat_haric": 2}, {"A_e": 0.985, "E_kayip_ariza_kwh": 100}, None, {"A_garanti": 0.98})
    assert "Kullanılabilirlik" in rp4.markdown()
