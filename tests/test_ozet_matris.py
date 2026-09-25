"""v2.365 — saat×ay matrisi köşe durumları (25 Eyl canlı, Format Lab).

Yalnız enerji eşlenmiş günlük dosyada güç kolonu TÜMÜYLE boş kalır; pivot boş
döner ve boş index'in min'i int(NaN) ile ucu 500'e düşürüyordu. Ayrıca tüm
hücreler eşitken panel renk normalizasyonu NaN üretiyordu (ayrı zırh, panelde).
"""
import contextlib
import datetime as dt

import pandas as pd

from pvquant.services import ozet_service


def _kur(monkeypatch, df):
    class SahteOturum:
        def execute(self, *a, **k):
            class R:
                def mappings(self_r): return self_r
                def first(self_r): return {"tz": "Europe/Istanbul"}
            return R()
        def connection(self): return None
    @contextlib.contextmanager
    def baglam(_t):
        yield SahteOturum()
    monkeypatch.setattr("pvquant.db.tenant_baglami", baglam)
    monkeypatch.setattr(pd, "read_sql", lambda *a, **k: df)


def test_guc_tumuyle_bos_500_atmaz(monkeypatch):
    ts = [dt.datetime(2016, 5, g, 21, tzinfo=dt.timezone.utc) for g in range(2, 31)]
    _kur(monkeypatch, pd.DataFrame({"ts_utc": ts, "power_kw": [None] * len(ts)}))
    m = ozet_service.saat_ay_matrisi("t", "p")
    assert m["saatler"] == [] and m["hucreler"] == []
    assert m["toplam"] == [None] * 12


def test_tek_saatlik_veri_saat_hucre_uyumlu(monkeypatch):
    ts = [dt.datetime(2016, 5, g, 9, tzinfo=dt.timezone.utc) for g in range(2, 31)]
    _kur(monkeypatch, pd.DataFrame({"ts_utc": ts, "power_kw": [420.0] * len(ts)}))
    m = ozet_service.saat_ay_matrisi("t", "p")
    assert len(m["saatler"]) == len(m["hucreler"]) == 1
    assert m["hucreler"][0][4] == 420          # Mayıs
    assert m["hucreler"][0][0] is None         # Ocak verisiz
