"""Faz 0 C3-a hazırlık (21.11): A1 ikinci sahip + A2 sahip 2FA — mevcut yetki/kurtarma/kilitlenme davranışının YALITIK kanıtı
(test DB, sentetik hesaplar; canlı hesap yaratılmaz, 2FA zorlanmaz). Gerçek servis fonksiyonları, sahte kimlik yok."""
from __future__ import annotations

import os
import uuid

import pyotp
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.skipif(not os.environ.get("PVQ_DB_URL"), reason="test DB gerekir")


@pytest.fixture()
def hesaplar():
    from pvquant.db import bakim_baglami
    onek = f"faz0c3a-{uuid.uuid4().hex[:6]}"
    yield onek
    with bakim_baglami() as s:
        s.execute(text("DELETE FROM denetim_izi WHERE aktor_eposta LIKE :e OR ayrinti->>'email' LIKE :e"), {"e": onek + "%"})
        s.execute(text("DELETE FROM platform_kullanicilar WHERE email LIKE :e"), {"e": onek + "%"})


def _kod(secret: str) -> str:
    return pyotp.TOTP(secret).now()


def test_a2_sahip_2fa_kurulumu_ve_kapsam(hesaplar):
    from pvquant.services import platform_service as ps
    e1 = f"{hesaplar}-sahip1@example.invalid"
    p1 = "Gizli-Parola-123456"
    pid = ps.ilk_sahip_olustur(e1, p1)
    # 2FA yokken giriş: jeton var ama «iki_adim_kurulmali»; hassas işlem (yeniden doğrulama) parolayla bile GEÇMEZ (kapı kurulum uçlarına dar)
    g = ps.giris(e1, p1)
    assert g and g["iki_adim_kurulmali"] is True and g["rol"] == "sahip"
    assert ps.yeniden_dogrula(pid, p1, "000000") is False   # 2FA kurulu değilken ikinci sahip açılamaz (A1, A2'ye bağlı)
    # A2: kurulum → doğrula → aktif; aynı kod ikinci kez geçmez; giriş artık kod ister
    secret = ps.iki_adim_baslat(pid)["secret"]
    kod = _kod(secret)
    ps.iki_adim_dogrula(pid, kod)
    assert ps.oturum_durumu(pid)["totp_aktif"] is True
    assert ps.giris(e1, p1) == {"iki_adim_gerekli": True}
    with pytest.raises(ps.PlatformHata):
        ps.iki_adim_baslat(pid)   # açıkken yeniden kurulum yok (sıfırlama yalnız başka sahip)
    # tekrar koruması: kurulumda kullanılan kodla giriş reddedilir
    assert ps.giris(e1, p1, kod) is None
    # kilitlenme senaryosu: yanlış/eksik kod → giriş yok; platformda KURTARMA KODU yok (tablo yalnız müşteri users FK)
    assert ps.giris(e1, p1, "123456") is None
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        # O-1 kapısı (21.11): information_schema.constraint_column_usage yalnız tablo SAHİBİNE görünür (CI pvq_api rolünde boş) → pg_catalog
        fk = s.execute(text("SELECT confrelid::regclass::text FROM pg_constraint WHERE conrelid = 'kurtarma_kodlari'::regclass AND contype = 'f'")).scalars().all()
    assert fk == ["users"]


