"""v2.334 — ortak posta katmanı: yapılandırma yokken sessiz False, varken
SMTP akışının doğru kurulması (TLS/login koşulları), hatada False.
Gerçek ağ yok: smtplib.SMTP sahteyle değiştirilir."""
import smtplib

from pvquant.services import basvuru_service, posta_service


class _SahteSMTP:
    """send_message çağrılarını sınıf düzeyinde biriktirir."""
    kutu: list = []          # (kime, konu) kayıtları
    tls_cagrildi = False
    login_cagrildi = False

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        _SahteSMTP.tls_cagrildi = True

    def login(self, u, p):
        _SahteSMTP.login_cagrildi = True

    def send_message(self, m):
        _SahteSMTP.kutu.append((m["To"], m["Subject"]))


def _sifirla(monkeypatch, **env):
    _SahteSMTP.kutu = []
    _SahteSMTP.tls_cagrildi = False
    _SahteSMTP.login_cagrildi = False
    for k in ["PVQ_SMTP_HOST", "PVQ_SMTP_PORT", "PVQ_SMTP_USER", "PVQ_SMTP_PASS",
              "PVQ_SMTP_FROM", "PVQ_SMTP_TLS", "PVQ_BILDIRIM_EPOSTA"]:
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(smtplib, "SMTP", _SahteSMTP)


def test_yapilandirma_yoksa_false(monkeypatch):
    _sifirla(monkeypatch)
    assert posta_service.yapilandirildi() is False
    assert posta_service.gonder("a@b.co", "konu", "gövde") is False
    assert _SahteSMTP.kutu == []


def test_gonderim_tls_ve_login(monkeypatch):
    _sifirla(monkeypatch, PVQ_SMTP_HOST="smtp.ornek", PVQ_SMTP_USER="u",
             PVQ_SMTP_PASS="p", PVQ_SMTP_FROM="no-reply@pvq")
    assert posta_service.gonder("a@b.co", "konu", "gövde") is True
    assert _SahteSMTP.kutu == [("a@b.co", "konu")]
    assert _SahteSMTP.tls_cagrildi and _SahteSMTP.login_cagrildi


def test_tls_kapali_ve_loginsiz(monkeypatch):
    # yerel sınama sunucusu kipi: TLS=0 ve kullanıcı yok — ikisi de atlanır
    _sifirla(monkeypatch, PVQ_SMTP_HOST="localhost", PVQ_SMTP_TLS="0")
    assert posta_service.gonder("a@b.co", "konu", "gövde") is True
    assert not _SahteSMTP.tls_cagrildi and not _SahteSMTP.login_cagrildi


def test_hata_yutulur_false(monkeypatch):
    _sifirla(monkeypatch, PVQ_SMTP_HOST="smtp.ornek")

    def patla(m):
        raise smtplib.SMTPException("ret")
    monkeypatch.setattr(_SahteSMTP, "send_message", lambda self, m: patla(m))
    assert posta_service.gonder("a@b.co", "konu", "gövde") is False


def test_basvuru_teyit_ve_bildirim(monkeypatch):
    """başvuru kaydı: başvurana teyit + PVQ_BILDIRIM_EPOSTA'ya bildirim;
    SMTP yokken teyit False ama kayıt yine tamam."""
    class _S:
        def execute(self, *a, **k):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(basvuru_service, "sistem_baglami", lambda: _S())

    _sifirla(monkeypatch, PVQ_SMTP_HOST="smtp.ornek",
             PVQ_BILDIRIM_EPOSTA="sahip@pvq")
    r = basvuru_service.kaydet("musteri@ges.com", "Deneme GES", 1000.0)
    assert r == {"tamam": True, "teyit": True}
    assert ("musteri@ges.com", "PVQuant — başvurunuz alındı") in _SahteSMTP.kutu
    assert ("sahip@pvq", "[PVQuant] Yeni vitrin başvurusu") in _SahteSMTP.kutu

    _sifirla(monkeypatch)   # SMTP yok
    r = basvuru_service.kaydet("musteri@ges.com", None, None)
    assert r == {"tamam": True, "teyit": False}
    assert _SahteSMTP.kutu == []
