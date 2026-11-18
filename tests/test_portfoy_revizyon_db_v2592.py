"""v2.592 (Faz 3 F3-E, DB) — revizyon karar desteği: yarın için gün içi yeni yayın (A santrali %20 düşük) → sapma_orta + santral_degisim; program öneri (bildirilen yok);
teslim penceresi açık (14:20 TSİ); bugün: kalan saatler, gün içi düzeltme penceresi; üye yok; izolasyon; otomatik eylem yok."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from sqlalchemy import text
from test_portfoy_sapma_db_v2590 import KAPS, TZ, _profil
from test_portfoy_sapma_db_v2590 import portfoy as _portfoy

from pvquant.db import sistem_baglami
from pvquant.services import portfoy_revizyon_service as rv

portfoy = _portfoy   # fixture'ı bu modülde ad olarak tanıtır
BUGUN = date(2026, 9, 11)


def test_db_yarin_ve_bugun_onerileri(portfoy):
    tid, tid2, pid, pl = portfoy
    simdi = pd.Timestamp("2026-09-11 14:20", tz=TZ)
    # A için gün içi yeni yayın (17:00 TSİ, 15:30 kesiminden sonra → program değişmez, «son» tahmin %20 düşer)
    idx = pd.date_range(pd.Timestamp("2026-09-12", tz=TZ), periods=24, freq="h").tz_convert("UTC")
    with sistem_baglami() as s:
        rid = s.execute(text("INSERT INTO forecast_runs(tenant_id, plant_id, run_at, mode, model, meteo_source, meteo_ozet_json) VALUES(CAST(:t AS uuid), :p, :ra, 'B', 'barhdadi_bennis', 'acik-nwp', '{}') RETURNING id"),
                        {"t": tid, "p": pl["A"], "ra": pd.Timestamp("2026-09-11 14:00", tz="UTC").to_pydatetime()}).scalar()
        p50 = _profil(KAPS["A"], idx) * 0.8
        s.execute(text("INSERT INTO forecast_values(tenant_id, run_id, plant_id, ts_utc, p50_kw, p10_kw, p90_kw) VALUES(:t, :r, :p, :ts, :p50, :p10, :p90)"),
                  [{"t": tid, "r": rid, "p": pl["A"], "ts": t.to_pydatetime(), "p50": float(a), "p10": float(a * 0.8), "p90": float(a * 1.2)} for t, a in zip(idx, p50, strict=True)])
    o = rv.oneriler(tid, pid, "yarin", simdi)
    assert o["durum"] == "ok" and o["gun"] == "2026-09-12" and o["santral"] == 3 and o["risk"]["saat"] == 24
    kod = {x["kod"]: x for x in o["oneriler"]}
    pct = o["risk"]["beklenen_sapma_pct"]
    assert -10 < pct < -5 and "sapma_orta" in kod and kod["sapma_orta"]["etiket"] == "tahmini" and "düşük" in kod["sapma_orta"]["metin"]
    assert kod["santral_degisim"]["metin"].startswith("Bir santralde") and o["santraller"][0]["santral"] == "GES A" and o["santraller"][0]["degisim_pct"] == pytest.approx(-20.0, abs=0.2)
    assert kod["program_yok"]["tur"] == "bilgi" and o["program_kaynak"]["oneri"] == 24 and kod["pencere"]["tur"] == "eylem" and "70 dakika" in kod["pencere"]["metin"]
    assert kod["fiyat_yok"]["metin"] == "Finansal etki hesabı için güncel piyasa fiyatı bulunamadı." and o["maruziyet"] is not None and "maruziyet" in kod
    assert kod["belirsizlik"]["etiket"] == "eksik" and o["ozet"].startswith("Yarın portföy beklentisi programdan %") and "eylem önerisi" in o["ozet"]
    assert o["meta"]["karar"].startswith("Karar desteğidir") and all(x["tur"] in ("bilgi", "oneri", "eylem") for x in o["oneriler"]) and o["oneriler"][0]["tur"] == "eylem"
    # 16:00 TSİ: pencere geçti
    o2 = rv.oneriler(tid, pid, "yarin", pd.Timestamp("2026-09-11 16:00", tz=TZ))
    assert {x["kod"]: x for x in o2["oneriler"]}["pencere"]["etiket"] == "gecti"
    # bugün: kalan saatler (14:20 → 14:00 saatinden itibaren 10 saat), gün içi pencere 15:00 teslimatı için 14:30'a kadar açık
    b = rv.oneriler(tid, pid, "bugun", simdi)
    assert b["durum"] == "ok" and b["gun"] == "2026-09-11" and b["risk"]["saat"] == 10 and b["gun_ici"]["acik"] is True and b["gun_ici"]["dakika_kaldi"] == 10
    kb = {x["kod"]: x for x in b["oneriler"]}
    assert "sakin" in kb and "bugünkü kalan saatlerdeki" in kb["sakin"]["metin"] and kb["pencere"]["tur"] == "eylem" and "15:00" in kb["pencere"]["metin"]
    assert b["olcum_yas_saat"] is not None and b["olcum_yas_saat"] > 6 and kb["olcum_tazelik"]["etiket"] == "eksik"   # ölçüm 10 Eylül'de bitiyor
    b2 = rv.oneriler(tid, pid, "bugun", pd.Timestamp("2026-09-11 14:40", tz=TZ))
    assert {x["kod"]: x for x in b2["oneriler"]}["pencere"]["etiket"] == "gecti" and b2["gun_ici"]["acik"] is False
    # üye yok / izolasyon / hedef hatası
    assert rv.oneriler(tid2, pid, "yarin", simdi)["durum"] == "uye_yok"
    with pytest.raises(ValueError):
        rv.oneriler(tid, pid, "haftaya", simdi)


def test_db_hazirla_onbellek_turu_birebir(portfoy):
    """18.11 DSG/portfoy hiz turu: oneriler == oneriler_hazirdan(JSON(hazirla)); zaman ilerleyince ayni hazirlikla pencere/olcum yasi taze."""
    import json

    from fastapi.encoders import jsonable_encoder
    tid, _, pid, _ = portfoy
    t = pd.Timestamp("2026-09-12 13:40", tz=TZ)
    dogrudan = rv.oneriler(tid, pid, "yarin", t)
    h = json.loads(json.dumps(jsonable_encoder(rv.hazirla(tid, pid, "yarin", t))))
    yeni = rv.oneriler_hazirdan(h, t)
    assert jsonable_encoder(yeni) == jsonable_encoder(dogrudan), "onbellek turu ciktiyi degistirmemeli"
    sonra = rv.oneriler_hazirdan(h, pd.Timestamp("2026-09-12 15:10", tz=TZ))
    assert sonra["pencere"]["durum"] == "pencere_acik" and dogrudan["pencere"]["durum"] == "erken" and sonra["simdi"].startswith("2026-09-12T15:10")
    assert (sonra["olcum_yas_saat"] or 0) > (dogrudan["olcum_yas_saat"] or 0)
    hb = json.loads(json.dumps(jsonable_encoder(rv.hazirla(tid, pid, "bugun", t))))
    assert rv.oneriler_hazirdan(hb, t)["gun_ici"] == rv.oneriler(tid, pid, "bugun", t)["gun_ici"]


def test_db_portfoy_damgasi_uyelik_ve_olcumle_degisir(portfoy):
    """18.11 DSG/portfoy hiz turu: portfoy damgasi uyelerin olcumunu/kosusunu ve uyelik/portfoy kayitlarini kapsar; uyelik eklenince etag degisir."""
    import uuid

    from pvquant.services import damga_service
    from pvquant.services import portfoy_varlik_service as pv
    tid, _, pid, _pl = portfoy
    d = damga_service.portfoy_hesapla(tid, pid)
    for k in ("son_scada", "son_kosu", "portfoy_guncelleme", "uyelik_guncelleme", "sozlesme_guncelleme", "son_portfoy_sonuc", "santral_ozu", "son_piyasa", "son_is"):
        assert k in d, k
    assert d["son_scada"] and d["son_kosu"] and d["uyelik_guncelleme"] and d["santral_ozu"]
    e1 = damga_service.etag_uret(d)
    with sistem_baglami() as s:
        yeni = str(uuid.uuid4())
        s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, 'GES Z', 1000, 37.0, 32.0, :tz, '{}')"), {"p": yeni, "t": tid, "tz": TZ})
    pv.uyelik_ekle(tid, pid, yeni, "2026-01-01")
    e2 = damga_service.etag_uret(damga_service.portfoy_hesapla(tid, pid))
    assert e2 != e1, "uyelik eklenince portfoy damgasi degismeli (santral ozu + uyelik guncelleme)"
    assert damga_service.etag_uret(damga_service.portfoy_hesapla(tid, str(uuid.uuid4()))) != e2   # bos portfoy: yalniz kiraci parcalari
