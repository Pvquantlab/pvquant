"""Yanıt önbelleği — ağır GET uçları için damga anahtarlı, süreç içi, kiracı + santral yalıtımlı (16.11.2026 gezinme hızı partisi).

Neden: Santralim/Doğruluk/Kalibrasyon açılışında aynı santral için her gezinmede 0,3–1,5 s süren pandas hesapları
(özet, sağlık, dengesizlik, geri test, hata dağılımı…) yeniden koşuyordu; veri ise yalnız gece işleri, SCADA yüklemesi
ya da ayar değişince değişir. Anahtarın bir parçası santralın DEĞİŞİM DAMGASI (damga_service: son SCADA/koşu/alarm/skill/
kalibrasyon/piyasa/iş/meteo + santral satırı özü) olduğundan veri değişir değişmez eski kayıt kendiliğinden geçersizleşir;
TTL yalnız emniyettir. Kiracı ve santral kimliği anahtardadır: başka kiracı aynı santral kimliğiyle gelse de kayıt
paylaşılmaz (ayrıca yetki/404 denetimi üretici içinde yine koşar — önbellek yalnız YETKİLİ ve BAŞARILI yanıtı saklar).

Açma: PVQ_YANIT_ONBELLEK=1 (docker-compose api). Kapalıyken `getir` üreticiyi doğrudan çağırır (testler, yerel geliştirme).
Damga okunamazsa (DB yok) yine önbelleksiz üretilir — doğruluk hızdan önce gelir. Her uvicorn işçisinin kendi belleği vardır.
"""
from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from typing import Any, Callable

_KILIT = threading.Lock()
_KAYIT: "OrderedDict[tuple[str, str, str, str], tuple[float, Any]]" = OrderedDict()
_DAMGA: dict[tuple[str, str], tuple[float, str]] = {}
EN_COK = 512            # işçi başına kayıt tavanı (LRU)
DAMGA_SN = 5.0          # damga etag'i bu kadar süre yeniden hesaplanmaz (bir sayfanın ~20 isteği tek damga sorgusu paylaşır)
VARSAYILAN_TTL_SN = 900
SAYAC = {"isabet": 0, "iska": 0, "atlandi": 0}


def etkin() -> bool:
    return os.environ.get("PVQ_YANIT_ONBELLEK", "0") == "1"


def _damga_etag(tenant_id, plant_id) -> str:
    k = (str(tenant_id), str(plant_id)); simdi = time.monotonic()
    with _KILIT:
        v = _DAMGA.get(k)
        if v and simdi - v[0] < DAMGA_SN:
            return v[1]
    from pvquant.services import damga_service
    et = damga_service.etag_uret(damga_service.hesapla(tenant_id, plant_id))
    with _KILIT:
        _DAMGA[k] = (simdi, et)
    return et


def getir(tenant_id, plant_id, anahtar: str, uret: Callable[[], Any], ttl_sn: int = VARSAYILAN_TTL_SN) -> Any:
    """Anahtar = (kiracı, santral, uç+parametre, damga etag). İsabet → saklanan yanıt; ıska → `uret()` koşar ve saklanır.
    Üretici istisna atarsa hiçbir şey saklanmaz (404/422 önbelleğe girmez)."""
    if not etkin():
        SAYAC["atlandi"] += 1
        return uret()
    try:
        et = _damga_etag(tenant_id, plant_id)
    except Exception:
        SAYAC["atlandi"] += 1
        return uret()
    k = (str(tenant_id), str(plant_id), anahtar, et); simdi = time.monotonic()
    with _KILIT:
        v = _KAYIT.get(k)
        if v and simdi - v[0] < ttl_sn:
            _KAYIT.move_to_end(k); SAYAC["isabet"] += 1
            return v[1]
    deger = uret()
    with _KILIT:
        _KAYIT[k] = (simdi, deger); _KAYIT.move_to_end(k); SAYAC["iska"] += 1
        while len(_KAYIT) > EN_COK:
            _KAYIT.popitem(last=False)
    return deger


def temizle() -> None:
    with _KILIT:
        _KAYIT.clear(); _DAMGA.clear()
    for k in SAYAC:
        SAYAC[k] = 0
