"""29.10 (v2.506) — dışa aktarma biçimi müşterinin EPYS/TPYS dosyasından öğrenilir: CSV ve Excel ayrıştırma, sıra/ayraç/ondalık/tarih,
csv_metni'nin öğrenilen sırayı uygulaması (varsayılan çıktı bayt bayt aynı), geri okuma (csv_oku) uyumu, API kapıları."""
import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.deps import gecerli_kullanici
from pvquant.ext.turkiye import kgup as kg


def _tablo():
    return pd.DataFrame({"tarih": ["2026-10-30"] * 24, "saat": range(24), "uevcb": ["UEVCB-1"] * 24,
                         "kgup_mwh": [1.25] * 24, "eak_mw": [9.0] * 24, "ceyrek": [None] * 24})


def test_csv_ogren_sira_ayrac_ondalik_ve_eslesmeyen():
    r = kg.sablon_ogren("Saat;KGÜP (MWh);Açıklama;EAK (MW);UEVÇB\n0;1,250;x;9,000;UEVCB-1\n".encode("utf-8-sig"), "epys.csv")
    s = r["sablon"]
    assert s["sira"] == "saat,kgup,eak,uevcb" and s["ayrac"] == ";" and s["ondalik"] == "," and s["kgup"] == "KGÜP (MWh)" and s["uevcb"] == "UEVÇB"
    assert r["eslesmeyen"] == ["Açıklama"] and r["bicim"] == "csv" and "tarih" not in s
    r2 = kg.sablon_ogren(b"Date,Hour,Plan MWh\n2026-10-30,0,1.25\n", "x.csv")
    assert r2["sablon"]["ayrac"] == "," and r2["sablon"]["ondalik"] == "." and r2["sablon"]["tarih_bicim"] == "%Y-%m-%d" and r2["sablon"]["sira"] == "tarih,saat,kgup"
    with pytest.raises(ValueError):
        kg.sablon_ogren(b"A;B\n1;2\n")
    with pytest.raises(ValueError):
        kg.sablon_ogren(b"")


def test_xlsx_ogren():
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.append(["Tarih", "Saat", "UEVÇB", "KGÜP", "EAK"]); ws.append(["30.10.2026", 0, "U1", 1.25, 9])
    b = io.BytesIO(); wb.save(b)
    r = kg.sablon_ogren(b.getvalue(), "sablon.xlsx")
    assert r["bicim"] == "xlsx" and r["sablon"]["sira"] == "tarih,saat,uevcb,kgup,eak" and r["sablon"]["tarih_bicim"] == "%d.%m.%Y" and r["uyarilar"]


def test_csv_metni_ogrenilen_sira_ve_varsayilan_degismez():
    t = _tablo()
    varsayilan = kg.csv_metni(t)
    assert varsayilan.splitlines()[:2] == ["Saat,Miktar", "00:00,1.25"]            # v2.512: varsayılan = TPYS KGUP.csv
    ogr = kg.sablon_ogren("Saat;KGÜP (MWh);EAK (MW);UEVÇB\n0;1,250;9,000;UEVCB-1\n".encode("utf-8-sig"))["sablon"]
    sab = kg.Sablon.params_json_dan({"kgup_sablon": ogr})
    m = kg.csv_metni(t, sab)
    assert m.splitlines()[0] == "Saat;KGÜP (MWh);EAK (MW);UEVÇB" and m.splitlines()[1] == "0;1,250;9,000;UEVCB-1"
    # geri okuma: kendi ürettiğimiz dosya aynı şablonla okunur
    from pvquant.services import kgup_arsiv_service as ka
    df = ka.csv_oku(kg.csv_baytlari(t, sab), sab)
    assert len(df) == 24 and abs(float(df["kgup_mwh"].sum()) - 30.0) < 1e-6
    # ingilizce/virgül şablon
    ing = kg.Sablon.params_json_dan({"kgup_sablon": kg.sablon_ogren(b"Date,Hour,Plan MWh\n2026-10-30,0,1.25\n")["sablon"]})
    m2 = kg.csv_metni(t, ing)
    assert m2.splitlines()[0] == "Date,Hour,Plan MWh" and m2.splitlines()[1] == "2026-10-30,0,1.250"


