"""24.10 Faz 1 — platform kimliği ve kiracı yönetimi UÇTAN UCA (DB'li; CI'da ve yerel timescale ile koşar).
İlk sahip → giriş → jeton kapsamı → 2FA kurulumu → kiracı oluşturma (posta kapalı: davet bağlantısı döner) → davetle parola
belirleme → müşteri girişi → askıya alma → müşteri girişi 403 (KiraciAskida) ve açık jetonların düşmesi → denetim izi."""
import os
import uuid
import jwt as _jwt
import pyotp
import pytest
from sqlalchemy import text

from pvquant.db import sistem_baglami
from pvquant.services import platform_service as ps, auth_service as au, denetim_service as dz


@pytest.fixture
def temiz(monkeypatch):
    monkeypatch.delenv("PVQ_SMTP_HOST", raising=False)       # posta kapalı → bağlantı yanıtta
    monkeypatch.setenv("PVQ_JWT_SECRET", "test-sirri-0123456789abcdef-uzun")
    etiket = uuid.uuid4().hex[:8]
    yield etiket
    ps.oturum_onbellegi_dusur(); au.oturum_onbellegi_dusur()
    with sistem_baglami() as s:
        s.execute(text("DELETE FROM denetim_izi WHERE aktor_eposta LIKE :e OR ayrinti::text LIKE :e"), {"e": f"%{etiket}%"})
        s.execute(text("DELETE FROM parola_sifirlama WHERE user_id IN (SELECT id FROM users WHERE email LIKE :e)"), {"e": f"%{etiket}%"})
        s.execute(text("DELETE FROM users WHERE email LIKE :e"), {"e": f"%{etiket}%"})
        s.execute(text("DELETE FROM tenants WHERE name LIKE :e"), {"e": f"%{etiket}%"})
        s.execute(text("DELETE FROM platform_kullanicilar WHERE email LIKE :e"), {"e": f"%{etiket}%"})


def test_uctan_uca(temiz):
    e = temiz
    sahip_eposta = f"sahip-{e}@pvq.test"
    pid = ps.ilk_sahip_olustur(sahip_eposta, "cok-gizli-parola-123")
    # giriş + jeton kapsamı
    assert ps.giris(sahip_eposta, "yanlis") is None
    g = ps.giris(sahip_eposta, "cok-gizli-parola-123")
    assert g["iki_adim_kurulmali"] is True and g["rol"] == "sahip"
    c = _jwt.decode(g["token"], au._sir(), algorithms=["HS256"])
    assert c["kapsam"] == "platform" and c["sub"] == pid and c["sv"] == 0
    # 2FA kur → artık kodsuz giriş olmaz
    k = ps.iki_adim_baslat(pid)
    ps.iki_adim_dogrula(pid, pyotp.TOTP(k["secret"]).now())
    assert ps.giris(sahip_eposta, "cok-gizli-parola-123") == {"iki_adim_gerekli": True}
    assert ps.giris(sahip_eposta, "cok-gizli-parola-123", pyotp.TOTP(k["secret"]).now())["iki_adim_kurulmali"] is False
    # kiracı oluştur (posta kapalı → bağlantı döner), listede görünür
    firma = f"Firma {e}"; admin_eposta = f"admin-{e}@musteri.test"
    y = ps.kiraci_olustur(pid, firma, admin_eposta)
    assert y["davet_gonderildi"] is False and "davet_baglantisi" in y
    assert any(x["id"] == y["tenant_id"] and x["kullanici"] == 1 for x in ps.kiraci_listesi(pid))
    d = ps.kiraci_detay(pid, y["tenant_id"])
    assert d["kullanicilar"][0]["email"] == admin_eposta and d["kullanicilar"][0]["rol"] == "admin"
    with pytest.raises(ValueError):
        ps.kiraci_olustur(pid, firma, f"baska-{e}@musteri.test")     # aynı ad
    # davet bağlantısıyla parola belirle → müşteri girişi çalışır
    jeton = y["davet_baglantisi"].split("jeton=")[1]
    au.parola_sifirla(jeton, "musteri-parola-123")
    mg = au.giris(admin_eposta, "musteri-parola-123")
    assert mg and mg["role"] == "admin" and mg["tenant_id"] == y["tenant_id"]
    sv0 = _jwt.decode(mg["token"], au._sir(), algorithms=["HS256"])["sv"]
    # askıya al → müşteri girişi 403 mantığı (KiraciAskida), açık jetonlar düşer (sv arttı), gecerli_kullanici 403
    ps.kiraci_guncelle(pid, y["tenant_id"], status="suspended", notlar="ödeme bekleniyor")
    with pytest.raises(au.KiraciAskida):
        au.giris(admin_eposta, "musteri-parola-123")
    durum = au.oturum_durumu(y["user_id"])
    assert durum["kiraci_durum"] == "suspended" and durum["sv"] == sv0 + 1
    # yeniden aç → giriş çalışır
    ps.kiraci_guncelle(pid, y["tenant_id"], status="active")
    assert au.giris(admin_eposta, "musteri-parola-123")["role"] == "admin"
    # kullanıcı arama + destek bağlantısı
    assert any(u["email"] == admin_eposta for u in ps.kullanici_ara(pid, e))
    dv = ps.davet_gonder(pid, y["user_id"], saat=24)
    assert dv["gonderildi"] is False and "baglanti" in dv
    # denetim izi: yaz/oku, kiracıya göre süz
    assert dz.kaydet("platform", "kiraci_guncelle", aktor_id=pid, aktor_eposta=sahip_eposta, tenant_id=y["tenant_id"],
                     nesne_tur="tenant", nesne_id=y["tenant_id"], ayrinti={"etiket": e})
    kayitlar = dz.listele(tenant_id=y["tenant_id"])
    assert kayitlar and kayitlar[0]["eylem"] == "kiraci_guncelle" and kayitlar[0]["ayrinti"]["etiket"] == e
    # operatör yönetimi: son sahip düşürülemez
    op = ps.operator_ekle(f"op-{e}@pvq.test", "operator")
    assert ps.operator_guncelle(op["id"], aktif=False)
    sahipler = [o for o in ps.operator_listesi() if o["rol"] == "sahip" and o["aktif"]]
    if len(sahipler) == 1:
        with pytest.raises(ValueError):
            ps.operator_guncelle(pid, aktif=False)
