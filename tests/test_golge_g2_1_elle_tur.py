"""Faz 1 G2-1 (26.11.2026) — ELLE gölge turu (`golge_service.golge_turu`, `scripts/golge_tur.py`): zamanlayıcı yok.

- Kimlik: mod başına bağımsız run_id, etiket 'golge', mode/model/geri_dusus künyede; C artefaktsız → B düşüşü açık.
- Zaman: meteo BİR kez çekilir, bütün modlar aynı run_at (= yayın anı) ve aynı NWP koşu zamanı, aynı ufuk.
- İzolasyon: yalnız gölge koşuları varken müşteri son koşu/geçmiş/yayımlanmış koşu BOŞ; damga oynamaz; üretim yolu çağrılmaz.
- Hata: bir mod düşerse diğerleri yazılır, hata metni `hatalar`'da; kuru koşu yazmaz.
- Geriye uyum: `uret_ve_kaydet` imzası ve davranışı değişmedi; worker/API gölge turunu çağırmaz.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_kosu_kunyesi_v2572 import (  # noqa: F401 — DB fixture'ı (tenant+plant+kalibrasyon B; teardown siler)
    _sentetik_meteo,
    santral,
)

from pvquant.db import sistem_baglami
from pvquant.services import damga_service as ds
from pvquant.services import forecast_service as fs
from pvquant.services import golge_service as gs

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "scripts"))
import golge_tur  # noqa: E402


class _Meteo:
    """Sahte meteo istemcisi: çağrı sayar, sabit NWP koşu zamanı."""
    def __init__(self, bas: str, nwp: pd.Timestamp):
        self.bas, self.nwp, self.cagri = bas, nwp, 0

    def get_forecast(self, latitude, longitude, days):
        self.cagri += 1
        return _sentetik_meteo(self.bas, min(days, 3), kosu_zamani=self.nwp)


def _tur(tid, plant, simdi, **k):
    m = _Meteo(simdi.strftime("%Y-%m-%d"), simdi - pd.Timedelta(hours=6))
    t = gs.golge_turu(tid, plant, meteo_istemci=m, simdi=simdi, **k)
    return t, m


def _satirlar(tid):
    with sistem_baglami() as s:
        return s.execute(text("SELECT id, etiket, mode, model, run_at, ufuk_saat, nwp_kosu_zamani, kalibrasyon_id, ml_model_id, "
                              "veri_kalitesi_json->>'geri_dusus' AS gd, (SELECT count(*) FROM forecast_values v WHERE v.run_id = r.id) AS n "
                              "FROM forecast_runs r WHERE tenant_id = :t ORDER BY mode"), {"t": tid}).mappings().all()


def test_kimlik_ve_zaman_hizasi_abc(santral):   # noqa: F811
    tid, plant, cid = santral
    simdi = pd.Timestamp.now("UTC").floor("h")
    t, m = _tur(tid, plant, simdi)
    assert m.cagri == 1 and t.tam and t.kaydedildi and t.etiket == "golge" and set(t.sonuclar) == {"A", "B", "C"}
    idler = t.run_idler
    assert len(set(idler.values())) == 3 and all(idler.values())                                  # bağımsız kimlik
    rows = _satirlar(tid)   # C→B düşüşü yüzünden iki satır mode='B' → kimlik run_id ile, mode ile değil
    assert len(rows) == 3 and [x["etiket"] for x in rows] == ["golge", "golge", "golge"]
    assert {str(x["id"]) for x in rows} == set(idler.values())
    assert all(pd.Timestamp(x["run_at"]).tz_convert("UTC") == simdi for x in rows)              # aynı yayın anı
    assert all(pd.Timestamp(x["nwp_kosu_zamani"]).tz_convert("UTC") == m.nwp for x in rows)     # aynı meteo
    assert len({x["ufuk_saat"] for x in rows}) == 1 and rows[0]["ufuk_saat"] > 0                # aynı ufuk
    ra = next(x for x in rows if str(x["id"]) == idler["A"])
    rb = next(x for x in rows if str(x["id"]) == idler["B"])
    assert ra["kalibrasyon_id"] is None and str(rb["kalibrasyon_id"]) == cid and ra["mode"] == "A" and rb["mode"] == "B"   # A kalibrasyonsuz, B kalibre
    assert all(x["n"] > 0 for x in rows)
    # C: aktif artefakt yok → B'ye düşüş; künye ve sonuç bunu GİZLEMEZ (mode 'B' yazılır, geri_dusus dolu); dolayısıyla DB'de iki 'B' satırı
    c = t.sonuclar["C"]
    assert (c.mod, c.mode_gerceklesen, c.model_adi, c.geri_dusus) == ("C", "B", "barhdadi_bennis", "hibrit_artefakt_yok")
    with sistem_baglami() as s:
        modlar = s.execute(text("SELECT mode, veri_kalitesi_json->>'geri_dusus' FROM forecast_runs WHERE tenant_id=:t ORDER BY mode"), {"t": tid}).all()
    assert sorted(x[0] for x in modlar) == ["A", "B", "B"] and sorted(str(x[1]) for x in modlar) == ["None", "None", "hibrit_artefakt_yok"]


def test_izolasyon_yalniz_golge_varken_musteri_yuzeyleri_bos(santral):   # noqa: F811
    tid, plant, _ = santral
    simdi = pd.Timestamp.now("UTC").floor("h")
    t, _m = _tur(tid, plant, simdi, modlar=("A", "B"))
    assert t.tam and len(_satirlar(tid)) == 2
    assert fs.son_kosu(tid, plant["id"]) is None                                   # panel son koşu YOK
    assert fs.kosu_gecmisi(tid, plant["id"], n=10) == []                           # geçmiş tablosu BOŞ
    hedef = t.sonuclar["A"].h.index[30]
    assert fs.yayimlanmis_kosu(tid, plant["id"], hedef, yayin_oncesi=simdi + pd.Timedelta(minutes=5)) is None
    assert ds.hesapla(tid, plant["id"])["son_kosu"] is None                        # damga oynamadı


def test_hata_izolasyonu_bir_mod_duserse_digerleri_yazilir(santral, monkeypatch):   # noqa: F811
    tid, plant, _ = santral
    simdi = pd.Timestamp.now("UTC").floor("h")
    asil = gs.tahmin_uret

    def _patlak(plant_, meteo, girdi, simdi=None):
        if girdi.mode == "B":
            raise RuntimeError("B deneme hatası")
        return asil(plant_, meteo, girdi, simdi=simdi)
    monkeypatch.setattr(gs, "tahmin_uret", _patlak)
    t, _m = _tur(tid, plant, simdi)
    assert not t.tam and set(t.sonuclar) == {"A", "C"} and list(t.hatalar) == ["B"] and "RuntimeError: B deneme hatası" in t.hatalar["B"]
    assert len(_satirlar(tid)) == 2 and set(t.run_idler.values()) == {str(x["id"]) for x in _satirlar(tid)}


def test_kuru_kosu_yazmaz(santral):   # noqa: F811
    tid, plant, _ = santral
    t, m = _tur(tid, plant, pd.Timestamp.now("UTC").floor("h"), kaydet=False)
    assert m.cagri == 1 and t.tam and not t.kaydedildi and all(v is None for v in t.run_idler.values()) and _satirlar(tid) == []


def test_geriye_uyum_ve_zamanlayici_yok():
    assert str(inspect.signature(fs.uret_ve_kaydet)) == "(tenant_id, plant: 'dict', etiket: 'str | None' = None) -> 'str'"
    assert "golge" not in inspect.getsource(fs.uret_ve_kaydet)                      # üretim yolu dokunulmadı
    for yol in ("apps/worker/main.py", "apps/api/main.py"):
        metin = (KOK / yol).read_text()
        assert not any(k in metin for k in ("golge_turu", "golge_service", "golge_arsivle", "golge_tur")), yol   # zamanlayıcı/uç yok
    a = golge_tur.argumanlar(["--tenant", "t", "--plant", "p", "--modlar", "a, c", "--kuru"])
    assert (a.tenant, a.plant, a.modlar, a.kuru) == ("t", "p", ("A", "C"), True)
    assert golge_tur.argumanlar(["--tenant", "t", "--plant", "p"]).modlar == ("A", "B", "C")
    with pytest.raises(SystemExit):
        golge_tur.argumanlar(["--plant", "p"])