@pytest.fixture()
def istemci(monkeypatch):
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "t", "role": "editor", "exp": 0}
    from pvquant.services import plant_service
    depo = {"params_json": {}}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": p, "capacity_kwp": 1000.0, **depo})
    def birlestir(t, p, **k):
        depo["params_json"] = {kk: v for kk, v in {**depo["params_json"], **k}.items() if v is not None}; return depo["params_json"]
    monkeypatch.setattr(plant_service, "params_birlestir", birlestir)
    yield TestClient(api_main.app), depo
    api_main.app.dependency_overrides.clear()


def test_sablon_kapilari(istemci):
    c, depo = istemci
    j = c.post("/v1/plants/p1/kgup/sablon", files={"dosya": ("epys.csv", "Saat;KGÜP (MWh);EAK (MW);UEVÇB\n0;1,250;9,000;U1\n".encode("utf-8-sig"), "text/csv")}).json()
    assert j["sablon"]["kolonlar"] == ["Saat", "KGÜP (MWh)", "EAK (MW)", "UEVÇB"] and j["sablon"]["kaynak"]["dosya"] == "epys.csv" and "öğrenildi" in j["sablon"]["durum"]
    assert depo["params_json"]["kgup_sablon"]["sira"] == "saat,kgup,eak,uevcb"
    assert c.post("/v1/plants/p1/kgup/sablon", files={"dosya": ("k.csv", b"A;B\n1;2\n", "text/csv")}).status_code == 422
    s = c.delete("/v1/plants/p1/kgup/sablon").json()["sablon"]
    assert s["kaynak"] is None and s["kolonlar"] == ["Saat", "Miktar"] and s["eak_kolonlar"][:3] == ["Saat", "Miktar", "ic_tuketim"] and "kgup_sablon" not in depo["params_json"]


def test_epys_disa_aktarimi_uyarisi():
    """v2.510 (04 #5): EPYS «KGÜP Listeleme» dışa aktarımı (Tarih/Versiyon/Bölge/Santral/UEVÇB/Miktar) yükleme şablonu değildir → uyarı."""
    from pvquant.ext.turkiye import kgup
    b = "Tarih;Versiyon;Bölge;Santral;UEVÇB;Saat;Miktar KGUP MWh\n01.11.2026;1;TR1;Edikli GES;40X;0;0,000\n".encode("utf-8-sig")
    r = kgup.sablon_ogren(b, "epys.csv")
    assert any("EPYS" in u and "TPYS" in u for u in r["uyarilar"]), r["uyarilar"]
    b2 = "Tarih;Saat;UEVCB;KGUP_MWh;EAK_MW\n01.11.2026;0;40X;0,000;12\n".encode("utf-8-sig")
    assert not any("EPYS" in u for u in kgup.sablon_ogren(b2, "tpys.csv")["uyarilar"])
    assert "TPYS" in kgup.SABLON_DURUMU and "EPYS'den" not in kgup.SABLON_DURUMU


# ---------------------------------------------------------------- v2.512: resmî TPYS şablonları (kullanıcı 30.10.2026'da indirdi) ------
from pathlib import Path
TPYS = Path(__file__).parent / "data" / "tpys"


def _sifir():
    idx = pd.date_range("2026-10-25", periods=24, freq="h", tz="Europe/Istanbul")
    return pd.DataFrame({"tarih": idx.date, "saat": idx.hour, "uevcb": "U", "kgup_mwh": [0.0] * 24, "eak_mw": [0.0] * 24})


