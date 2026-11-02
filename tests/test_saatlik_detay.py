"""v2.527 (P2b-2) — EPYS saatlik uzlaştırma detayı: dosya tanıma (CSV/XLSX, kılavuz kolon adları), kayıt + okuma (RLS'li tablo, test DB; ekran bazında son
yükleme birleşimi), PVQuant dökümüyle eş kapsamlı saatlik kıyas ve fark ayrıştırması (sahte döküm), mutabakat özeti, API uçları."""
from __future__ import annotations

import io
import uuid
from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.services import dengesizlik_service as dz
from pvquant.services import mutabakat_service as ms
from pvquant.services import saatlik_detay_service as sd


def _csv(saat=48, bas="10.10.2026", ptf=2000.0, smf=2100.0, uevm=2.0, budup=1.8, edt_poz=0.0, edt_neg=380.0, kupst=12.5, baslik=True) -> bytes:
    """«Uzlaştırma Dönemi Detay Listeleme» benzeri; tarih ve saat ayrı sütun, Türkçe ondalık."""
    d0 = pd.Timestamp(f"{bas[6:]}-{bas[3:5]}-{bas[:2]} 00:00")
    hat = ["Uzlaştırma Dönemi Detay Listeleme;Fatura Dönemi: 10.2026", "Tarih;Saat;Versiyon;PTF (TL/MWh);SMF (TL/MWh);KUDÜP (MWh);BUDÜP (MWh);YALM (MWh);YATM (MWh);UEVM (MWh);UEÇM (MWh);Pozitif EDM (MWh);Negatif EDM (MWh);Pozitif EDT (TL);Negatif EDT (TL);KÜPSM (MWh);KÜPST (TL)"]
    if not baslik:
        hat = hat[:1]
    f = lambda v: f"{v:.3f}".replace(".", ",")   # noqa: E731
    for i in range(saat):
        t = d0 + pd.Timedelta(hours=i)
        hat.append(";".join([t.strftime("%d.%m.%Y"), t.strftime("%H:00"), "1", f(ptf), f(smf), f(budup), f(budup), "0", "0", f(uevm), "0", f(max(uevm - budup, 0)), f(max(budup - uevm, 0)), f(edt_poz), f(edt_neg), "0,050", f(kupst)]))
    return ("\n".join(hat) + "\n").encode("utf-8")


@pytest.fixture()
def kiraci():
    tid, pid = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, 'saatlik-test', 'active')"), {"t": tid})
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz) VALUES(:p, :t, 'Saatlik GES', 10000, 37.0, 32.0, 'Europe/Istanbul')"), {"p": pid, "t": tid})
    yield tid, {"id": pid, "name": "Saatlik GES", "capacity_kwp": 10000.0, "params_json": {}}
    with sistem_baglami() as s:
        for t in ("uzlastirma_saatlik", "uzlastirma_bildirimi"):
            s.execute(text(f"DELETE FROM {t} WHERE tenant_id=:t"), {"t": tid})
        s.execute(text("DELETE FROM plants WHERE id=:p"), {"p": pid})
        s.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": tid})


