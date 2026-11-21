"""Faz 0 §24 R2 (21.11.2026) — tek platform sahibinin kilitlenmesi: hesap sınırı yalnız BAŞARISIZ denemeleri sayar; sunucu CLI çıkışları
(--iki-adim-sifirla, --kilit-ac) denetimli ve sır sızdırmaz. Test DB gerekir; sentetik hesaplar temizlenir."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import uuid

import pyotp
import pytest
from sqlalchemy import text

from tests.test_faz0_platform_kurtarma_a3 import (
    sahip,  # noqa: F401 — 2FA'lı sentetik sahip fixture'ı (temizliği kendi yapar)
)

pytestmark = pytest.mark.skipif(not os.environ.get("PVQ_DB_URL"), reason="test DB gerekir")
KOK = pathlib.Path(__file__).resolve().parents[1]


def _istemci(monkeypatch, giris):
    from fastapi.testclient import TestClient

    from apps.api import main as api_main
    from apps.api import yonetim as yo
    from pvquant.services import platform_service as ps
    monkeypatch.setattr(yo, "paylasimli_sinir", lambda *a, **k: None)   # IP sınırı dışarıda; yalnız hesap sınırı gerçek sayaçla
    monkeypatch.setattr(yo.limiter, "enabled", False)
    monkeypatch.setattr(ps, "giris", giris)
    monkeypatch.setattr(yo.dz, "kaydet", lambda *a, **k: True)
    return TestClient(api_main.app)


def test_1_hesap_siniri_yalniz_basarisizlik_sayar_ve_cli_kilit_acar(monkeypatch):
    from pvquant.services import kullanim_service as ks
    from pvquant.services import platform_service as ps
    e = f"faz0r2-{uuid.uuid4().hex[:6]}@example.invalid"
    anahtar = ks.hesap_anahtari(ps.HESAP_SINIR_AD, e)
    def _giris(email, sifre, kod=None):
        if sifre == "dogru" and kod is None:
            return {"iki_adim_gerekli": True}            # parola doğru, kod bekleniyor → başarısızlık DEĞİL
        return {"token": "t", "rol": "sahip", "email": email, "iki_adim_kurulmali": False, "ikinci_adim": "totp"} if sifre == "dogru" else None
    c = _istemci(monkeypatch, _giris)
    try:
        # 15 başarılı giriş + 5 «kod bekleniyor» → sayaç 0 (eski davranışta 20 deneme kilitlerdi)
        assert all(c.post("/v1/yonetim/giris", json={"email": e, "sifre": "dogru", "kod": "1"}).status_code == 200 for _ in range(15))
        assert all(c.post("/v1/yonetim/giris", json={"email": e, "sifre": "dogru"}).status_code == 200 for _ in range(5))
        assert ks.pencere_oku(anahtar, 900) == 0
        # 10 başarısız → 11. deneme 429; e-posta büyük harf/boşluk aynı anahtar
        kodlar = [c.post("/v1/yonetim/giris", json={"email": e if i % 2 else f" {e.upper()} ", "sifre": "yanlis"}).status_code for i in range(11)]
        assert kodlar == [401] * 10 + [429]
        assert ks.pencere_oku(anahtar, 900) == 10
        # kilitliyken doğru parola da 429 (uzaktan kilitleme olgusu) → CLI kilit açma → doğru giriş 200
        assert c.post("/v1/yonetim/giris", json={"email": e, "sifre": "dogru", "kod": "1"}).status_code == 429
        assert ps.kilit_ac_cli(e) >= 1
        assert c.post("/v1/yonetim/giris", json={"email": e, "sifre": "dogru", "kod": "1"}).status_code == 200
        assert ks.pencere_oku(anahtar, 900) == 0                                             # başarılı giriş sayaca girmedi
    finally:
        ks.pencere_sil(anahtar)


def test_2_var_olmayan_hesap_da_sayilir_varlik_sizmaz(monkeypatch):
    from pvquant.services import kullanim_service as ks
    from pvquant.services import platform_service as ps
    e = f"faz0r2-yok-{uuid.uuid4().hex[:6]}@example.invalid"
    c = _istemci(monkeypatch, lambda email, sifre, kod=None: None)
    try:
        kodlar = [c.post("/v1/yonetim/giris", json={"email": e, "sifre": "x"}).status_code for _ in range(11)]
        assert kodlar == [401] * 10 + [429]
    finally:
        ks.pencere_sil(ks.hesap_anahtari(ps.HESAP_SINIR_AD, e))


def test_3_iki_adim_sifirla_cli_sir_ve_kodlari_siler_oturumlari_dusurur(sahip):   # noqa: F811 — içe aktarılan fixture
    from fastapi.testclient import TestClient

    from apps.api import main as api_main
    from pvquant.db import sistem_baglami
    from pvquant.services import platform_service as ps
    pid, email, parola, secret = sahip["pid"], sahip["email"], sahip["parola"], sahip["secret"]
    jeton = ps.giris(email, parola, pyotp.TOTP(secret).at(int(__import__("time").time()) + 30))["token"]
    c = TestClient(api_main.app)
    assert c.get("/v1/yonetim/ben", headers={"Authorization": f"Bearer {jeton}"}).status_code == 200
    assert ps.iki_adim_sifirla_cli(email.upper()) == pid                                    # normalize
    with sistem_baglami() as s:
        r = s.execute(text("SELECT totp_aktif, totp_secret, totp_zarf, totp_son_adim FROM platform_kullanicilar WHERE id=:i"), {"i": pid}).first()
        assert (r.totp_aktif, r.totp_secret, r.totp_zarf, r.totp_son_adim) == (False, None, None, None)
        assert s.execute(text("SELECT count(*) FROM platform_kurtarma_kodlari WHERE platform_user_id = CAST(:p AS uuid)"), {"p": pid}).scalar() == 0
    assert c.get("/v1/yonetim/ben", headers={"Authorization": f"Bearer {jeton}"}).status_code == 401   # açık oturum düştü
    g = ps.giris(email, parola)                                                               # parola AYNI; kurulum zorunlu
    assert g is not None and g.get("iki_adim_kurulmali") is True and g.get("ikinci_adim") is None
    g2 = ps.giris(email, parola, sahip["kodlar"][0])                                         # 2FA kapalı: kod yok sayılır, kurtarma DEĞİL
    assert g2 is not None and g2.get("ikinci_adim") is None and g2.get("iki_adim_kurulmali") is True
    assert ps.kurtarma_kalan(pid) == 0
    with pytest.raises(ps.PlatformHata, match="etkin hesap"):
        ps.iki_adim_sifirla_cli(f"yok-{email}")


def test_4_cli_betigi_onay_ister_ve_denetim_izi_sir_tasimaz(sahip):   # noqa: F811
    from pvquant.db import bakim_baglami, sistem_baglami
    email = sahip["email"]
    env = {**os.environ, "PYTHONPATH": f"{KOK / 'src'}{os.pathsep}{KOK}"}
    def kos(*args, girdi):
        return subprocess.run([sys.executable, str(KOK / "scripts" / "platform_sahip.py"), *args], input=girdi, capture_output=True, text=True, env=env, cwd=KOK, timeout=120)
    r = kos("--kilit-ac", email, girdi="HAYIR\n")
    assert r.returncode == 1 and "vazgeçildi" in r.stdout
    r = kos("--kilit-ac", email, girdi="")                                                     # QA İ-4: EOF → traceback yok
    assert r.returncode == 1 and "vazgeçildi" in r.stdout and "Traceback" not in r.stderr
    r = kos("--iki-adim-sifirla", f"yok-{email}", girdi="EVET\n")                              # QA İ-4: yok hesap → okunur hata + iz
    assert r.returncode == 1 and "hata: etkin hesap" in r.stdout and "Traceback" not in r.stderr
    r = kos("--kilit-ac", email, girdi="EVET\n")
    assert r.returncode == 0 and "kilit açıldı" in r.stdout, r.stdout + r.stderr
    r = kos("--iki-adim-sifirla", email, girdi="EVET\n")
    assert r.returncode == 0 and "2FA sıfırlandı" in r.stdout, r.stdout + r.stderr
    assert kos("--kilit-ac", "--iki-adim-sifirla", email, girdi="EVET\n").returncode == 1   # iki bayrak birden → kullanım hatası
    with sistem_baglami() as s:
        izler = s.execute(text("SELECT eylem, ayrinti::text FROM denetim_izi WHERE kapsam='platform' AND eylem IN ('kilit_ac_cli','iki_adim_sifirla_cli') "
                               "AND ayrinti->>'email' = :e ORDER BY zaman"), {"e": email}).all()
    assert [i.eylem for i in izler] == ["kilit_ac_cli", "iki_adim_sifirla_cli"]
    with sistem_baglami() as s:
        hata_iz = s.execute(text("SELECT count(*) FROM denetim_izi WHERE eylem='cli_hata' AND ayrinti->>'komut'='--iki-adim-sifirla' AND ayrinti->>'neden' LIKE 'etkin hesap%'")).scalar()
    assert hata_iz >= 1
    duz = " ".join(i.ayrinti for i in izler)
    assert sahip["secret"] not in duz and sahip["parola"] not in duz and all(k not in duz for k in sahip["kodlar"])
    with bakim_baglami() as s:                                                                # aktor_eposta 'cli' → fixture temizliği yakalamaz
        s.execute(text("DELETE FROM denetim_izi WHERE eylem IN ('kilit_ac_cli','iki_adim_sifirla_cli') AND ayrinti->>'email' = :e"), {"e": email})
        s.execute(text("DELETE FROM denetim_izi WHERE eylem='cli_hata' AND aktor_eposta='cli' AND zaman > now() - interval '10 minutes'"))


def test_5_pinler_anahtar_ve_eylem_adlari():
    from apps.api import yonetim as yo
    from pvquant.services import denetim_service as dz
    from pvquant.services import platform_service as ps
    assert yo.HESAP_SINIR_AD == ps.HESAP_SINIR_AD == "ygiris-hesap"
    assert {"parola_sifirla_cli", "iki_adim_sifirla_cli", "kilit_ac_cli"} <= set(dz.EYLEMLER_PLATFORM)
    sozluk = (KOK / "web/src/lib/sozluk.ts").read_text(encoding="utf-8")
    assert "iki_adim_sifirla_cli:" in sozluk and "kilit_ac_cli:" in sozluk


def test_6_es_zamanli_basarisiz_denemeler_tavani_asamaz(monkeypatch):
    """QA R2 İ-1: oku→artır yarışında 20 eş zamanlı yanlış parola 20×401 geçiyordu. Atomik rezerve ile tam 10×401 + 10×429, sayaç 10."""
    from concurrent.futures import ThreadPoolExecutor

    from pvquant.services import kullanim_service as ks
    from pvquant.services import platform_service as ps
    e = f"faz0r2-yaris-{uuid.uuid4().hex[:6]}@example.invalid"
    anahtar = ks.hesap_anahtari(ps.HESAP_SINIR_AD, e)
    c = _istemci(monkeypatch, lambda email, sifre, kod=None: None)
    try:
        with ThreadPoolExecutor(max_workers=20) as ex:
            kodlar = sorted(ex.map(lambda _: c.post("/v1/yonetim/giris", json={"email": e, "sifre": "yanlis"}).status_code, range(20)))
        assert kodlar == [401] * 10 + [429] * 10
        assert ks.pencere_oku(anahtar, 900) == 10                                               # reddedilenler sayılmadı
        # başarılı deneme rezervi geri alır: kilit varken 429 (sayaç 10 kalır); kilit açılınca doğru giriş sayaca girmez
        assert ps.kilit_ac_cli(e) >= 1
        monkeypatch.setattr(ps, "giris", lambda email, sifre, kod=None: {"token": "t", "rol": "sahip", "email": email, "iki_adim_kurulmali": False})
        assert c.post("/v1/yonetim/giris", json={"email": e, "sifre": "dogru"}).status_code == 200
        assert ks.pencere_oku(anahtar, 900) == 0
    finally:
        ks.pencere_sil(anahtar)


def test_7_kurulum_uclarinda_onbellek_atlanir(sahip, monkeypatch):   # noqa: F811
    """QA R2 İ-2: CLI ayrı süreçte sürümü artırır; kurulum uçları 60 sn önbellekle eski jetonu kabul ediyordu. Önbellek dolu bırakılıp
    sürüm DB'de artırılır (ayrı süreç taklidi): kurulum ucu (/ben) anında 401, önbellek düşürülmeden."""
    from fastapi.testclient import TestClient

    from apps.api import main as api_main
    from pvquant.db import bakim_baglami
    from pvquant.services import platform_service as ps
    pid, email, parola, secret = sahip["pid"], sahip["email"], sahip["parola"], sahip["secret"]
    jeton = ps.giris(email, parola, pyotp.TOTP(secret).at(int(__import__("time").time()) + 30))["token"]
    c = TestClient(api_main.app)
    h = {"Authorization": f"Bearer {jeton}"}
    assert c.get("/v1/yonetim/ben", headers=h).status_code == 200                              # önbellek doldu
    with bakim_baglami() as s:                                                                  # başka süreç: sürüm artar, bu sürecin önbelleği düşmez
        s.execute(text("UPDATE platform_kullanicilar SET oturum_surumu = oturum_surumu + 1 WHERE id=:i"), {"i": pid})
    assert c.get("/v1/yonetim/ben", headers=h).status_code == 401                              # kurulum ucu: taze okuma → anında düşer
    assert c.post("/v1/yonetim/iki-adim/baslat", headers=h).status_code == 401
