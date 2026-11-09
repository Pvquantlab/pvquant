"""v2.558 — V3 çoklu cihaz (ek birimler) ve V5 kısıt (701 ThrotSrc, 704/123 yalnız okunur, kısıt olay adayı). SAF testler."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pvquant.io.canli import sunspec as sp
from pvquant.services import canli_alim_service as ca
from pvquant.services import canli_ornekleme_service as co
from pvquant.services import cihaz_olay_service as ce

T0 = datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc)


def test_hedef_dogrula_ek_cihazlar():
    h = ca.hedef_dogrula("10.0.0.5", 502, 1, None, None, [{"birim": 2, "ad": "İnverter 2"}, 3, {"birim": 4, "profil": "sungrow_string"}])
    assert h["cihazlar"] == [{"birim": 2, "ad": "İnverter 2"}, {"birim": 3}, {"birim": 4, "profil": "sungrow_string"}]
    assert "cihazlar" not in ca.hedef_dogrula("10.0.0.5", 502, 1)
    for kotu, msg in (([{"birim": 1}], "yineleniyor"), ([{"birim": 2}, {"birim": 2}], "yineleniyor"), ([{"birim": 300}], "0–247"), ([{"birim": "x"}], "sayı"), ([{"birim": i} for i in range(2, 36)], "en çok 32")):
        with pytest.raises(ValueError, match=msg):
            ca.hedef_dogrula("10.0.0.5", 502, 1, None, None, kotu)


class _Istemci:
    """Birim kimliğine göre farklı SunSpec seri no ve güç döndüren sahte istemci (cihaz_oku yerine monkeypatch)."""
    def __init__(self, host, port, birim, za):
        self.birim = birim
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def test_ornekler_al_ana_ve_ek_cihazlar_kismi_hata(monkeypatch):
    def sahte_cihaz_oku(istemci, profil):
        if istemci.birim == 3:
            raise TimeoutError("yanıt yok")
        return {"ortak": {"seri_no": f"SN-{istemci.birim}"}, "inverter": {"guc_w": 1000.0 * istemci.birim, "enerji_wh": 5.0, "durum_kodu": 4, "olaylar": []}, "profil": "1xx", "sinir": "inverter_ac", "enerji_yolu": "1xx",
                "kisit": {"kisma_yuzde": 25.0, "etkin": True, "kaynak": ["MAX_W"], "model": 701} if istemci.birim == 2 else None}
    monkeypatch.setattr(ca, "cihaz_oku", sahte_cihaz_oku)
    monkeypatch.setattr(ca, "_cozumle", lambda h: "10.0.0.5")
    b = ca.hedef_dogrula("10.0.0.5", 502, 1, None, None, [{"birim": 2}, {"birim": 3}])
    liste, hatalar = co.ornekler_al(b, T0, _Istemci)
    assert [o["cihaz_id"] for o in liste] == ["SN-1", "SN-2"] and [o["guc_w"] for o in liste] == [1000.0, 2000.0]
    assert liste[1]["kisit_yuzde"] == 25.0 and liste[1]["kisit_kaynak"] == ["MAX_W"] and liste[0]["kisit_yuzde"] is None
    assert len(hatalar) == 1 and "birim 3" in hatalar[0] and "TimeoutError" in hatalar[0]
    # seri no yoksa ek cihazlı kurulumda kimlik «birim-N» (çakışmasın), tek cihazda «santral»
    monkeypatch.setattr(ca, "cihaz_oku", lambda i, p: {"ortak": {}, "inverter": {"guc_w": 1.0}, "profil": "1xx", "sinir": "inverter_ac"})
    assert [o["cihaz_id"] for o in co.ornekler_al(b, T0, _Istemci)[0]] == ["birim-1", "birim-2", "birim-3"]
    assert co.ornek_al(ca.hedef_dogrula("10.0.0.5", 502, 1), T0, _Istemci)["cihaz_id"] == "santral"


def _oku_704(va, adet):
    r = [0] * adet
    r[12] = 1; r[13] = 700; r[52] = (-1) & 0xFFFF   # etkin, %70,0 → kısma %30
    return r


def _oku_123(va, adet):
    r = [0] * adet
    r[3] = 100; r[7] = 0; r[21] = 0   # sınır %100 ama devre dışı → kısma yok
    return r


def test_kontrol_modelleri_ve_kisit_ozeti():
    k704 = sp.der_kontrol_modeli(_oku_704, 0, 65)
    assert k704 == {"sinir_etkin": True, "sinir_yuzde": 70.0, "model": 704}
    oz = sp.kisit_ozeti(None, k704); assert oz["kisma_yuzde"] == 30.0 and oz["etkin"] and oz["kaynak"] == ["MAX_W"] and oz["model"] == 704
    k123 = sp.anlik_kontrol_modeli(_oku_123, 0, 24)
    assert k123 == {"sinir_etkin": False, "sinir_yuzde": 100.0, "model": 123}
    oz = sp.kisit_ozeti(None, k123); assert oz["kisma_yuzde"] == 0.0 and oz["etkin"] is False and oz["kaynak"] == []
    # 701 ThrotPct öncelikli; ThrotSrc bitleri çözülür
    inv = {"kisma_yuzde": 12.0, "kisma_kaynak": ["FREQ_WATT"]}
    oz = sp.kisit_ozeti(inv, k704); assert oz["kisma_yuzde"] == 12.0 and oz["kaynak"] == ["FREQ_WATT"] and oz["model"] == 701
    assert sp.kisit_ozeti(None, None) is None
    with pytest.raises(ValueError, match="kısa"):
        sp.der_kontrol_modeli(_oku_704, 0, 20)
    assert sp._bitler(1 << 5, sp.THROT_SRC) == ["FREQ_WATT"]


def _o(dk, kisit=None, cihaz="SN-A"):
    return {"ts_utc": T0 + timedelta(minutes=dk), "cihaz_id": cihaz, "durum_kodu": 4, "olaylar": [], "guc_w": 500.0, "kisit_yuzde": kisit, "kisit_kaynak": ["MAX_W"] if kisit else []}


def test_kisit_olay_adayi():
    ornekler = [_o(0), _o(15, 50.0), _o(30, 48.0), _o(45, 52.0), _o(60), _o(75, 10.0), _o(90)]
    a = [x for x in ce.adaylar(ornekler, [], 15, T0 + timedelta(minutes=100)) if x["tur"] == "kisit"]
    assert len(a) == 1 and a[0]["ornek_sayisi"] == 3 and a[0]["kisma_yuzde_ort"] == 50.0 and a[0]["kisma_yuzde_maks"] == 52.0 and a[0]["kodlar"] == ["MAX_W"]
    assert a[0]["bas"] == (T0 + timedelta(minutes=15)).isoformat() and a[0]["bit"] == (T0 + timedelta(minutes=60)).isoformat() and a[0]["durum"] == "bitti"
    assert "talimat" in a[0]["not"] and not a[0]["kayitli"]
    # tek örneklik kısma (75. dk) gürültü sayılır; arıza adayı yok
    assert not [x for x in ce.adaylar(ornekler, [], 15, T0 + timedelta(minutes=100)) if x["tur"] == "ariza"]
    # mevcut YAT talimatı ile çakışan kısıt «kayıtlı»
    mevcut = [{"baslangic": T0 + timedelta(minutes=10), "bitis": T0 + timedelta(minutes=70), "tur": "talimat_yat"}]
    assert ce.adaylar(ornekler, mevcut, 15, T0 + timedelta(minutes=100))[-1]["kayitli"] or any(x["kayitli"] for x in ce.adaylar(ornekler, mevcut, 15, T0 + timedelta(minutes=100)) if x["tur"] == "kisit")
