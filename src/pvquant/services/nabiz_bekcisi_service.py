"""v2.670 adayı (28.11.2026) — NABIZ BEKÇİSİ: worker'dan BAĞIMSIZ (API süreci içinde) worker nabzını izler.
`hizmet_uyari` işi worker içinde koşar; worker tamamen durursa kendini bildiremez. Bu bekçi API'de arka plan iş parçacığı olarak
her ARALIK_DK dakikada `sistem_nabiz` (bilesen='worker') yaşını okur: > ESIK_DK → «worker sessiz» mektubu (tek; düzelene dek
tekrarlanmaz), düzelince tek «düzeldi». Kanal mevcut `posta_service` + `PVQ_ALARM_TO` (compose api environment'a eklendi).
Fail-safe: PVQ_ALARM_TO ya da SMTP yoksa başlamaz (log satırı); hiçbir istisna API'yi düşürmez; yalnız SELECT, yazma yok.
"""
from __future__ import annotations

import datetime as dt
import os
import threading
import time

from sqlalchemy import text

ARALIK_DK = 10
ESIK_DK = 30           # NABIZ_SESSIZ_DK (15) panel sinyalidir; e-posta için iki kat tolerans (yeniden başlatma/dağıtım penceresi)
KONU_ONEK = "[PVQuant uyarı]"


def durum(nabiz_zaman: dt.datetime | None, simdi: dt.datetime, esik_dk: int = ESIK_DK) -> tuple[str, int | None]:
    """SAF. ('yok'|'sessiz'|'calisiyor', yaş_dk)."""
    if nabiz_zaman is None:
        return "yok", None
    if nabiz_zaman.tzinfo is None:
        nabiz_zaman = nabiz_zaman.replace(tzinfo=dt.timezone.utc)
    yas = int((simdi - nabiz_zaman).total_seconds() // 60)
    return ("sessiz" if yas > esik_dk else "calisiyor"), yas


class Bekci:
    """Durum makinesi (bellek içi; API yeniden başlarsa sıfırlanır — sessizlik sürüyorsa bir kez daha bildirir, kabul edilir)."""

    def __init__(self, kime: str, gonder, esik_dk: int = ESIK_DK):
        self.kime, self.gonder, self.esik_dk = kime, gonder, esik_dk
        self.sessiz_bildirildi = False
        self.son: dict = {}

    def tur(self, nabiz_zaman: dt.datetime | None, simdi: dt.datetime) -> dict:
        d, yas = durum(nabiz_zaman, simdi, self.esik_dk)
        sonuc = {"durum": d, "yas_dk": yas, "gonderildi": None}
        if d in ("sessiz", "yok") and not self.sessiz_bildirildi:
            ok = self.gonder(self.kime, f"{KONU_ONEK} worker sessiz ({'nabız yok' if yas is None else f'{yas} dk'})",
                             f"PVQuant worker nabzı {simdi.strftime('%d.%m %H:%M')} UTC itibarıyla "
                             f"{'hiç yazılmamış' if yas is None else f'{yas} dakikadır yenilenmedi'} (eşik {self.esik_dk} dk). "
                             "Zamanlanmış tahmin/alarm işleri koşmuyor olabilir: `docker compose ps`, worker logu, sistem_nabiz. "
                             "Düzelince tek «düzeldi» mektubu gelir.")
            sonuc["gonderildi"] = "sessiz" if ok else "gonderilemedi"
            self.sessiz_bildirildi = bool(ok)
        elif d == "calisiyor" and self.sessiz_bildirildi:
            ok = self.gonder(self.kime, f"{KONU_ONEK} worker düzeldi", f"Worker nabzı yeniden geliyor (yaş {yas} dk).")
            sonuc["gonderildi"] = "duzeldi" if ok else "gonderilemedi"
            if ok:
                self.sessiz_bildirildi = False
        self.son = sonuc
        return sonuc


def nabiz_oku() -> dt.datetime | None:
    """Yalnız SELECT; sistem_nabiz küresel tablo (kiracısız)."""
    from pvquant.db import SessionLocal
    with SessionLocal() as s:
        return s.execute(text("SELECT zaman FROM sistem_nabiz WHERE bilesen = 'worker'")).scalar()


def baslat(aralik_dk: int = ARALIK_DK) -> threading.Thread | None:
    """API açılışında çağrılır. Kanal yoksa None (başlamaz). Daemon iş parçacığı; hata API'yi düşürmez."""
    from pvquant.services import posta_service
    kime = (os.environ.get("PVQ_ALARM_TO") or "").strip()
    if not kime or not posta_service.yapilandirildi():
        print("[nabiz-bekcisi] kapalı: PVQ_ALARM_TO ya da PVQ_SMTP_HOST tanımsız (worker kesintisi e-postayla bildirilmez)", flush=True)
        return None
    bekci = Bekci(kime, posta_service.gonder)

    def _dongu():
        while True:
            try:
                r = bekci.tur(nabiz_oku(), dt.datetime.now(dt.timezone.utc))
                if r.get("gonderildi"):
                    print(f"[nabiz-bekcisi] {r}", flush=True)
            except Exception as e:   # bekçi API'yi düşüremez
                print(f"[nabiz-bekcisi][hata] {type(e).__name__}: {e}", flush=True)
            time.sleep(aralik_dk * 60)

    t = threading.Thread(target=_dongu, name="nabiz-bekcisi", daemon=True)
    t.start()
    print(f"[nabiz-bekcisi] açık: her {aralik_dk} dk, eşik {ESIK_DK} dk, alıcı tanımlı", flush=True)
    return t
