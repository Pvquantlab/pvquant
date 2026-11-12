"""v2.600 (Faz 4 F4-F, Stage 9) — mevzuat kural sicili: sicil bütünlüğü (künye, RG envanteri, yürürlük), motor = sicil (gün gün, segment×koşul),
AFL zinciri geriye uyumlu, M5 sürüm (surum_tam AFL+DSG ayırt eder; surum değişmedi), sha16 kararlılığı, takvim/senaryo tek kaynak,
anlık görüntü (DB, idempotent), API uçları, meta damgaları, olay sayacı katsayıları."""
from __future__ import annotations

import json
import re
import uuid
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from pvquant.ext.turkiye import kgup, kunye
from pvquant.ext.turkiye import kural_sicili as ks
from pvquant.ext.turkiye import kurallar as kr
from pvquant.services import dengesizlik_service as ds
from pvquant.services import piyasa_service

KOK = Path(__file__).resolve().parents[1]
ENV = json.loads((KOK / "tests/data/kunye_envanteri.json").read_text(encoding="utf-8"))
RG = re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{4})-(\d{5})")


# ───────────────────────────────────────────── sicil bütünlüğü ─────────────────────────────────────────────
def test_sicil_kayitlari_tutarli_ve_kunyeli():
    assert len(ks.SICIL) >= 60 and len({(k.kural_id, k.surum, k.kosul) for k in ks.SICIL}) == len(ks.SICIL)   # sürüm etiketi tekil
    for k in ks.SICIL:
        assert k.dogrulama in ks.DOGRULAMA and k.gerekce and k.madde and k.parametre
        assert k.yururluk_bit is None or k.yururluk_bit > k.yururluk_bas
        if k.yayim_rg:
            g, a, y, sayi = RG.match(k.yayim_rg).groups()
            assert sayi in ENV and ENV[sayi] == f"{int(g):02d}.{int(a):02d}.{y}", (k.surum, k.yayim_rg)   # RG envanteriyle eş
        if k.kunye_ad in kunye.KUNYE:
            assert kunye.kunye(k.kunye_ad)
    # her kural_id için yürürlük aralıkları (aynı segment/koşulda) çakışmaz
    for kid in {k.kural_id for k in ks.SICIL}:
        for seg_kosul in {(k.segmentler, k.kosul) for k in ks.SICIL if k.kural_id == kid}:
            kay = sorted([k for k in ks.SICIL if k.kural_id == kid and (k.segmentler, k.kosul) == seg_kosul], key=lambda k: k.yururluk_bas)
            for a, b in zip(kay, kay[1:], strict=False):
                assert a.yururluk_bit is not None and a.yururluk_bit <= b.yururluk_bas, (kid, a.surum, b.surum)
    assert ks.sicil_sha16() == ks.sicil_sha16() and len(ks.sicil_sha16()) == 16
    assert {k.dogrulama for k in ks.SICIL if k.kural_id in ("2027", "dgp.15dk")} == {"belirsiz"}
    assert ks.ara("dsg.esik", date(2027, 3, 1)).dogrulama == "varsayim"


