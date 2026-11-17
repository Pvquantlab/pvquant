"""Yanıt önbelleği ısıtıcısı — sunucu içi, damga tetiklemeli (17.11.2026 Genel bakış hız turu).

Neden: yanıt önbelleği (yanit_onbellegi) yalnız BİR ziyaretçi bedelini ödedikten sonra ısınır. Gece işleri (koşu, meteo, piyasa)
damgayı değiştirince her santralın ilk ziyaretçisi soğuk hesapları bekliyordu — ÖLÇÜLDÜ (canlı konteyner, Format Lab, 17.11):
genel-bakis soğuk 573 ms / ılık 4 ms, summary 184 / 5, forecast 294 / 23. Kuyrukta (4 işçi, eşzamanlı) bu soğuk maliyetler
1,1–1,5 s'ye uzuyordu.

Ne yapar: tek bir işçi (dosya kilidiyle seçilir; uvicorn 4 süreç) her ARALIK_SN'de bütün etkin santralların damga etag'ini okur;
etag değişmişse (ya da ilk turda) kayıtlı üreticileri `yanit_onbellegi.getir` ile koşturur. Anahtar ve TTL uç sarmalıyla
BİREBİR aynı olduğundan (örn. "genel-bakis", "forecast?hours=384") gerçek istek doğrudan isabet eder; dosya katmanı sayesinde
diğer işçiler de yararlanır. Hesap yazmaz, yetki gerektirmez (kiracı kimliği damgada ve anahtarda; üretici RLS içinde koşar).

Açma: PVQ_YANIT_ISITICI=1 (docker-compose api) ve PVQ_YANIT_ONBELLEK=1. Kapalıyken `baslat` hiçbir şey yapmaz (testler, yerel).
Üretici istisnası (ör. koşusu olmayan santralda forecast 404) sayılır ve geçilir; ısıtıcı asla uygulamayı düşürmez.
17.11 KGUP hiz turu: anahtarlar {bugun}/{yarin} yer tutucusu tasiyabilir (gunler/anahtar_coz; "kgup?gun={yarin}&kantil=p50&fmt=json",
"kgup/revizyon-girdi?gun={bugun}"); etag anisina gun eklenir; uretici 4xx'i (409 kosu yok) «bos» sayilir, etag anisini engellemez.
"""
from __future__ import annotations

import contextlib
import os
import threading
import time
from collections.abc import Callable
from typing import Any

from pvquant.services import yanit_onbellegi

ARALIK_SN = 60.0        # damga yoklama aralığı (istemcinin görünür yoklamasıyla aynı)
ILK_GECIKME_SN = 15.0   # açılışta servis ön yüklemesi bitsin, DB ayağa kalksın
SAYAC = {"tur": 0, "isitilan": 0, "atlanan": 0, "bos": 0, "hata": 0}   # bos: uretici 4xx (kosusu olmayan santral) — kalici durum, hata degil
_SON_ETAG: dict[str, str] = {}
_KILIT_DOSYASI: Any = None

Uretici = Callable[[str, str], Any]            # (tenant_id, plant_id) -> yanıt
Kayit = dict[str, tuple[Uretici, int]]         # anahtar -> (üretici, ttl_sn)


def etkin() -> bool:
    return os.environ.get("PVQ_YANIT_ISITICI", "0") == "1" and yanit_onbellegi.etkin()


