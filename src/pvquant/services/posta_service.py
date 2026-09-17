"""v2.334 — ortak e-posta katmanı (dışa mektup atan TEK kapı).

Bugüne dek sistemden dışarı e-posta yalnız alarm servisinin kendi SMTP
bloğundan çıkabiliyordu ve PVQ_SMTP_HOST tanımsızsa o da atlanıyordu.
Başvuru teyidi (v2.334) ve parola sıfırlama (sıradaki dalga) aynı kapıyı
kullanacağından blok buraya taşındı; alarm_service artık buradan geçer.

Sözleşme:
- PVQ_SMTP_HOST tanımsızsa posta YAPILANDIRILMAMIŞTIR: gonder() False döner,
  hiçbir akış bu yüzden PATLAMAZ (başvuru yine tabloya düşer, alarm yine
  alerts satırı yazar). Sessiz başarı yanılsaması da yaratılmaz — çağıran,
  dönüş değerinden gönderilip gönderilmediğini bilir.
- PVQ_SMTP_TLS=0 STARTTLS'i kapatır (yalnız yerel sınama sunucusu için);
  PVQ_SMTP_USER boşsa login atlanır. Gönderim hatası yutulur ve False döner:
  posta, ana işin (kayıt) yan ürünüdür, ana işi düşüremez.
"""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText


def yapilandirildi() -> bool:
    return bool(os.environ.get("PVQ_SMTP_HOST"))


def gonder(kime: str, konu: str, govde: str) -> bool:
    """True = SMTP sunucusu mektubu kabul etti; False = yapılandırma yok ya da
    gönderim hatası (ayrıntı log'da, çağırana sızdırılmaz)."""
    host = os.environ.get("PVQ_SMTP_HOST")
    if not host or not kime:
        return False
    try:
        m = MIMEText(govde, "plain", "utf-8")
        m["Subject"] = konu
        m["From"] = os.environ.get("PVQ_SMTP_FROM") or os.environ.get("PVQ_SMTP_USER", "")
        m["To"] = kime
        with smtplib.SMTP(host, int(os.environ.get("PVQ_SMTP_PORT") or 587),
                          timeout=15) as srv:
            if os.environ.get("PVQ_SMTP_TLS", "1") != "0":
                srv.starttls()
            kullanici = os.environ.get("PVQ_SMTP_USER")
            if kullanici:
                srv.login(kullanici, os.environ.get("PVQ_SMTP_PASS", ""))
            srv.send_message(m)
        return True
    except Exception as e:   # noqa: BLE001 — posta ana işi düşüremez
        print("[posta][hata]", konu, "->", type(e).__name__, e)
        return False
