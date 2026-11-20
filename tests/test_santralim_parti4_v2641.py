# -*- coding: utf-8 -*-
"""v2.641 — Santralim denetimi Parti 4 (kalan bulgular): referans kıyasında sınır uyarısı (02A-B10), toplayıcı anahtarı önek
çakışması (02A-B11), KGÜP segment notu (02B-B5), segment etiketi."""
from datetime import datetime, timedelta, timezone

import pytest

from pvquant.ext.turkiye import segment as sg
from pvquant.services import edge_service as es
from pvquant.services import kgup_service as kgs
from pvquant.services import pilot_service as pls


def test_segment_etiketi_tum_uyeler():
    assert set(sg.ETIKET) == {s.value for s in sg.Segment}
    assert sg.Segment.LISANSSIZ_DAGITIM.etiket == "Lisanssız dağıtım" and sg.Segment.OZ_TUKETIM_SAATLIK.etiket == "Öz tüketim"


def test_kgup_segment_notu():
    assert "Segment seçilmedi" in kgs.segment_notu({})
    n = kgs.segment_notu({"segment": "lisanssiz_dagitim"})
    assert "Lisanssız dağıtım" in n and "KGÜP yükümlü değil" in n and "TPYS bildirimi gerekmez" in n
    assert "mahsuplaşma" in kgs.segment_notu({"segment": "oz_tuketim_saatlik"})
    for s in ("lisansli_serbest", "lisansli_yekdem", "yeka", "lisanssiz_iletim"):
        assert kgs.segment_notu({"segment": s}) is None, s
    assert "seçilmedi" in kgs.segment_notu({"segment": "uydurma"})   # bilinmeyen değer → segment yok sayılır
    src = open(kgs.__file__, encoding="utf-8").read()
    assert "seg_notu = segment_notu(pj)" in src and "uyarilar.append(seg_notu)" in src   # uret içinde uyarı satırı; kapı değil


def test_edge_dogrula_onek_cakismasi():
    a1, onek, _ = es.anahtar_uret(); a2, _, _ = es.anahtar_uret()
    g1 = es.ayristir(a1)[1]; g2 = es.ayristir(a2)[1]
    satir = lambda i, g: {"id": i, "tenant_id": "t", "plant_id": "p", "ad": i, "anahtar_hash": es._hash(g), "durum": "etkin"}   # noqa: E731
    hepsi = [satir("yeni", g2), satir("eski", g1)]   # aynı önekte iki kayıt (yeni → eski)
    assert es.dogrula(a1, bul=lambda o: hepsi)["id"] == "eski"   # eskiden LIMIT 1 ile yalnız «yeni» bakılır, «eski» hiç doğrulanamazdı
    assert es.dogrula(a2, bul=lambda o: hepsi)["id"] == "yeni"
    with pytest.raises(PermissionError, match="geçersiz"):
        es.dogrula(f"pvqe_{onek}_yanlisgizli", bul=lambda o: hepsi)
    assert es.dogrula(a1, bul=lambda o: satir("tek", g1))["id"] == "tek"   # eski tek-kayıt (dict) sözleşmesi
    with pytest.raises(PermissionError, match="geçersiz"):
        es.dogrula(a1, bul=lambda o: None)
    with pytest.raises(PermissionError, match="iptal"):
        es.dogrula(a1, bul=lambda o: [{**satir("eski", g1), "durum": "iptal"}])
    src = open(es.__file__, encoding="utf-8").read()
    assert 'WHERE prefix=:o ORDER BY olusturma DESC"' in src and "ORDER BY olusturma DESC LIMIT 1" not in src   # tüm adaylar çekilir


def test_referans_degerlendir_sinir_uyarisi(monkeypatch):
    from pvquant.services import kaynak_secim_service as ks, plant_service
    yaz = {}
    monkeypatch.setattr(plant_service, "params_birlestir", lambda t, p, **k: yaz.update(k))
    t0 = datetime(2026, 11, 10, 8, tzinfo=timezone.utc)
    ref = [{"ts_utc": t0 + timedelta(hours=i), "kwh": 100.0} for i in range(6)]
    # gölge görünümde yalnız 2 saat var → 4 saat «kaynak kıyasında yok»
    monkeypatch.setattr(ks, "golge_gorunum", lambda tid, plant, bas, bit, sinir: {"saatler": [{"ts_utc": (t0 + timedelta(hours=i)).isoformat(), "secilen": {"tamlik": "measured_complete", "energy_kwh": 100.0, "kaynak": "iec104"}} for i in range(2)], "uyari": None})
    k = pls.referans_degerlendir("t", {"id": "p", "params_json": {}}, ref, sinir="pcc_net", meta={"uyarilar": ["x"], "atlanan": 0})
    assert k["n_golge_yok"] == 4 and k["sinir_etiketi"] == "bağlantı noktası net"
    assert any("4 referans saati «bağlantı noktası net» sınırında kaynak kıyasında yok" in u for u in k["uyarilar"]) and k["uyarilar"][0] == "x"
    assert yaz["pilot"]["referans_sonuc"]["sinir_etiketi"] == "bağlantı noktası net" and yaz["pilot"]["referans_sonuc"]["sinir"] == "pcc_net"
    # hepsi kıyasta → uyarı yok
    monkeypatch.setattr(ks, "golge_gorunum", lambda tid, plant, bas, bit, sinir: {"saatler": [{"ts_utc": r["ts_utc"].isoformat(), "secilen": {"tamlik": "measured_complete", "energy_kwh": 100.0}} for r in ref], "uyari": None})
    k2 = pls.referans_degerlendir("t", {"id": "p", "params_json": {}}, ref, sinir="inverter_ac")
    assert k2["n_golge_yok"] == 0 and not any("kaynak kıyasında yok" in u for u in k2["uyarilar"])