def test_varsayilan_kgup_tpys_sablonuyla_bayt_bayt():
    """KGUP.csv (TPYS ek 146797): «Saat,Miktar», 24 satır «HH:00,0», virgül, LF, BOM yok — varsayılan çıktı bayt bayt aynı."""
    assert kg.csv_baytlari(_sifir()) == (TPYS / "KGUP.csv").read_bytes()
    m = kg.csv_metni(_sifir().assign(kgup_mwh=[1.25] * 24))
    assert m.splitlines()[1] == "00:00,1.25" and m.splitlines()[-1] == "23:00,1.25" and not m.startswith("\ufeff")


def test_eak_dosyasi_tpys_sablonu():
    """EAK.csv (TPYS ek 146796): 8 kolon, saat 0–23 tam sayı, boş hücre = yok, CRLF. Kurulu güç − EAK − iç tüketim → kaynak_yetersizligi."""
    ref = (TPYS / "EAK.csv").read_bytes().decode()
    t = _sifir().assign(eak_mw=[600.0] * 23 + [590.0])
    e = kg.eak_csv_metni(t, 605.0, ic_tuketim_mw=5.0)
    assert e.splitlines()[0] == ref.splitlines()[0] == ",".join(kg.EAK_KOLONLAR) and "\r\n" in e and len(e.splitlines()) == 25
    assert e.splitlines()[1] == "0,600,5,,,,," and e.splitlines()[24] == "23,590,5,10,,,,"
    gece = kg.eak_csv_metni(_sifir(), 12.5)
    assert gece.splitlines()[1] == "0,0,,12.5,,,," and gece.splitlines()[0].startswith("Saat,Miktar")   # GES gece: EAK 0, kurulu gücün tamamı kaynak yetersizliği
    with pytest.raises(ValueError):
        kg.eak_csv_metni(_sifir(), 1.0, gerekce="x")
    # EAK şablonu KGÜP şablonu olarak öğretilemez
    with pytest.raises(ValueError):
        kg.sablon_ogren((TPYS / "EAK.csv").read_bytes(), "EAK.csv")


def test_tpys_kgup_ogrenme_ve_geri_okuma():
    """Resmî KGUP.csv öğretilince varsayılanla aynı biçim çıkar; arşiv okuyucu «HH:00» saati ve eski «;» dosyasını da okur."""
    from pvquant.services import kgup_arsiv_service as ka
    s = kg.sablon_ogren((TPYS / "KGUP.csv").read_bytes(), "KGUP.csv")["sablon"]
    assert s["ayrac"] == "," and s["ondalik"] == "." and s["saat_bicim"] == "%H:00" and s["bom"] == "" and s["kesir"] == "3" and s["sira"] == "saat,kgup" and s["kgup"] == "Miktar"
    t = ka.csv_oku((TPYS / "KGUP.csv").read_bytes())
    assert t["saat"].tolist() == list(range(24)) and float(t["kgup_mwh"].sum()) == 0.0
    eski = ("Tarih;Saat;UEVCB;KGUP_MWh;EAK_MW\n" + "\n".join(f"25.10.2026;{h};U;1,250;9,000" for h in range(24)) + "\n").encode("utf-8-sig")
    t2 = ka.csv_oku(eski)
    assert abs(float(t2["kgup_mwh"].sum()) - 30.0) < 1e-6 and t2["eak_mw"][0] == 9.0
    # v2.506–v2.511 arasında öğrenilmiş şablon (saat_bicim/bom yok): tam sayı saat ve BOM korunur
    sab = kg.Sablon.params_json_dan({"kgup_sablon": {"ayrac": ";", "ondalik": ",", "sira": "saat,kgup", "kgup": "KGÜP (MWh)"}})
    b = kg.csv_baytlari(_sifir(), sab)
    assert b.startswith(b"\xef\xbb\xbf") and b.decode("utf-8-sig").splitlines()[1] == "0;0,000"
