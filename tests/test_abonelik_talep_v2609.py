"""v2.609 (Faz 6 F6-D) — teklif / yükseltme talebi: `basvuru_service.talep_kaydet` (vitrin_basvurulari, kaynak yukseltme | sanayi_ges, e-posta kullanıcıdan,
kurulu güç kiracı toplamı), `POST /v1/abonelik/talep` (viewer 403, tür doğrulama 422, denetim izi mesajla), platform listesi kaynak etiketi."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from pvquant.db import bakim_baglami, sistem_baglami
from pvquant.services import basvuru_service as bs


@pytest.fixture()
def kiraci():
    t, u = str(uuid.uuid4()), str(uuid.uuid4())
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO tenants(id, name, status, plan) VALUES(:t, 'TL Kuruluş', 'active', 'pilot')"), {"t": t})
        s.execute(text("INSERT INTO users(id, tenant_id, email, pw_hash, role, aktif) VALUES(:u, CAST(:t AS uuid), :e, 'x', 'admin', true)"), {"u": u, "t": t, "e": f"tl-{t[:8]}@pvq.test"})
        s.execute(text("INSERT INTO plants(tenant_id, name, capacity_kwp, lat, lon, tz, params_json) VALUES(CAST(:t AS uuid), 'TL A', 1500, 37, 32, 'Europe/Istanbul', '{}'), (CAST(:t AS uuid), 'TL B', 500, 37, 32, 'Europe/Istanbul', '{}')"), {"t": t})
    yield t, u
    with bakim_baglami() as s:
        s.execute(text("DELETE FROM vitrin_basvurulari WHERE eposta LIKE :e"), {"e": f"tl-{t[:8]}%"})
        s.execute(text("DELETE FROM denetim_izi WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
        for tbl in ("plants", "users"):
            s.execute(text(f"DELETE FROM {tbl} WHERE tenant_id = CAST(:t AS uuid)"), {"t": t})
        s.execute(text("DELETE FROM tenants WHERE id = CAST(:t AS uuid)"), {"t": t})


def test_talep_kaydet_ve_liste(kiraci):
    t, u = kiraci
    y = bs.talep_kaydet(t, u, "modul", "finansal_etki", "deneme")
    assert y["tamam"] and y["kaynak"] == "yukseltme" and y["eposta"].startswith("tl-")
    y2 = bs.talep_kaydet(t, u, "sanayi_ges", None, None)
    assert y2["kaynak"] == "sanayi_ges"
    with pytest.raises(ValueError):
        bs.talep_kaydet(t, u, "satin_al", None, None)
    with pytest.raises(ValueError):
        bs.talep_kaydet(t, u, "modul", "bedava", None)                                           # öz inceleme: hedef sözlükten
    with pytest.raises(ValueError):
        bs.talep_kaydet(t, u, "plan", "altin", None)
    assert bs.talep_kaydet(t, u, "diger", "serbest konu", None)["kaynak"] == "yukseltme"        # diğer: serbest metin
    with pytest.raises(LookupError):
        bs.talep_kaydet(t, str(uuid.uuid4()), "plan", "standart", None)                      # başka kiracının/olmayan kullanıcı
    liste = [b for b in bs.listele(50) if b["id"] in (y["id"], y2["id"])]
    assert {b["kaynak"] for b in liste} == {"yukseltme", "sanayi_ges"} and {b["kaynak_etiketi"] for b in liste} == {"yükseltme talebi", "Sanayi GES talebi"}
    b = next(x for x in liste if x["id"] == y["id"])
    assert b["santral_adi"] == "TL Kuruluş · modül: finansal_etki" and b["kurulu_guc_kwp"] == 2000.0 and b["okundu"] is False   # kiracı toplam kWp


def test_uc(kiraci, monkeypatch):
    from fastapi.testclient import TestClient

    import apps.api.main as api_main
    from apps.api.deps import gecerli_kullanici
    from pvquant.services import denetim_service as dz
    t, u = kiraci
    kayit = []
    monkeypatch.setattr(dz, "kaydet", lambda *a, **k: kayit.append((a, k)) or True)
    monkeypatch.setattr(api_main, "paylasimli_sinir", lambda *a, **k: None)
    c = TestClient(api_main.app)
    try:
        api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": u, "tenant_id": t, "role": "viewer", "exp": 0}
        assert c.post("/v1/abonelik/talep", json={"tur": "plan", "hedef": "standart"}).status_code == 403          # viewer yazamaz
        api_main.app.dependency_overrides[gecerli_kullanici] = lambda: {"sub": u, "tenant_id": t, "role": "admin", "exp": 0}
        assert c.post("/v1/abonelik/talep", json={"tur": "satin_al"}).status_code == 422
        assert c.post("/v1/abonelik/talep", json={"tur": "plan", "hedef": "x" * 80}).status_code == 422               # uzunluk
        y = c.post("/v1/abonelik/talep", json={"tur": "plan", "hedef": "standart", "mesaj": "yıl sonuna kadar"})
        assert y.status_code == 201 and y.json()["kaynak"] == "yukseltme"
        assert kayit[-1][0][1] == "abonelik_talep" and kayit[-1][1]["ayrinti"]["mesaj"] == "yıl sonuna kadar" and kayit[-1][1]["nesne_id"] == y.json()["id"]
    finally:
        api_main.app.dependency_overrides.clear()
