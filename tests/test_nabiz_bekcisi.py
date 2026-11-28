"""v2.670 adayı — API nabız bekçisi: durum eşiği, tek bildirim/düzelme, gönderim hatası, kanal yoksa başlamaz."""
from __future__ import annotations

import datetime as dt

from pvquant.services import nabiz_bekcisi_service as nb

T0 = dt.datetime(2026, 11, 28, 10, 0, tzinfo=dt.timezone.utc)


def test_durum_esigi():
    assert nb.durum(None, T0) == ("yok", None)
    assert nb.durum(T0 - dt.timedelta(minutes=29), T0) == ("calisiyor", 29)
    assert nb.durum(T0 - dt.timedelta(minutes=31), T0) == ("sessiz", 31)
    assert nb.durum((T0 - dt.timedelta(minutes=40)).replace(tzinfo=None), T0)[0] == "sessiz"   # tz'siz damga UTC sayılır


def test_sessiz_tek_bildirim_sonra_duzelme_tek_mektup():
    kutu = []
    b = nb.Bekci("ops@ornek.test", lambda kime, konu, govde, html=None: kutu.append((kime, konu)) or True)
    assert b.tur(T0 - dt.timedelta(minutes=5), T0)["gonderildi"] is None                 # sağlıklı: sessiz
    assert b.tur(T0 - dt.timedelta(minutes=45), T0)["gonderildi"] == "sessiz"            # eşik aşıldı → mektup
    assert b.tur(T0 - dt.timedelta(minutes=55), T0 + dt.timedelta(minutes=10))["gonderildi"] is None   # sürüyor → tekrar yok
    assert b.tur(T0 + dt.timedelta(minutes=19), T0 + dt.timedelta(minutes=20))["gonderildi"] == "duzeldi"
    assert b.tur(T0 + dt.timedelta(minutes=29), T0 + dt.timedelta(minutes=30))["gonderildi"] is None
    assert [k for _, k in kutu] == [f"{nb.KONU_ONEK} worker sessiz (45 dk)", f"{nb.KONU_ONEK} worker düzeldi"]
    assert all(k == "ops@ornek.test" for k, _ in kutu)


def test_nabiz_hic_yoksa_bildirir_ve_gonderim_hatasi_tekrar_dener():
    kutu = []
    b = nb.Bekci("ops@ornek.test", lambda *a, **k: kutu.append(1) and False)
    assert b.tur(None, T0)["gonderildi"] == "gonderilemedi" and not b.sessiz_bildirildi
    assert b.tur(None, T0 + dt.timedelta(minutes=10))["gonderildi"] == "gonderilemedi"   # bildirilemedi → bir sonraki turda yeniden dener
    assert len(kutu) == 2


def test_kanal_yoksa_baslamaz(monkeypatch):
    monkeypatch.delenv("PVQ_ALARM_TO", raising=False)
    monkeypatch.setenv("PVQ_SMTP_HOST", "smtp.ornek")
    assert nb.baslat() is None
    monkeypatch.setenv("PVQ_ALARM_TO", "ops@ornek.test")
    monkeypatch.delenv("PVQ_SMTP_HOST", raising=False)
    assert nb.baslat() is None


def test_kanal_varsa_daemon_is_parcacigi(monkeypatch):
    monkeypatch.setenv("PVQ_ALARM_TO", "ops@ornek.test")
    monkeypatch.setenv("PVQ_SMTP_HOST", "smtp.ornek")
    monkeypatch.setattr(nb, "nabiz_oku", lambda: dt.datetime.now(dt.timezone.utc))   # DB yok
    t = nb.baslat(aralik_dk=60)
    assert t is not None and t.daemon and t.is_alive() and t.name == "nabiz-bekcisi"