def test_motor_sicil_ile_birebir_gun_gun():
    """kurallar.py motoru değer ve dayanağı sicilden okur: 2015–2027 her gün, her segment×koşul için aynı."""
    g = date(2015, 7, 1); son = date(2027, 6, 30)
    while g <= son:
        afl_k = ks.ara("afl", g); assert kr.afl(g) == afl_k.deger and kr.afl_dayanak(g) == afl_k.gerekce
        e = kr.edt_kurali(g); r = ks.ara("edt.rejim", g); t = ks.ara("edt.toplama", g)
        assert e.rejim == r.rejim and e.k == r.deger["k"] and e.l == r.deger["l"] and e.toplama == t.deger and e.surum.startswith(r.surum)
        v = ks.ara("edt.V", g); assert (v.deger if v else None) == e.V and kr.v_degeri(g) == e.V
        esik, day = kr.dsg_esigi(g); d = ks.ara("dsg.esik", g); assert esik == d.deger and day == d.gerekce
        kes = ks.ara("kgup.kesim", g); assert kr.kgup_kesim(g)[0] == tuple(kes.deger) and kr.kgup_kesim(g)[1] == kes.gerekce
        for seg in ("lisansli_serbest", "lisansli_yekdem", "yeka", "lisanssiz_iletim", "lisanssiz_dagitim"):
            for portfoy in (False, True):
                for luy in (False, True):
                    kp = kr.kupst_kurali(g, seg, portfoy, luy)
                    kosul = None
                    if seg == "lisanssiz_dagitim" and portfoy: kosul = "portfoy"
                    if seg == "lisanssiz_iletim" and luy and ks.ara("kupst", g, seg, "luy_istisna"): kosul = "luy_istisna"
                    k = ks.ara("kupst", g, seg, kosul) or [x for x in ks.kayitlar("kupst") if x.segmentler and seg in x.segmentler and x.kosul is None][0]
                    assert (kp.m, kp.n, kp.n_ariza, kp.ariza_esigi, kp.surum, kp.dayanak) == (k.deger["m"], k.deger["n"], k.deger["n_ariza"], k.deger["ariza_esigi"], k.surum, k.gerekce), (g, seg, portfoy, luy)
        g += timedelta(days=37)   # 2015–2027 arası ~120 gün + sınır günleri aşağıda
    for g in (date(2019, 12, 31), date(2020, 1, 1), date(2020, 7, 31), date(2020, 8, 1), date(2023, 1, 31), date(2023, 2, 1), date(2024, 12, 31), date(2025, 1, 1),
              date(2025, 12, 31), date(2026, 1, 1), date(2026, 10, 18), date(2026, 10, 19), date(2026, 10, 31), date(2026, 11, 1), date(2026, 12, 31), date(2027, 1, 1)):
        k = kr.kural(g, "lisansli_serbest")
        assert k.surum == f"{ks.ara('edt.rejim', g).surum if g < date(2026, 1, 1) else 'edt-2026-V' + str(int(ks.ara('edt.V', g).deger)) + '-' + ks.ara('edt.toplama', g).deger}+{ks.ara('kupst', g, 'lisansli_serbest').surum}"


def test_afl_zinciri_geriye_uyumlu_ve_kapsam_disi():
    assert kr._AFL_ZINCIRI[0] == (date(2026, 4, 4), 4500.0, "Karar 14459 (RG 3.4.2026-33213 s.47)") and len(kr._AFL_ZINCIRI) == 37
    assert kr.afl(date(2015, 6, 30)) == 2000.0 and "kapsam dışı" in kr.afl_dayanak(date(2015, 6, 30))
    assert kr.afl(date(2017, 2, 1)) == 500.0 and ks.ara("afl", date(2017, 2, 1)).dogrulama == "dogrulandi" and ks.ara("afl", date(2018, 6, 1)).dogrulama == "dogrulanamadi"


def test_m5_surum_tam_afl_ve_dsg_ayirt_eder_surum_degismez():
    a, b = kr.kural(date(2026, 4, 3), "lisansli_serbest"), kr.kural(date(2026, 4, 4), "lisansli_serbest")
    assert a.surum == b.surum == "edt-2026-V150-edta_net+kupst-14029"                     # saklanan dizgi aynı (AFL değişimi görünmez — eski davranış)
    assert a.surum_tam != b.surum_tam and a.surum_tam.endswith("+afl3400+dsg5") and b.surum_tam.endswith("+afl4500+dsg5")   # tam sürüm ayırt eder
    c, d = kr.kural(date(2025, 12, 31), "lisansli_serbest"), kr.kural(date(2024, 12, 31), "lisansli_serbest")
    assert c.surum_tam.endswith("+afl3400+dsg10") and d.surum_tam.endswith("+afl3000+dsg-yok")
    prm = kr.parametre_cercevesi(pd.date_range("2026-04-03 20:00", "2026-04-04 03:00", freq="h", tz="UTC"), "lisansli_serbest")
    assert set(prm["surum"]) == {"edt-2026-V150-edta_net+kupst-14029"} and len(set(prm["surum_tam"])) == 2
    assert a.sicil_sha16 == ks.sicil_sha16()
    o = ds.kural_ozeti("lisansli_serbest", date(2026, 11, 12))
    assert o["kural_surumu_tam"] == "edt-2026-V100-edta_ayrik+kupst-14907+afl4500+dsg5" and o["kural_sicili_sha"] == ks.sicil_sha16()
    assert o["kgup_kesim"] == "15:30" and o["kgup_takvim"]["son"] == "15:30"