def test_a1_ikinci_sahip_ve_sifirlama_kurtarma_yolu(hesaplar, monkeypatch):
    from pvquant.services import platform_service as ps
    e1 = f"{hesaplar}-sahip1@example.invalid"
    p1 = "Gizli-Parola-123456"
    pid1 = ps.ilk_sahip_olustur(e1, p1)
    s1 = ps.iki_adim_baslat(pid1)["secret"]
    ps.iki_adim_dogrula(pid1, _kod(s1))
    # hassas işlem yeniden doğrulaması: yanlış kod False, doğru kod (yeni adım) True
    import time
    kod = _kod(s1)
    assert ps.yeniden_dogrula(pid1, "yanlis-parola-123", kod) is False
    # kurulumda kullanılan kodla aynı adımda yeniden doğrulama tekrar korumasına takılır → yeni adım bekle (test 30 s adım; sahte zaman yerine farklı pencere)
    import pyotp as _p
    ileri = _p.TOTP(s1).at(int(time.time()) + 30)
    assert ps.yeniden_dogrula(pid1, p1, ileri) is True   # valid_window=1 ile bir sonraki adım kabul
    # A1: ikinci sahip açılır (geçici parola yalnız yanıtta), ilk girişte parola değişimi + 2FA kurulumu gerekir
    y = ps.operator_ekle(f"{hesaplar}-sahip2@example.invalid", "sahip")
    pid2 = y["id"]
    assert y["rol"] == "sahip" and len(y["gecici_parola"]) >= 12
    g2 = ps.giris(y["email"], y["gecici_parola"])
    assert g2 and g2["iki_adim_kurulmali"] is True
    with pytest.raises(ps.PlatformHata, match="zaten kayıtlı"):
        ps.operator_ekle(y["email"], "sahip")
    # KURTARMA YOLU: sahip1 telefonunu kaybetti → sahip2 (2FA'sını kurduktan sonra) sahip1'in 2FA'sını sıfırlar; sahip1 parolayla girip yeniden kurar
    s2 = ps.iki_adim_baslat(pid2)["secret"]
    ps.iki_adim_dogrula(pid2, _kod(s2))
    assert ps.operator_guncelle(pid1, iki_adim_sifirla=True) is True
    assert ps.oturum_durumu(pid1)["totp_aktif"] is False and ps.giris(e1, p1)["iki_adim_kurulmali"] is True   # oturum sürümü arttı, yeniden kurulum
    # son etkin sahip korunur: sahip2 pasifleştirilemez/düşürülemez iken sahip1 de sahipse düşürülebilir; tek sahip kalınca hayır
    assert ps.operator_guncelle(pid1, aktif=False) is True          # iki sahip var → düşürülebilir
    # «son etkin sahip» bekçisi DB genelindeki etkin sahip sayısına bakar; test DB'de başka sahipler olabilir → yalıtmak için
    # onları geçici pasifleştir (bakım bağlamı, finally ile geri)
    from pvquant.db import bakim_baglami
    with bakim_baglami() as s:
        digerleri = [str(x) for x in s.execute(text("SELECT id FROM platform_kullanicilar WHERE rol='sahip' AND aktif AND id <> CAST(:p AS uuid)"), {"p": pid2}).scalars().all()]
        s.execute(text("UPDATE platform_kullanicilar SET aktif=false WHERE rol='sahip' AND aktif AND id <> CAST(:p AS uuid)"), {"p": pid2})
    try:
        with pytest.raises(ps.PlatformHata, match="son etkin sahip"):
            ps.operator_guncelle(pid2, aktif=False)                    # tek etkin sahip kaldı → korunur
        with pytest.raises(ps.PlatformHata, match="son etkin sahip"):
            ps.operator_guncelle(pid2, rol="operator")
    finally:
        with bakim_baglami() as s:
            for d in digerleri:
                s.execute(text("UPDATE platform_kullanicilar SET aktif=true WHERE id=CAST(:i AS uuid)"), {"i": d})
    # CLI kilitlenme çıkışı: parola yenileme yalnız ETKİN hesapta ve 2FA'yı KORUR (TOTP kaybında yetmez); pasif hesapta «etkin hesap bulunamadı»
    with pytest.raises(ps.PlatformHata, match="etkin hesap"):
        ps.parola_sifirla_cli(e1, "Yeni-Parola-123456")   # sahip1 pasifleştirilmişti
    ps.operator_guncelle(pid1, aktif=True)
    assert ps.parola_sifirla_cli(e1, "Yeni-Parola-123456") == pid1
    assert ps.giris(e1, "Yeni-Parola-123456")["iki_adim_kurulmali"] is True   # 2FA sıfırlanmıştı → kurulum ekranı; parola yenilendi
    # yeni sahip açma (ilk_sahip_olustur) mevcut sahip varken de çalışır (CLI acil çıkış) — 2FA'sız başlar
    assert ps.ilk_sahip_olustur(f"{hesaplar}-cli@example.invalid", "Acil-Parola-123456")