def test_dosya_oku_csv_ve_xlsx():
    o = sd.dosya_oku(_csv(), "detay.csv")
    assert len(o["satirlar"]) == 48 and o["donem"] == date(2026, 10, 1) and o["kaynak_ekran"] == "detay" and o["bicim"] == "csv" and o["uyarilar"] == []
    ilk = o["satirlar"][0]; assert ilk["ts_utc"].isoformat() == "2026-10-09T21:00:00+00:00" and ilk["ptf"] == 2000.0 and ilk["uevm_mwh"] == 2.0 and ilk["edt_neg_tl"] == 380.0 and ilk["kupst_tl"] == 12.5 and ilk["versiyon"] == "1"
    assert set(o["kolonlar"]) >= {"ptf", "smf", "uevm_mwh", "budup_mwh", "edt_poz_tl", "edt_neg_tl", "kupsm_mwh", "kupst_tl"}
    # XLSX: aynı tablo; tarih-saat tek hücrede
    buf = io.BytesIO()
    df = pd.DataFrame({"Tarih Saat": [f"2026-10-10 {h:02d}:00:00" for h in range(24)], "PTF": [1500.5] * 24, "SMF": [1600.0] * 24, "UEVM": [1.25] * 24, "Pozitif EDT": [10.0] * 24, "Negatif EDT": [0.0] * 24})
    df.to_excel(buf, index=False); x = sd.dosya_oku(buf.getvalue(), "detay.xlsx")
    assert x["bicim"] == "xlsx" and len(x["satirlar"]) == 24 and x["kaynak_ekran"] == "dengesizlik" and x["satirlar"][0]["ts_utc"].isoformat() == "2026-10-09T21:00:00+00:00" and x["satirlar"][5]["ptf"] == 1500.5
    # yalnız KÜPST ekranı; tutar var
    k = sd.dosya_oku("Tarih;Saat;PTF;SMF;KUDÜP;YALM;YATM;BUDÜP;KÜPST\n11.10.2026;09:00;2000;2100;1,5;0;0;1,5;3,25\n".encode("utf-8"), "kupst.csv")
    assert k["kaynak_ekran"] == "kupst" and k["satirlar"][0]["kupst_tl"] == 3.25 and k["uyarilar"] == []
    # başlık yok → hata; yinelenen saat → atlanan sayısı; çok ay → uyarı
    with pytest.raises(ValueError, match="başlığı bulunamadı"):
        sd.dosya_oku(_csv(baslik=False), "x.csv")
    y = sd.dosya_oku(_csv(saat=3) + "10.10.2026;02:00;1;1;1;1;1;0;0;1;0;0;0;0;0;0;0\n".encode("utf-8"), "y.csv"); assert y["atlanan"] == 1 and len(y["satirlar"]) == 3
    z = sd.dosya_oku(_csv(saat=30, bas="31.10.2026"), "z.csv"); assert z["donem"] == date(2026, 10, 1) and any("birden çok aya" in u for u in z["uyarilar"])
    assert sd._zaman("12.10.2026 13:00") == sd._zaman("12.10.2026", "13:00-14:00") == sd._zaman("2026-10-12 13:00:00") == sd._zaman("12/10/2026", 13)


def test_kaydet_oku_birlesim(kiraci):
    tid, plant = kiraci
    k = sd.kaydet(tid, plant, _csv(), "detay.csv")
    assert k["saat"] == 48 and k["donem"] == "2026-10" and k["kaynak_ekran"] == "detay" and len(k["sha256"]) == 64 and "KÜPST (TL)" in k["kolon_etiketleri"]
    with pytest.raises(ValueError, match="dönemine ait"):
        sd.kaydet(tid, plant, _csv(), "detay.csv", donem="2026-09")
    with pytest.raises(ValueError, match="gelecekte"):
        sd.kaydet(tid, plant, _csv(bas="10.10.2099"), "x.csv")
    # ikinci yükleme: yalnız KÜPST ekranı, farklı KÜPST — ekran bazında son yükleme; «detay» ekranı öncelikli (combine_first)
    sd.kaydet(tid, plant, "Tarih;Saat;PTF;SMF;KUDÜP;YALM;YATM;BUDÜP;KÜPST\n10.10.2026;00:00;2000;2100;1,8;0;0;1,8;99\n12.10.2026;05:00;2000;2100;1,8;0;0;1,8;7\n".encode("utf-8"), "kupst.csv")
    df, kullanilan = sd.oku(tid, plant["id"], date(2026, 10, 1))
    assert len(df) == 49 and [u["kaynak_ekran"] for u in kullanilan] == ["detay", "kupst"]
    assert df.loc[pd.Timestamp("2026-10-09 21:00", tz="UTC"), "kupst_tl"] == 12.5 and df.loc[pd.Timestamp("2026-10-12 02:00", tz="UTC"), "kupst_tl"] == 7.0
    y = sd.yuklemeler(tid, plant["id"]); assert len(y) == 2 and y[0]["kaynak_ekran"] == "kupst" and y[1]["saat"] == 48
    assert sd.oku(tid, plant["id"], date(2026, 9, 1))[0].empty