def gunler() -> dict[str, str]:
    """17.11 KGUP hiz turu — {bugun}/{yarin}: piyasa gunu (Istanbul). Anahtarlardaki yer tutucular her turda bununla cozulur ve
    etag anisina gun eklenir: damga degismese de gun donunce KGUP (yarin) ve revizyon girdisi (bugun) yeniden isitilir."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    from pvquant.zaman import PIYASA_TZ
    b = datetime.now(ZoneInfo(PIYASA_TZ)).date()
    return {"bugun": b.isoformat(), "yarin": (b + timedelta(days=1)).isoformat()}


def anahtar_coz(anahtar: str, g: dict[str, str] | None = None) -> str:
    g = g or gunler()
    return anahtar.replace("{bugun}", g["bugun"]).replace("{yarin}", g["yarin"])


def santraller() -> list[tuple[str, str]]:
    """(tenant_id, plant_id) — etkin kiracıların arşivlenmemiş santralları, sistem bağlamından (RLS dışı; kiracı kimliği anahtara girer)."""
    from sqlalchemy import text

    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        return [(str(r[0]), str(r[1])) for r in s.execute(text(
            "SELECT p.tenant_id, p.id FROM plants p JOIN tenants t ON t.id = p.tenant_id"
            " WHERE NOT p.archived AND t.status = 'active' ORDER BY p.tenant_id, p.name")).all()]   # 17.11 inceleme: askıdaki kiracı ısıtılmaz


def tur(kayit: Kayit, liste: list[tuple[str, str]] | None = None, zorla: bool = False) -> dict:
    """Bir yoklama turu: damga etag'i değişen santrallar için kayıtlı üreticileri ısıtır. Dönüş: bu turun sayaçları."""
    sonuc = {"isitilan": 0, "atlanan": 0, "bos": 0, "hata": 0}
    g = gunler()
    for tenant_id, plant_id in (liste if liste is not None else santraller()):
        try:
            et = yanit_onbellegi._damga_etag(tenant_id, plant_id) + "|" + g["bugun"]   # gun donunce de yeniden (KGUP yarin / revizyon bugun)
        except Exception:
            sonuc["hata"] += 1
            continue
        if not zorla and _SON_ETAG.get(plant_id) == et:
            sonuc["atlanan"] += 1
            continue
        hata = 0
        for anahtar, (uret, ttl_sn) in kayit.items():
            try:
                yanit_onbellegi.getir(tenant_id, plant_id, anahtar_coz(anahtar, g), lambda u=uret, t=tenant_id, p=plant_id: u(t, p), ttl_sn=ttl_sn)
                sonuc["isitilan"] += 1
            except Exception as e:
                kod = getattr(e, "status_code", None)
                if isinstance(kod, int) and 400 <= kod < 500:
                    sonuc["bos"] += 1    # 404/409 (kosu yok, program yok): kalici durum; onbellege girmez, etag anisini engellemez (her dakika yeniden denenmez)
                else:
                    hata += 1    # gecici (DB) hata: sayilir, gecilir; bir sonraki turda yeniden denenir
        sonuc["hata"] += hata
        if hata == 0:
            _SON_ETAG[plant_id] = et    # 17.11 inceleme: hata varsa (geçici DB sorunu) bir sonraki turda yeniden denenir
    SAYAC["tur"] += 1
    for k in ("isitilan", "atlanan", "bos", "hata"):
        SAYAC[k] += sonuc[k]
    return sonuc


def _kilit_al() -> bool:
    """Çok işçili uvicorn'da tek ısıtıcı: paylaşılan önbellek dizininde dosya kilidi (fcntl, engelsiz). Dizin yoksa ısıtıcı koşmaz."""
    global _KILIT_DOSYASI
    if _KILIT_DOSYASI is not None:
        return True
    d = yanit_onbellegi._dizin()
    if d is None:
        return False    # 17.11 inceleme: paylaşılan dizin yoksa dosya katmanı da yok; 4 işçi aynı işi boşa yapmasın
    try:
        import fcntl
        fh = open(os.path.join(d, "isitici.lock"), "w")   # noqa: SIM115 — kilit süreç ömrünce açık kalır
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _KILIT_DOSYASI = fh
        return True
    except OSError:
        with contextlib.suppress(Exception):
            fh.close()
        return False


def _dongu(kayit: Kayit) -> None:
    time.sleep(ILK_GECIKME_SN)
    while True:
        try:
            if _kilit_al():
                tur(kayit)
        except Exception:
            SAYAC["hata"] += 1
        time.sleep(ARALIK_SN)


def baslat(kayit: Kayit) -> threading.Thread | None:
    """Uygulama açılışında çağrılır; etkin değilse None döner. Arka plan iş parçacığı daemon'dur (kapanışı bekletmez)."""
    if not etkin() or not kayit:
        return None
    t = threading.Thread(target=_dongu, args=(kayit,), name="yanit-isitici", daemon=True)
    t.start()
    return t
