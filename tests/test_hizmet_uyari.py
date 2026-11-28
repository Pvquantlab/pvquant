"""v2.670 adayı — servis hatası uyarısı: tespit, tekilleme, düzelme, hata görünürlüğü, sır süzgeci ve GERÇEK SMTP teslimi (yerel aiosmtpd alıcısı)."""
from __future__ import annotations

import datetime as dt
import threading
from contextlib import contextmanager

import pytest

from pvquant.services import hizmet_uyari_service as h

T0 = dt.datetime(2026, 11, 28, 9, 0, tzinfo=dt.timezone.utc)


class _Oturum:
    """Sahte DB: jobs_log error satırları + önceki hizmet_uyari sonucu."""
    def __init__(self, hatalar, onceki=None):
        self.hatalar, self.onceki = hatalar, onceki

    def execute(self, sql, params=None):
        o = self

        class R:
            def mappings(self):
                class M:
                    def all(self):
                        return o.hatalar
                return M()

            def scalar(self):
                return o.onceki
        return R()


def _baglam(hatalar, onceki=None):
    @contextmanager
    def b():
        yield _Oturum(hatalar, onceki)
    return b


def _hata(job="gece_meteo", plant="8d9acd11-aaaa", detail="OperationalError: connection to postgresql://u:gizli@db:5432 failed", dk=10):
    return {"job": job, "plant_id": plant, "started": T0 - dt.timedelta(minutes=dk), "detail": detail}


@pytest.fixture
def kanal(monkeypatch):
    monkeypatch.setenv("PVQ_SMTP_HOST", "smtp.ornek")
    monkeypatch.setenv("PVQ_ALARM_TO", "ops@ornek.test")
    kutu = []
    return kutu, (lambda kime, konu, govde, html=None: kutu.append((kime, konu, govde)) or True)


def test_hata_varsa_tek_mektup_sir_maskeli_musteri_verisi_yok(kanal):
    kutu, gonder = kanal
    r = h.calistir(T0, gonder=gonder, baglam=_baglam([_hata(), _hata(dk=50)]))
    assert r["durum"] == "uyari_gonderildi" and r["gonderilen"] == 1 and len(kutu) == 1    # aynı imza iki satır → tek imza
    kime, konu, govde = kutu[0]
    assert kime == "ops@ornek.test" and konu.startswith(h.KONU_ONEK) and "gece_meteo" in govde and "8d9acd11" in govde
    assert "gizli" not in govde and "://***@" in govde                                       # sır maskelendi
    assert r["gonderim"]["gece_meteo|8d9acd11|OperationalError"] == T0.isoformat()


def test_tekilleme_6_saat_sonra_tekrar(kanal):
    kutu, gonder = kanal
    onceki = {"aktif": ["gece_meteo|8d9acd11|OperationalError"], "gonderim": {"gece_meteo|8d9acd11|OperationalError": (T0 - dt.timedelta(hours=2)).isoformat()}}
    r = h.calistir(T0, gonder=gonder, baglam=_baglam([_hata()], onceki))
    assert r["durum"] == "ok" and kutu == []                                                # 2 sa önce bildirildi → sus
    onceki["gonderim"]["gece_meteo|8d9acd11|OperationalError"] = (T0 - dt.timedelta(hours=7)).isoformat()
    r2 = h.calistir(T0, gonder=gonder, baglam=_baglam([_hata()], onceki))
    assert r2["durum"] == "uyari_gonderildi" and len(kutu) == 1                             # 7 sa → tekrar


def test_duzelme_tek_mektup_sonra_sessiz(kanal):
    kutu, gonder = kanal
    onceki = {"aktif": ["gece_meteo|8d9acd11|OperationalError"], "gonderim": {"gece_meteo|8d9acd11|OperationalError": T0.isoformat()}}
    r = h.calistir(T0 + dt.timedelta(hours=1), gonder=gonder, baglam=_baglam([], onceki))
    assert r["durum"] == "duzeldi" and len(kutu) == 1 and "düzeldi" in kutu[0][1]
    r2 = h.calistir(T0 + dt.timedelta(hours=2), gonder=gonder, baglam=_baglam([], {"aktif": r["aktif"], "gonderim": r["gonderim"]}))
    assert r2["durum"] == "ok" and len(kutu) == 1                                            # ikinci düzelme mektubu yok


def test_gonderim_basarisiz_gorunur_hata(kanal):
    with pytest.raises(RuntimeError, match="gönderilemedi"):
        h.calistir(T0, gonder=lambda *a, **k: False, baglam=_baglam([_hata()]))


def test_kanal_yoksa_atlandi(monkeypatch):
    monkeypatch.delenv("PVQ_SMTP_HOST", raising=False)
    monkeypatch.setenv("PVQ_ALARM_TO", "ops@ornek.test")
    r = h.calistir(T0, baglam=_baglam([_hata()]))
    assert r["durum"] == "atlandi" and "kanalı yok" in r["neden"]
    monkeypatch.setenv("PVQ_SMTP_HOST", "smtp.ornek")
    monkeypatch.setenv("PVQ_ALARM_TO", "")
    assert h.calistir(T0, baglam=_baglam([_hata()]))["durum"] == "atlandi"


def test_uctan_uca_gercek_smtp_teslimi_yerel_alici(monkeypatch):
    """Gerçek smtplib yolu: yerel aiosmtpd alıcısı (TLS/login yok) → mektup alıcıya ulaşır; müşteri verisi/sır yok."""
    aiosmtpd = pytest.importorskip("aiosmtpd.controller")
    gelen = []

    class Alici:
        async def handle_DATA(self, server, session, envelope):  # noqa: N802 — aiosmtpd kancası
            gelen.append((envelope.rcpt_tos, envelope.content.decode("utf-8", "replace")))
            return "250 OK"
    import socket
    with socket.socket() as sk:                      # boş yerel port (Controller port=0'ı çözmez)
        sk.bind(("127.0.0.1", 0))
        port = sk.getsockname()[1]
    ctrl = aiosmtpd.Controller(Alici(), hostname="127.0.0.1", port=port)
    ctrl.start()
    try:
        monkeypatch.setenv("PVQ_SMTP_HOST", "127.0.0.1")
        monkeypatch.setenv("PVQ_SMTP_PORT", str(ctrl.port))
        monkeypatch.setenv("PVQ_SMTP_TLS", "0")
        monkeypatch.delenv("PVQ_SMTP_USER", raising=False)
        monkeypatch.setenv("PVQ_SMTP_FROM", "pvquant@ornek.test")
        monkeypatch.setenv("PVQ_ALARM_TO", "ops@ornek.test")
        r = h.calistir(T0, baglam=_baglam([_hata(job="sabah_tahmin", detail="RuntimeError: sentetik test hatası (müşteri verisi yok)")]))
    finally:
        ctrl.stop()
    assert r["durum"] == "uyari_gonderildi" and len(gelen) == 1
    import email
    alicilar, ham = gelen[0]
    msg = email.message_from_string(ham)
    govde = msg.get_payload(decode=True).decode("utf-8")
    assert alicilar == ["ops@ornek.test"] and "sabah_tahmin" in govde and "sentetik" in govde and "gizli" not in govde
    assert str(email.header.make_header(email.header.decode_header(msg["Subject"]))).startswith(h.KONU_ONEK)
    assert threading.active_count() >= 1