def _dokum(saat=48, bas="2026-10-10 00:00", ptf=2000.0, gerc=2.0, prog=1.8, edt_borc=380.0, edt_alacak=0.0, kupst=12.5):
    z = pd.date_range(bas, periods=saat, freq="h")
    return pd.DataFrame({"zaman": [t.strftime("%Y-%m-%d %H:%M") for t in z], "program_mwh": prog, "program_kaynak": "bildirilen", "gerceklesen_mwh": gerc, "sapma_mwh": gerc - prog, "yon": "fazla",
                         "ptf_tl_mwh": ptf, "smf_tl_mwh": 2100.0, "edt_borc_tl": edt_borc, "edt_alacak_tl": edt_alacak, "kupst_tl": kupst, "durum": "ok", "kural_surumu": "edt-2026"})


def test_kiyas_ayristirma_ve_mutabakat_ozeti(kiraci, monkeypatch):
    tid, plant = kiraci
    sd.kaydet(tid, plant, _csv(), "detay.csv")                                   # 10–11 Ekim, 48 saat, EPİAŞ: EDT borç 380, KÜPST 12,5
    # PVQuant: 72 saat (10–12 Ekim) — ortak 48; ilk 10 saatte fiyat farklı, 10–20 üretim farklı, 20–25 program farklı, 25–30 kural farkı (girdiler eşit, EDT farklı)
    df = _dokum(saat=72)
    df.loc[0:9, "ptf_tl_mwh"] = 1990.0; df.loc[10:19, "gerceklesen_mwh"] = 2.1; df.loc[20:24, "program_mwh"] = 1.7; df.loc[25:29, "edt_borc_tl"] = 400.0
    df.loc[0:29, "edt_borc_tl"] = df.loc[0:29, "edt_borc_tl"].where(df.loc[0:29, "edt_borc_tl"] != 380.0, 390.0)   # ilk 30 saatte EDT de farklı
    # 03.11 inceleme: 30–34 üretim/program eşit ama PVQuant sapması EPİAŞ EDM'sinden farklı (pozisyon) ve EDT 395; 35–36 PTF 2000,004 (tolerans içi) ve EDT 381 (yuvarlama)
    df.loc[30:34, "sapma_mwh"] = 0.3; df.loc[30:34, "edt_borc_tl"] = 395.0; df.loc[35:36, "ptf_tl_mwh"] = 2000.004; df.loc[35:36, "edt_borc_tl"] = 381.0
    monkeypatch.setattr(dz, "dokum", lambda t, p, gun, uretim=None: (df, {"fiyat": {"senaryo_saat": 0}}))
    k = sd.kiyas(tid, plant, date(2026, 10, 1), bugun=date(2026, 11, 2))
    assert k["yuklu"] and k["epias_saat"] == 48 and k["pv_saat"] == 72 and k["ortak_saat"] == 48 and k["yalniz_pvquant_saat"] == 24 and k["yalniz_epias_saat"] == 0
    a = k["ayristirma"]; assert (a["fiyat_farki_saat"], a["uretim_farki_saat"], a["program_farki_saat"], a["pozisyon_farki_saat"], a["yuvarlama_saat"], a["kural_farki_saat"]) == (10, 10, 5, 5, 2, 5)
    assert a["edt_farki_saat"] == 37 and a["uyumlu_saat"] == 11 and a["pozisyon_karsilastirildi"]
    t = k["toplam"]; assert t["edt_net_epias_tl"] == -48 * 380.0 and t["edt_net_fark_tl"] == round(-(25 * 10.0 + 5 * 20.0 + 5 * 15.0 + 2 * 1.0), 2) and t["kupst_fark_tl"] == 0.0 and t["uevm_mwh"] == 96.0
    assert k["en_buyuk"][0]["edt_fark_tl"] == -20.0 and k["en_buyuk"][0]["nedenler"] == ["kural"] and len(k["satirlar"]) == 48 and k["satirlar"][0]["nedenler"] == ["fiyat"]
    assert k["satirlar"][30]["nedenler"] == ["pozisyon"] and k["satirlar"][30]["edm_epias_mwh"] == 0.2 and k["satirlar"][30]["sapma_pvquant_mwh"] == 0.3 and k["satirlar"][30]["yon"] == "fazla"
    assert k["satirlar"][35]["nedenler"] == ["yuvarlama"] and k["neden_aciklama"]["pozisyon"].startswith("üretim ve program eşit")
    csv = sd.kiyas_csv(k); assert csv.startswith("﻿# ") and csv.count("\n") == 50 and ";fiyat" in csv and ";pozisyon" in csv
    # mutabakat özeti ve eylem eki
    oz = sd.ozet_kisa(tid, plant, date(2026, 10, 1), bugun=date(2026, 11, 2)); assert oz["yuklu"] and oz["ortak_saat"] == 48 and oz["toplam"]["edt_net_fark_tl"] == -427.0
    m = ms.mutabakat(tid, plant, "2026-10", bugun=date(2026, 11, 2))
    assert m["saatlik_detay"]["ortak_saat"] == 48 and (m["eylem"] or "").count("Eş kapsamlı kıyas") == 1 and "ortak 48 saat" in m["eylem"]
    assert ms.mutabakat(tid, plant, "2026-09", bugun=date(2026, 11, 2))["saatlik_detay"] == {"yuklu": False, "epias_saat": 0, "ortak_saat": 0}
    # yüklü ama PVQuant dökümü yok → ortak 0, toplam yok
    monkeypatch.setattr(dz, "dokum", lambda t, p, gun, uretim=None: (pd.DataFrame(), {}))
    k0 = sd.kiyas(tid, plant, date(2026, 10, 1), bugun=date(2026, 11, 2)); assert k0["yuklu"] and k0["ortak_saat"] == 0 and k0["toplam"] is None


