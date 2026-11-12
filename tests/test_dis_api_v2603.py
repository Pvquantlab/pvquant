"""v2.603 (Faz 4 F4-I, Stage 11) — kurumsal API: santral kapsamı (api_keys.plant_ids), yeni kapsamlar ve uçlar (tahmin arşivi, kalite, portföyler,
portföy finansal etkisi), hata gövdesi {detail, kod, schema_version}, X-PVQuant-Schema başlığı, imleçli sayfalama, KGÜP yan etkisi POST'ta.
Negatif testler GERÇEK DB ile: kiracılar arası santral, kapsam dışı santral, kapsam eksik, süresi dolmuş, iptal edilmiş, bozuk anahtar."""
from __future__ import annotations

import uuid
from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import apps.api.main as api_main
from pvquant.db import bakim_baglami, sistem_baglami
from pvquant.services import api_anahtar_service as ak
from pvquant.services import denetim_service as dz
from pvquant.services import portfoy_varlik_service as pv

TZ = "Europe/Istanbul"
KAPS = ["tahmin:oku", "kgup:oku", "veri_kalitesi:oku", "portfoy:oku", "finans:oku"]


@pytest.fixture()
def ortam(monkeypatch):
    """İki kiracı; kiracı 1'de iki santral (A ölçümlü) ve üç portföy; anahtarlar: A-kapsamlı, tüm-santral dar kapsamlı, süresi dolmuş, iptal."""
    monkeypatch.setattr(ak, "_paylasimli_izin", lambda p, r, t: ak._kova_izin(p, r))   # hız penceresi DB'siz (test); doğrulama/kapsam/santral gerçek DB
    t1, t2 = str(uuid.uuid4()), str(uuid.uuid4())
    a, b, c = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        for t, ad in ((t1, "dis-1"), (t2, "dis-2")):
            s.execute(text("INSERT INTO tenants(id, name, status) VALUES(:t, :n, 'active')"), {"t": t, "n": ad})
        for pid, t, ad in ((a, t1, "A GES"), (b, t1, "B GES"), (c, t2, "C GES")):
            s.execute(text("INSERT INTO plants(id, tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(:p, :t, :n, 1000, 37.0, 32.0, :tz, '{\"segment\": \"lisansli_serbest\"}')"),
                      {"p": pid, "t": t, "n": ad, "tz": TZ})
        gun0 = pd.Timestamp("2026-10-01", tz=TZ)
        for h in range(48):   # 1–2 Ekim 2026: 48 saat; 4'ü donuk, 2'si kısıntı
            ts = (gun0 + pd.Timedelta(hours=h)).tz_convert("UTC").to_pydatetime()
            flag = "frozen_value" if h in (10, 11, 12, 13) else ("kisinti" if h in (30, 31) else "valid")
            s.execute(text("INSERT INTO scada_hourly(tenant_id, plant_id, ts_utc, power_kw, energy_kwh, flag, kapsama_dk, kaynak, alinma_zamani) "
                           "VALUES(:t, :p, :ts, 100, 100, :f, 60, 'scada_dosya', '2026-10-03 08:00+00')"), {"t": t1, "p": a, "ts": ts, "f": flag})
    for ad in ("P1", "P2", "P3"):
        pv.portfoy_ekle(t1, f"{ad}-{t1[:6]}", "isletme", date(2026, 1, 1))
    k_a = ak.uret(t1, "A", KAPS, plant_ids=[a])
    k_dar = ak.uret(t1, "dar", ["tahmin:oku"])
    k_eski = ak.uret(t1, "eski", KAPS, gecerlilik_gun=1)
    k_iptal = ak.uret(t1, "iptal", KAPS)
    ak.iptal(t1, k_iptal["id"])
    with sistem_baglami() as s:
        s.execute(text("UPDATE api_keys SET expires_at = now() - interval '1 day' WHERE id = :i"), {"i": k_eski["id"]})
    yield {"t1": t1, "t2": t2, "a": a, "b": b, "c": c, "k_a": k_a["anahtar"], "k_dar": k_dar["anahtar"], "k_eski": k_eski["anahtar"], "k_iptal": k_iptal["anahtar"],
           "k_a_id": k_a["id"]}
    _temizle(t1, t2)