def test_takvim_senaryo_ve_belirsizlik_tek_kaynak():
    assert ks.guncel("kgup.takvim").deger == kgup.TAKVIM and kgup.TAKVIM["son"] == "15:30"
    sen = ks.guncel("piyasa.senaryo").deger
    assert piyasa_service.SENARYO_PTF == sen["ptf"] == 2651.81 and sen["smf"] == piyasa_service.SENARYO_SMF and sen["ad"] == piyasa_service.SENARYO_AD
    assert kr.BELIRSIZ_2027_GEREKCE is ks.BELIRSIZ_2027_GEREKCE
    oz = ks.ozet(date(2026, 11, 12))
    assert oz["sha16"] == ks.sicil_sha16() and oz["kayit"] == len(ks.SICIL) and "2027-belirsiz" in [g["surum"] for g in oz["gelecek"]]
    assert any(k["surum"] == "kupst-14907" for k in oz["yururlukte"]) and "dsg-5-2027-varsayim" in oz["belirsiz"]
    assert sum(oz["dogrulama_dagilimi"].values()) == len(ks.SICIL)


def test_olay_sayaci_katsayilari_sicilden():
    from pvquant.services.olay_service import _kupst_n, _sayac_metni
    assert _kupst_n("lisansli_serbest", date(2026, 11, 12)) == {"n": 0.05, "n_ariza": 0.08, "ariza_esigi": 30, "kural_surumu": "kupst-14907", "karar": "Karar 14907"}
    assert _kupst_n("lisansli_serbest", date(2025, 6, 1)) == {"n": 0.03, "n_ariza": 0.05, "ariza_esigi": 40, "kural_surumu": "kupst-13025", "karar": "Karar 13025"}
    assert "0,05'ten 0,08'e çıkarır (Karar 14907)" in _sayac_metni(_kupst_n("lisansli_serbest", date(2026, 11, 12)))
    il = _kupst_n("lisanssiz_iletim", date(2025, 6, 1))   # 2025 belirsiz: katsayı yok → sayı basılmaz, «Karar 2025» türetilmez
    assert il["n_ariza"] is None and il["karar"] == "Karar 13025" and "katsayısını değiştirmez" in _sayac_metni(il) and "0,00" not in _sayac_metni(il)
    assert _kupst_n(None, date(2026, 11, 12))["karar"] is None and "değiştirmez" in _sayac_metni(_kupst_n(None, date(2026, 11, 12)))
    from pvquant.ext.turkiye.dengesizlik import _kupst_yururluk
    assert _kupst_yururluk("kupst-14907-dagitim") == "2026-11-01" and _kupst_yururluk("yok") is None
    assert _kupst_yururluk("kupst-dagitim-santral-0") is None   # kapsam başı sentineli (2000-01-01) ekrana sızmaz


# ───────────────────────────────────────────── DB ──────────────────────────────────────────────
def test_db_anlik_goruntu_idempotent_ve_api():
    from sqlalchemy import text

    from pvquant.services import kural_sicili_service as kss
    r1 = kss.anlik_kaydet(); r2 = kss.anlik_kaydet()
    assert r1["sha16"] == r2["sha16"] == ks.sicil_sha16() and r2["yeni"] is False and r1["id"] == r2["id"]
    g = kss.anlik_getir(r1["sha16"]); assert g and g["kayit_sayisi"] == len(ks.SICIL) and len(g["sicil_json"]) == len(ks.SICIL)
    assert kss.gece_kural_sicili()["durum"] == "ok"
    with pytest.raises(Exception, match="permission denied"), __import__("pvquant.db", fromlist=["tenant_baglami"]).tenant_baglami(str(uuid.uuid4())) as s:
        s.execute(text("DELETE FROM kural_sicili_anlik WHERE sha16 = :s"), {"s": r1["sha16"]})
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": str(uuid.uuid4()), "tenant_id": str(uuid.uuid4()), "role": "viewer", "exp": 0}
    try:
        c = TestClient(api_main.app)
        j = c.get("/v1/kurallar").json()
        assert j["sicil"]["sha16"] == ks.sicil_sha16() and j["bugun"]["kural_surumu_tam"].startswith("edt-2026") and j["satirlar"] == kr.tablo("lisansli_serbest")
        j2 = c.get("/v1/kurallar/sicil").json()
        assert len(j2["kayitlar"]) == len(ks.SICIL) and j2["anlik"][0]["sha16"] == r1["sha16"] and j2["anlik_hata"] is None
    finally:
        api_main.app.dependency_overrides.pop(gecerli_kullanici, None)