def test_api_saatlik_uclari(kiraci, monkeypatch):
    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import plant_service
    tid, plant = kiraci
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": tid, "role": "admin", "exp": 0}
    monkeypatch.setattr(plant_service, "getir", lambda t, p: {"id": plant["id"], "name": "Saatlik GES", "capacity_kwp": 10000.0, "params_json": {}} if p == plant["id"] else None)
    monkeypatch.setattr(dz, "dokum", lambda t, p, gun, uretim=None: (_dokum(), {"fiyat": {"senaryo_saat": 0}}))
    kayit = []
    monkeypatch.setattr(api_main._denetim, "kaydet", lambda *a, **k: kayit.append((a, k)))
    c = TestClient(api_main.app)
    try:
        r = c.post(f"/v1/plants/{plant['id']}/mutabakat/saatlik", files={"dosya": ("detay.csv", _csv(), "text/csv")})
        assert r.status_code == 201, r.text
        assert r.json()["saat"] == 48 and r.json()["donem"] == "2026-10" and kayit[-1][0][:2] == ("musteri", "mutabakat_saatlik_yukle")
        assert c.post(f"/v1/plants/{plant['id']}/mutabakat/saatlik?donem=2026-09", files={"dosya": ("detay.csv", _csv(), "text/csv")}).status_code == 422
        assert c.get(f"/v1/plants/{plant['id']}/mutabakat/saatlik?fmt=pdf").status_code == 422 and c.get(f"/v1/plants/{plant['id']}/mutabakat/saatlik?uretim=x").status_code == 422
        g = c.get(f"/v1/plants/{plant['id']}/mutabakat/saatlik"); assert g.status_code == 200, g.text
        j = g.json(); assert j["donem"] == "2026-10" and j["ortak_saat"] == 48 and j["toplam"]["edt_net_fark_tl"] == 0.0 and j["ayristirma"]["uyumlu_saat"] == 48 and len(j["yuklemeler_tum"]) == 1
        cs = c.get(f"/v1/plants/{plant['id']}/mutabakat/saatlik?donem=2026-10&fmt=csv"); assert cs.status_code == 200 and "text/csv" in cs.headers["content-type"] and kayit[-1][0][1] == "mutabakat_saatlik_indir"
        assert c.get("/v1/plants/00000000-0000-0000-0000-000000000000/mutabakat/saatlik").status_code == 404
    finally:
        api_main.app.dependency_overrides.clear()