def _temizle(*tenants):
    for tb in ("kullanim_sayac",):   # tenant_id'li kullanım sayacı; ayrı işlemde (başarısız DELETE ana temizliği bozmasın)
        try:
            with bakim_baglami() as s:
                for t in tenants:
                    s.execute(text(f"DELETE FROM {tb} WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
        except Exception:   # noqa: BLE001
            pass
    with bakim_baglami() as s:
        for t in tenants:
            s.execute(text("DELETE FROM api_keys WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
            s.execute(text("DELETE FROM denetim_izi WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
            s.execute(text("DELETE FROM portfoy_uyelik WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
            s.execute(text("DELETE FROM portfoy WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
            s.execute(text("DELETE FROM scada_hourly WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
            s.execute(text("DELETE FROM plants WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
            s.execute(text("DELETE FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": t})


def _c():
    return TestClient(api_main.app)


def test_anahtar_servisi_santral_kapsami(ortam):
    o = ortam
    with pytest.raises(ValueError, match="bu kiracıda yok"):
        ak.uret(o["t1"], "x", ["tahmin:oku"], plant_ids=[o["c"]])   # başka kiracının santrali
    with pytest.raises(ValueError, match="geçersiz"):
        ak.uret(o["t1"], "x", ["tahmin:oku"], plant_ids=["uuid-degil"])
    with pytest.raises(ValueError, match="bilinmeyen kapsam"):
        ak.uret(o["t1"], "x", ["finans:yaz"])
    l = {x["id"]: x for x in ak.listele(o["t1"])}
    assert l[o["k_a_id"]]["plant_ids"] == [o["a"]] and all(v["plant_ids"] is None for k, v in l.items() if k != o["k_a_id"])
    d = ak.dogrula(o["k_a"], "tahmin:oku")
    assert d["plant_ids"] == [o["a"]] and ak.santral_izinli(d, o["a"]) and not ak.santral_izinli(d, o["b"]) and ak.santral_izinli({"plant_ids": None}, o["b"])


def test_db_negatifler_hata_sozlugu_ve_sema(ortam):
    o = ortam; c = _c(); H = {"X-API-Key": o["k_a"]}
    # santral kapsamı: liste süzülür; B 403 santral_kapsam_disi; başka kiracının C 404 santral_yok
    r = c.get("/v1/dis/santraller", headers=H); assert r.status_code == 200 and [x["id"] for x in r.json()] == [o["a"]] and r.headers["X-PVQuant-Schema"] == api_main.DIS_API_SEMA
    r = c.get(f"/v1/dis/santral/{o['b']}/kalite", headers=H); assert r.status_code == 403 and r.json() == {"detail": "santral bu anahtarın kapsamında değil", "kod": "santral_kapsam_disi", "schema_version": api_main.DIS_API_SEMA}
    r = c.get(f"/v1/dis/santral/{o['c']}/kalite", headers=H); assert r.status_code == 404 and r.json()["kod"] == "santral_yok" and r.headers["X-PVQuant-Schema"]
    # kapsam eksik / süresi dolmuş / iptal / bozuk / başlık yok
    r = c.get(f"/v1/dis/santral/{o['a']}/kalite", headers={"X-API-Key": o["k_dar"]}); assert r.status_code == 403 and r.json()["kod"] == "kapsam_yetersiz"
    for k in (o["k_eski"], o["k_iptal"], "pvq_bozuk", o["k_a"][:-3] + "xyz"):
        r = c.get(f"/v1/dis/santral/{o['a']}/kalite", headers={"X-API-Key": k}); assert r.status_code == 401 and r.json()["kod"] == "anahtar_gecersiz", k
    r = c.get(f"/v1/dis/santral/{o['a']}/kalite"); assert r.status_code == 422 and r.json()["kod"] == "istek_gecersiz" and r.json()["alanlar"][0]["konum"][-1] == "X-API-Key"
    # panel yolu değişmedi: FastAPI varsayılan gövdesi (kod yok)
    r = c.get("/v1/plants"); assert r.status_code in (401, 403, 422) and "kod" not in r.json() and "X-PVQuant-Schema" not in r.headers   # panel: FastAPI varsayılanı
    # kod eşlemesi dizgi detaylı 409 (koşu yok) ve 422
    r = c.get(f"/v1/dis/santral/{o['a']}/tahmin", headers=H); assert r.status_code == 409 and r.json()["kod"] == "kosu_yok"
    r = c.post(f"/v1/dis/santral/{o['a']}/kgup", json={"fmt": "xml"}, headers=H); assert r.status_code == 422 and r.json()["kod"] == "istek_gecersiz"
    r = c.get(f"/v1/dis/santral/{o['a']}/tahmin-arsivi?hedef=2026-10-01T10:00:00Z", headers=H); assert r.status_code == 404 and r.json()["kod"] == "kosu_yok"
    r = c.get(f"/v1/dis/santral/{o['a']}/tahmin-arsivi?hedef=bozuk", headers=H); assert r.status_code == 422 and r.json()["kod"] == "istek_gecersiz"


def test_db_kalite_ozeti(ortam):
    o = ortam; c = _c(); H = {"X-API-Key": o["k_a"]}
    r = c.get(f"/v1/dis/santral/{o['a']}/kalite?bas=2026-10-01&bit=2026-10-02", headers=H); assert r.status_code == 200, r.text
    j = r.json()
    assert j["schema_version"] == api_main.DIS_API_SEMA and j["beklenen_saat"] == 48 and j["olcumlu_saat"] == 48 and j["eksik_saat"] == 0
    from pvquant.services import kalite_sozlugu as ks
    assert j["bayrak"] == {"valid": 42, "frozen_value": 4, "kisinti": 2}
    assert j["uzlastirmaya_uygun_saat"] == sum(n for f, n in j["bayrak"].items() if f in ks.gecerli_flaglar("uzlastirma")) == (44 if "kisinti" in ks.gecerli_flaglar("uzlastirma") else 42)
    assert j["nitelik"]["olculmus"] == 44 and j["nitelik"]["supheli"] == 4 and sum(j["nitelik"].values()) == 48 and j["tazelik"]["kod"] == "gecikmis" and j["tazelik"]["yas_saat"] > 24
    assert j["kunye"]["kaynaklar"] == ["scada_dosya"] and j["kunye"]["son_alinma"].startswith("2026-10-03T08:00") and j["kunye"]["son_gecerli_olcum"].startswith("2026-10-02T20:00")
    r = c.get(f"/v1/dis/santral/{o['a']}/kalite?bas=2026-10-01&bit=2027-01-05", headers=H); assert r.status_code == 422 and r.json()["kod"] == "istek_gecersiz"
    j2 = c.get(f"/v1/dis/santral/{o['a']}/kalite?bas=2026-11-01&bit=2026-11-02", headers=H).json()
    assert j2["olcumlu_saat"] == 0 and j2["eksik_saat"] == 48 and j2["bayrak"] == {} and j2["kunye"]["kaynaklar"] == [] and j2["kunye"]["son_alinma"] is None   # künye pencere içi
    assert j2["tazelik"]["kod"] == "gecikmis" and j2["kunye"]["son_gecerli_olcum"].startswith("2026-10-02T20:00")   # tazelik santralın tamamından


def test_db_portfoyler_sayfalama_ve_finansal_etki(ortam):
    o = ortam; c = _c(); H = {"X-API-Key": o["k_a"]}
    r = c.get("/v1/dis/portfoyler?n=2&tarih=2026-06-01", headers=H); assert r.status_code == 200, r.text
    j = r.json(); assert len(j["portfoyler"]) == 2 and j["sonraki"] == j["portfoyler"][-1]["id"] and j["tarih"] == "2026-06-01"
    r2 = c.get(f"/v1/dis/portfoyler?n=2&tarih=2026-06-01&sonraki={j['sonraki']}", headers=H).json()
    assert len(r2["portfoyler"]) == 1 and r2["sonraki"] is None and r2["portfoyler"][0]["id"] > j["sonraki"]
    ids = [x["id"] for x in j["portfoyler"]] + [x["id"] for x in r2["portfoyler"]]
    assert len(set(ids)) == 3 and all(x["tur"] == "isletme" and x["uye_sayisi"] == 0 for x in j["portfoyler"])
    assert c.get("/v1/dis/portfoyler?tarih=2025-01-01", headers=H).json()["portfoyler"] == []   # geçerlilik öncesi
    assert c.get("/v1/dis/portfoyler", headers={"X-API-Key": o["k_dar"]}).status_code == 403
    r = c.get(f"/v1/dis/portfoy/{ids[0]}/finansal-etki?donem=2026-09", headers=H); assert r.status_code == 409 and r.json()["kod"] == "hesaplanamadi"   # üye yok
    r = c.get(f"/v1/dis/portfoy/{uuid.uuid4()}/finansal-etki?donem=2026-09", headers=H); assert r.status_code == 404 and r.json()["kod"] == "portfoy_yok"
    r = c.get(f"/v1/dis/portfoy/{ids[0]}/finansal-etki?donem=2026-09", headers={"X-API-Key": o["k_dar"]}); assert r.status_code == 403 and r.json()["kod"] == "kapsam_yetersiz"


def test_db_anahtar_uret_izi_plant_ids(ortam):
    o = ortam
    izler = dz.listele(tenant_id=o["t1"], eylem="anahtar_uret")
    assert izler == []   # servis doğrudan çağrıldı (API ucu iz bırakır); kapsam kaydı API gövdesinde
    from apps.api.deps import gecerli_kullanici
    api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": str(uuid.uuid4()), "tenant_id": o["t1"], "role": "admin", "exp": 0}
    try:
        r = _c().post("/v1/api-anahtarlari", json={"ad": "k", "kapsamlar": ["tahmin:oku"], "plant_ids": [o["b"]]}); assert r.status_code == 201, r.text
        assert r.json()["plant_ids"] == [o["b"]] and r.json()["anahtar"].startswith("pvq_")
        iz = dz.listele(tenant_id=o["t1"], eylem="anahtar_uret")[0]
        assert iz["ayrinti"]["plant_ids"] == [o["b"]] and "anahtar" not in iz["ayrinti"]
        assert _c().post("/v1/api-anahtarlari", json={"ad": "k", "kapsamlar": ["tahmin:oku"], "plant_ids": [o["c"]]}).status_code == 422
    finally:
        api_main.app.dependency_overrides.clear()
