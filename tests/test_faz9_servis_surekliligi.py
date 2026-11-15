"""Faz 9 (14.11.2026) — F alanı: servis sürekliliği göstergelerinin «sistem görevi başarılı ≠ müşteri güncel veri görüyor» sınaması.

Çekirdeğe dokunmaz. Bölüm 1 (DB'siz/alt süreç): healthz DB erişilemezken de 200; DB kesintisinde kimlikli uç 5xx (sahte başarı yok).
Bölüm 2 (test DB): `_logla_tek` None dönen işi «ok» yazar (kapalı yedek, kısmi meteo «başarılı» görünür) — jobs_log tabanlı başarı oranının
payını şişirir; satır `faz9_` önekli iş adıyla yazılır ve silinir.
Ölçüt bağları: F-Z1 iş başarı oranı (pay/payda) · F-B3 API erişilebilirliği (healthz anlamı) · F-B4 yedek başarısı · F-Z2 hata davranışı.
Koşu: PVQ_DB_URL=<test DB> PYTHONPATH=src .venv/bin/python3 -m pytest -q -p no:cacheprovider tests/test_faz9_servis_surekliligi.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import uuid

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _alt_surec(kod: str, db_url: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PVQ_DB_URL": db_url, "PYTHONPATH": os.path.join(KOK, "src") + os.pathsep + KOK, "PVQ_JWT_SECRET": "faz9-test-sirri-0123456789abcdef"}
    return subprocess.run([sys.executable, "-c", textwrap.dedent(kod)], cwd=KOK, env=env, capture_output=True, text=True, timeout=120)


KAPALI_DB = "postgresql+psycopg://x:y@127.0.0.1:1/yok?connect_timeout=2"


def test_healthz_db_erisilemezken_200():
    """F-B3 (K3 → K1, Yüksek): `/v1/healthz` DB'ye, worker nabzına ve diske bakmaz; DB kapalıyken de {"ok": true} döner. «API erişilebilirliği»
    ölçütü healthz ile ölçülürse gerçek kesintiyi göstermez (kanıt: kapalı porta bağlı alt süreç)."""
    r = _alt_surec("""
        from fastapi.testclient import TestClient
        import apps.api.main as m
        c = TestClient(m.app, raise_server_exceptions=False)
        y = c.get("/v1/healthz"); print("HEALTHZ", y.status_code, y.text)
        m.app.dependency_overrides[m.gecerli_kullanici] = lambda: {"sub": "u", "tenant_id": "00000000-0000-0000-0000-000000000001", "role": "admin", "exp": 0}
        y = c.get("/v1/plants"); print("PLANTS", y.status_code)
    """, KAPALI_DB)
    assert "HEALTHZ 200" in r.stdout, r.stdout + r.stderr
    plants = [x for x in r.stdout.splitlines() if x.startswith("PLANTS")]
    assert plants and int(plants[0].split()[1]) >= 500, r.stdout + r.stderr[-2000:]   # F-Z2: DB yokken sahte boş 200 yok


def test_gece_yedek_kapaliyken_none_doner(monkeypatch, tmp_path):
    """F-B4 (K3 → K1): PVQ_YEDEK_KAPALI doluysa `gece_yedek()` hiçbir şey yazmadan None döner. `_logla_tek` None'ı «ok» kaydeder
    (aşağıdaki DB testi) → yedek kapalıyken iş başarı oranı %100 görünür."""
    monkeypatch.setenv("PVQ_YEDEK_KAPALI", "1")
    import apps.worker.main as w
    assert w.gece_yedek() is None


def _db_var() -> bool:
    try:
        from sqlalchemy import text

        from pvquant.db import sistem_baglami
        with sistem_baglami() as s:
            s.execute(text("SELECT 1"))
        return True
    except Exception: 
        return False


@pytest.mark.skipif(not _db_var(), reason="test DB yok")
def test_logla_tek_none_donen_isi_ok_yazar():
    """F-Z1 (K3 → K1, Yüksek): iş başarı oranı = jobs_log status='ok' / tüm satırlar ise, «hiçbir şey yapmadan dönen» iş (None) pay'a
    girer. Ölçüt tanımı bu yüzden «ok ∧ (detail ∨ sonuc_json dolu) ∨ beklenen çıktı tablosunda yeni satır» olmalı (02, F-Z1)."""
    from sqlalchemy import text

    import apps.worker.main as w
    from pvquant.db import sistem_baglami
    ad = f"faz9_{uuid.uuid4().hex[:8]}"
    try:
        w._logla_tek(ad, lambda: None)()
        w._logla_tek(ad + "_hata", lambda: (_ for _ in ()).throw(RuntimeError("faz9 sentetik")))()
        with sistem_baglami() as s:
            r = {x.job: (x.status, x.detail) for x in s.execute(text("SELECT job, status, detail FROM jobs_log WHERE job LIKE :j"), {"j": ad + "%"})}
        assert r[ad] == ("ok", "")
        assert r[ad + "_hata"][0] == "error" and "faz9 sentetik" in r[ad + "_hata"][1]
    finally:
        with sistem_baglami() as s:
            s.execute(text("DELETE FROM jobs_log WHERE job LIKE :j"), {"j": ad + "%"})
