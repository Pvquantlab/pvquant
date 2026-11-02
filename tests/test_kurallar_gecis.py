"""03.11 (v2.528 inceleme) — uzlaştırma kuralı sürüm tablosu: dönem bütünlüğü ve geçiş tarihlerinde deterministik seçim.
Hakkında tablosu (kr.tablo) ile saatlik hesap çerçevesi (kr.parametre_cercevesi) aynı kuralı seçmeli; geçmiş dönem
yeni katsayıyla sessizce değişmemeli. Katsayı/tarih uydurulmaz: değerler kurallar.py'deki dayanaklardan okunur."""
from datetime import date, timedelta

import pandas as pd

from pvquant.ext.turkiye import kurallar as kr


def test_tablo_donemleri_bitisik_ve_cakismasiz():
    t = kr.tablo("lisansli_serbest")
    assert len(t) >= 2 and t[-1]["gecerlilik_bitis"] is None            # son dönem açık uçlu
    for a, b in zip(t, t[1:]):
        assert a["gecerlilik_bitis"] is not None
        assert date.fromisoformat(a["gecerlilik_bitis"]) + timedelta(days=1) == date.fromisoformat(b["gecerlilik_bas"])   # boşluk/çakışma yok
    assert [r["belirsiz_2027"] for r in t] == [False] * (len(t) - 1) + [True]   # «belirsiz» yalnız 2027 ve sonrası


def test_tablo_her_gun_motorla_ayni():
    """Tablonun kapsadığı her gün: o günü kapsayan satır ile kural() aynı sürüm/katsayıyı vermeli (eski el listesi
    1.2.2023 Karar 11589-2 geçişini atlıyordu — satır m = 0,10 derken motor 0,12 uyguluyordu)."""
    for segment in ("lisansli_serbest", "lisanssiz_dagitim", "lisansli_yekdem"):
        t = kr.tablo(segment)
        assert date.fromisoformat(t[0]["gecerlilik_bas"]) == kr.TABLO_BAS
        g = kr.TABLO_BAS; son = date(2027, 6, 1)
        while g <= son:
            satir = [r for r in t if r["gecerlilik_bas"] <= g.isoformat() and (r["gecerlilik_bitis"] is None or g.isoformat() <= r["gecerlilik_bitis"])]
            assert len(satir) == 1, (segment, g)
            r = satir[0]; k = kr.kural(g, segment)
            assert (r["kural_surumu"], r["V"], r["aylik_toplama"], r["kupst"]["m"], r["kupst"]["n"], r["kupst"]["taban"], r["dsg_esik"], r["belirsiz_2027"]) == \
                   (k.surum, k.edt.V, k.edt.toplama, k.kupst.m, k.kupst.n, k.kupst.taban, k.dsg_esik, k.belirsiz_2027), (segment, g)
            assert min(r["AFL"] or 0, r["AFL_son"] or 0) <= (kr.afl(g) if r["AFL"] is not None else 0) <= max(r["AFL"] or 0, r["AFL_son"] or 0) or r["AFL"] is None
            g += timedelta(days=1)
    t = kr.tablo("lisansli_serbest")
    assert "2023-02-01" in [r["gecerlilik_bas"] for r in t]            # Karar 11589-2 satırı artık var
    assert [r for r in t if r["gecerlilik_bas"] == "2023-02-01"][0]["kupst"]["m"] == 0.12


def test_gecis_tarihlerinde_secim():
    """Her sınırda bir gün önce/sonra: tablo satırı ile kural() aynı sürümü vermeli; belgelenen değişimler yerinde."""
    t = kr.tablo("lisansli_serbest")
    for r in t[1:]:
        bas = date.fromisoformat(r["gecerlilik_bas"])
        assert kr.kural(bas, "lisansli_serbest").surum == r["kural_surumu"]
        onceki = kr.kural(bas - timedelta(days=1), "lisansli_serbest").surum
        assert onceki == [x for x in t if x["gecerlilik_bas"] < r["gecerlilik_bas"]][-1]["kural_surumu"]
    # 2026 rejimi 1.1.2026'da başlar (önceki gün 2025 rejimi)
    assert kr.kural(date(2025, 12, 31), "lisansli_serbest").edt.rejim != kr.kural(date(2026, 1, 1), "lisansli_serbest").edt.rejim
    # aylık toplama 19.10.2026'da değişir; V 1.11.2026'da 150 → 100
    assert kr.kural(date(2026, 10, 18), "lisansli_serbest").edt.toplama != kr.kural(date(2026, 10, 19), "lisansli_serbest").edt.toplama
    assert kr.kural(date(2026, 10, 31), "lisansli_serbest").edt.V == 150.0 and kr.kural(date(2026, 11, 1), "lisansli_serbest").edt.V == 100.0
    assert not kr.kural(date(2026, 12, 31)).belirsiz_2027 and kr.kural(date(2027, 1, 1)).belirsiz_2027


def test_saatlik_cerceve_siniri_saat_bazinda_uygular():
    """31.10 → 1.11.2026 geçişini içeren saatlik dilim: her saat KENDİ gününün kuralını alır (İstanbul günü, UTC değil)."""
    idx = pd.date_range("2026-10-31 18:00", "2026-11-01 06:00", freq="h", tz="UTC")
    prm = kr.parametre_cercevesi(idx, "lisansli_serbest")
    yerel = idx.tz_convert(kr.IST)
    once = prm[yerel.date == date(2026, 10, 31)]; sonra = prm[yerel.date == date(2026, 11, 1)]
    assert len(once) == 3 and len(sonra) == 10                       # 21:00–23:00 ve 00:00–09:00 İstanbul
    assert set(once["V"]) == {150.0} and set(sonra["V"]) == {100.0}
    assert set(once["surum"]) == {kr.kural(date(2026, 10, 31), "lisansli_serbest").surum}
    assert set(sonra["surum"]) == {kr.kural(date(2026, 11, 1), "lisansli_serbest").surum}
    # geçmiş dönem yeniden hesaplandığında bugünkü kural sızmaz (tekrar üretilebilirlik)
    eski = kr.parametre_cercevesi(pd.date_range("2025-06-01", periods=24, freq="h", tz="UTC"), "lisansli_serbest")
    assert set(eski["surum"]) == {kr.kural(date(2025, 6, 1), "lisansli_serbest").surum} and eski["V"].isna().all()
