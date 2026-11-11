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
