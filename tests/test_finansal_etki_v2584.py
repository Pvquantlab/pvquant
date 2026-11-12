"""v2.584 (Faz 2 F2-F, Stage 5) — karar desteği önerileri: her kural tetikleyen asgari özetle; tür (bilgi/öneri/eylem) ve sayfa bağlantısı; boş özet."""
from __future__ import annotations

from pvquant.services import finansal_etki_service as fe


def _o(**k):
    o = {"donem": {"tur": "ay"}, "meta": {"segment": "lisansli_serbest"},
         "uretim": {"sapma": {"pct": -2.0, "mwh": -10.0, "ortak_saat": 700}, "gerceklesen": {"saat": 740, "beklenen_saat": 744, "kapsama": {"kapsama_pct": 99.5}}, "planlanan": {"kaynak": "bildirilen", "saat": 744}},
         "gelir": {"tarife": {"tip": "sabit"}, "bilesenler": [{"nitelik": "sozlesme_tahmini"}]},
         "uzlastirma": {"fiyat": {"senaryo_saat": 0, "epias_saat": 744}, "resmi": {"not": None, "durum": {"dengesizlik": "uyumlu"}}, "bilesenler": [{"kod": "kupst", "nitelik": "hesaplanan", "toplanir": True}],
                        "santral_tasir": True, "dsg": {"uye": {"edt_dsg_tl": 1.0}}},
         "dusukluk": {"siniflar": [{"kod": "aciklanmayan", "saat": 10}, {"kod": "kisinti_bakim", "saat": 3}, {"kod": "fiziksel", "saat": 0}], "bilesenler": [{"kod": "sozlesme_acigi", "nitelik": "sozlesme_tahmini"}]},
         "maruziyet": {"nitelik": "eksik"}}
    for yol, deger in k.items():
        cur = o; parcalar = yol.split(".")
        for p in parcalar[:-1]:
            cur = cur[p]
        cur[parcalar[-1]] = deger
    return o


def _kodlar(o):
    return [x["kod"] for x in fe.oneriler(o)]


def test_sakin_ozet_oneri_uretmez():
    assert _kodlar(_o()) == []


def test_her_kural_tetiklenir():
    assert _kodlar(_o(**{"uretim.sapma.pct": -12.0}))[0] == "sapma_buyuk"
    r = fe.oneriler(_o(**{"uretim.sapma.pct": 12.0}))[0]
    assert r["tur"] == "eylem" and r["sayfa"] == "kgup" and "fazla üretim" in r["metin"] and "%12,0" in r["metin"] and "sapma -10,0 MWh" in r["dayanak"]
    assert _kodlar(_o(**{"uretim.sapma.pct": -6.0})) == ["sapma_orta"]
    assert _kodlar(_o(**{"uzlastirma.fiyat.senaryo_saat": 24})) == ["piyasa_verisi_eksik"]
    assert _kodlar(_o(**{"uzlastirma.resmi.not": fe.NOT_BILDIRIM_YOK})) == ["bildirim_yok"]
    assert _kodlar(_o(**{"uzlastirma.resmi.durum": {"dengesizlik": "fark"}})) == ["mutabakat_fark"]
    assert _kodlar(_o(**{"donem.tur": "gun"})) == ["resmi_ay"]
    assert _kodlar(_o(**{"gelir.tarife.tip": None, "gelir.bilesenler": [{"nitelik": "senaryo"}]})) == ["tarife_yok"]
    assert _kodlar(_o(**{"uretim.gerceklesen.kapsama.kapsama_pct": 80.0})) == ["olcum_eksik"]
    assert _kodlar(_o(**{"uretim.planlanan.kaynak": "oneri"})) == ["bildirilen_yok"]
    assert _kodlar(_o(**{"uzlastirma.bilesenler": [{"kod": "kupst", "nitelik": "eksik", "toplanir": True}]})) == ["kupst_katsayi"]
    assert _kodlar(_o(**{"dusukluk.siniflar": [{"kod": "aciklanmayan", "saat": 10}, {"kod": "kisinti_bakim", "saat": 0}, {"kod": "fiziksel", "saat": 0}]})) == ["olay_kaydi"]
    assert _kodlar(_o(**{"dusukluk.bilesenler": [{"kod": "sozlesme_acigi", "nitelik": "eksik"}]})) == ["sozlesme_esigi"]
    m = fe.oneriler(_o(**{"maruziyet": {"nitelik": "senaryo", "aralik_tl": {"p25": -12000.0, "p50": -9000.0, "p75": -4000.0}, "ufuk": {"gun": 7}}}))
    assert [x["kod"] for x in m] == ["maruziyet"] and "-12.000 … -4.000 TL" in m[0]["metin"] and m[0]["tur"] == "bilgi"
    assert _kodlar(_o(**{"uzlastirma.dsg": {"uye": None, "neden": None}})) == ["dsg_kodu"]
    assert _kodlar(_o(**{"uzlastirma.dsg": {"uye": None, "neden": "Santral DSG hesabının dışında"}})) == []
    assert _kodlar(_o(**{"meta.segment": "lisanssiz_dagitim", "uzlastirma.santral_tasir": False, "uzlastirma.dsg": {"uye": None, "neden": None}})) == []
    assert all(x["tur_ad"] in ("bilgi", "öneri", "eylem") for x in fe.oneriler(_o(**{"uretim.sapma.pct": -12.0, "uzlastirma.fiyat.senaryo_saat": 5})))
