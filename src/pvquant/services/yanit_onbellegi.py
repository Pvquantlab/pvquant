"""Yanıt önbelleği — ağır GET uçları için damga anahtarlı, süreç içi, kiracı + santral yalıtımlı (16.11.2026 gezinme hızı partisi).

Neden: Santralim/Doğruluk/Kalibrasyon açılışında aynı santral için her gezinmede 0,3–1,5 s süren pandas hesapları
(özet, sağlık, dengesizlik, geri test, hata dağılımı…) yeniden koşuyordu; veri ise yalnız gece işleri, SCADA yüklemesi
ya da ayar değişince değişir. Anahtarın bir parçası santralın DEĞİŞİM DAMGASI (damga_service: son SCADA/koşu/alarm/skill/
kalibrasyon/piyasa/iş/meteo + santral satırı özü) olduğundan veri değişir değişmez eski kayıt kendiliğinden geçersizleşir;
TTL yalnız emniyettir. Kiracı ve santral kimliği anahtardadır: başka kiracı aynı santral kimliğiyle gelse de kayıt
paylaşılmaz (ayrıca yetki/404 denetimi üretici içinde yine koşar — önbellek yalnız YETKİLİ ve BAŞARILI yanıtı saklar).

Açma: PVQ_YANIT_ONBELLEK=1 (docker-compose api). Kapalıyken `getir` üreticiyi doğrudan çağırır (testler, yerel geliştirme).
Damga okunamazsa (DB yok) yine önbelleksiz üretilir — doğruluk hızdan önce gelir.

İki katman (16.11 canlı ölçüm dersi): uvicorn 4 işçi = 4 süreç; yalnız süreç içi bellekle ikinci ziyaret başka işçiye düşüp ıska
veriyordu (günlükte her ağır uç tam iki kez «YAVAS»). Bu yüzden ikinci katman konteynerin tmp dizininde PAYLAŞILAN dosya
önbelleğidir (`PVQ_YANIT_ONBELLEK_DIZIN`, varsayılan /tmp/pvq-yanit): anahtarın sha256'sı dosya adı, içerik FastAPI'nin
`jsonable_encoder` çıktısı (HTTP yanıtıyla birebir aynı JSON), yazma geçici dosya + atomik yeniden adlandırma, TTL dosya
mtime'ından. Yeni bağımlılık ve şema yok; dizin yazılamazsa yalnız süreç içi katman çalışır.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

_KILIT = threading.Lock()
_KAYIT: OrderedDict[tuple[str, str, str, str], tuple[float, Any]] = OrderedDict()
_DAMGA: dict[tuple[str, str], tuple[float, str]] = {}
EN_COK = 512            # işçi başına kayıt tavanı (LRU)
DAMGA_SN = 5.0          # damga etag'i bu kadar süre yeniden hesaplanmaz (bir sayfanın ~20 isteği tek damga sorgusu paylaşır)
VARSAYILAN_TTL_SN = 900
DOSYA_EN_COK = 4000       # paylaşılan dizindeki dosya tavanı; aşınca en eskiler silinir (her 50 yazmada bir bakılır)
SAYAC = {"isabet": 0, "dosya_isabet": 0, "iska": 0, "atlandi": 0}
_YAZMA_SAYACI = [0]


def _dizin() -> str | None:
    d = os.environ.get("PVQ_YANIT_ONBELLEK_DIZIN", "/tmp/pvq-yanit")
    try:
        os.makedirs(d, exist_ok=True)
        return d if os.access(d, os.W_OK) else None
    except OSError:
        return None


def _dosya_yolu(d: str, k: tuple[str, str, str, str]) -> str:
    return os.path.join(d, hashlib.sha256("\x1f".join(k).encode()).hexdigest() + ".json")


def _dosyadan(k, ttl_sn: int):
    d = _dizin()
    if d is None:
        return None
    y = _dosya_yolu(d, k)
    try:
        if time.time() - os.stat(y).st_mtime >= ttl_sn:
            return None
        with open(y, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _dosyaya(k, deger) -> None:
    d = _dizin()
    if d is None:
        return
    try:
        fd, gecici = tempfile.mkstemp(dir=d, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(deger, f, ensure_ascii=False)
        os.replace(gecici, _dosya_yolu(d, k))
        _YAZMA_SAYACI[0] += 1
        if _YAZMA_SAYACI[0] % 50 == 0:
            _budama(d)
    except (OSError, TypeError, ValueError):
        return


def _budama(d: str) -> None:
    try:
        dosyalar = [(os.stat(os.path.join(d, a)).st_mtime, a) for a in os.listdir(d) if a.endswith(".json")]
    except OSError:
        return
    if len(dosyalar) <= DOSYA_EN_COK:
        return
    dosyalar.sort()
    for _, a in dosyalar[: len(dosyalar) - DOSYA_EN_COK]:
        with contextlib.suppress(OSError):
            os.remove(os.path.join(d, a))


def etkin() -> bool:
    return os.environ.get("PVQ_YANIT_ONBELLEK", "0") == "1"


def _damga_etag(tenant_id, plant_id) -> str:
    k = (str(tenant_id), str(plant_id))
    simdi = time.monotonic()
    with _KILIT:
        v = _DAMGA.get(k)
        if v and simdi - v[0] < DAMGA_SN:
            return v[1]
    from pvquant.services import damga_service
    et = damga_service.etag_uret(damga_service.hesapla(tenant_id, plant_id))
    with _KILIT:
        _DAMGA[k] = (simdi, et)
    return et


def _portfoy_etag(tenant_id, portfoy_id) -> str:
    """18.11 DSG/portfoy hiz turu: portfoy damgasi (damga_service.portfoy_hesapla) — uyelerin olcum/kosu/yuklemeleri, uyelik/sozlesme/portfoy
    kayitlari, gece sonucu, piyasa ve is. Santral damgasiyla ayni 5 s hatirlama (ayni _DAMGA sozlugu, «pf» on ekli anahtar)."""
    k = ("pf", str(tenant_id), str(portfoy_id))
    simdi = time.monotonic()
    with _KILIT:
        v = _DAMGA.get(k)
        if v and simdi - v[0] < DAMGA_SN:
            return v[1]
    from pvquant.services import damga_service
    et = damga_service.etag_uret(damga_service.portfoy_hesapla(tenant_id, portfoy_id))
    with _KILIT:
        _DAMGA[k] = (simdi, et)
    return et


def _kiraci_etag(tenant_id) -> str:
    """18.11 gezinme (Parti B #3): kiraci damgasi (damga_service.kiraci_hesapla) — kiracinin tum santralleri + alarm + piyasa/is.
    Ayni 5 s hatirlama (_DAMGA, «k» on ekli anahtar)."""
    k = ("k", str(tenant_id))
    simdi = time.monotonic()
    with _KILIT:
        v = _DAMGA.get(k)
        if v and simdi - v[0] < DAMGA_SN:
            return v[1]
    from pvquant.services import damga_service
    et = damga_service.etag_uret(damga_service.kiraci_hesapla(tenant_id))
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
    return _anahtarla((str(tenant_id), str(plant_id), anahtar, et), uret, ttl_sn)


def getir_portfoy(tenant_id, portfoy_id, anahtar: str, uret: Callable[[], Any], ttl_sn: int = VARSAYILAN_TTL_SN) -> Any:
    """18.11 DSG/portfoy hiz turu: portfoy uclari icin (kiraci, «pf:»+portfoy, uc+parametre, portfoy damgasi etag). Depolama `getir` ile
    ayni (surec LRU + paylasilan dosya katmani); yetki kapisi (_pf_kapi) cagiranda, onbellegin DISINDA kalir."""
    if not etkin():
        SAYAC["atlandi"] += 1
        return uret()
    try:
        et = _portfoy_etag(tenant_id, portfoy_id)
    except Exception:
        SAYAC["atlandi"] += 1
        return uret()
    return _anahtarla((str(tenant_id), "pf:" + str(portfoy_id), anahtar, et), uret, ttl_sn)


def getir_kiraci(tenant_id, anahtar: str, uret: Callable[[], Any], ttl_sn: int = VARSAYILAN_TTL_SN) -> Any:
    """18.11 gezinme (Parti B #3): kiracinin tum santrallerini kapsayan uclar (/v1/portfoy ailesi) icin (kiraci, «k:», uc+parametre,
    kiraci damgasi etag). Depolama `getir` ile ayni; yetki/modul kapisi cagiranda, onbellegin DISINDA."""
    if not etkin():
        SAYAC["atlandi"] += 1
        return uret()
    try:
        et = _kiraci_etag(tenant_id)
    except Exception:
        SAYAC["atlandi"] += 1
        return uret()
    return _anahtarla((str(tenant_id), "k:", anahtar, et), uret, ttl_sn)


def _anahtarla(k: tuple[str, str, str, str], uret: Callable[[], Any], ttl_sn: int) -> Any:
    simdi = time.monotonic()
    with _KILIT:
        v = _KAYIT.get(k)
        if v and simdi - v[0] < ttl_sn:
            _KAYIT.move_to_end(k)
            SAYAC["isabet"] += 1
            return v[1]
    dosyadan = _dosyadan(k, ttl_sn)
    if dosyadan is not None:
        with _KILIT:
            _KAYIT[k] = (simdi, dosyadan)
            _KAYIT.move_to_end(k)
            SAYAC["dosya_isabet"] += 1
            while len(_KAYIT) > EN_COK:
                _KAYIT.popitem(last=False)
        return dosyadan
    from fastapi.encoders import jsonable_encoder
    deger = jsonable_encoder(uret())   # HTTP yanıtıyla birebir aynı JSON biçimi: bellek, dosya ve ağ aynı şeyi söyler
    with _KILIT:
        _KAYIT[k] = (simdi, deger)
        _KAYIT.move_to_end(k)
        SAYAC["iska"] += 1
        while len(_KAYIT) > EN_COK:
            _KAYIT.popitem(last=False)
    _dosyaya(k, deger)
    return deger


def getir_genel(anahtar: str, uret: Callable[[], Any], ttl_sn: int = 600, taze: bool = False) -> Any:
    """Kiracıdan ve santraldan BAĞIMSIZ sistem bilgisi için (16.11 yönetim grubu: /hakkinda meteo arşivinde DISTINCT tarama,
    /kurallar sürüm tablosu). Anahtar damga taşımaz; yalnız TTL ile tazelenir. Kiracı verisi taşıyan yanıtlar için ASLA
    kullanılmaz — çağıran, üreticinin claims/tenant okumadığını garanti eder.
    taze=True (18.11 gezinme Parti 1, isitici): bellek/dosya bakilmaz, uretilip saklanir — TTL dolmadan yenileme (ziyaretci soguk bedel odemesin)."""
    if not etkin():
        SAYAC["atlandi"] += 1
        return uret()
    k = ("*", "*", anahtar, "genel")
    simdi = time.monotonic()
    if not taze:
        with _KILIT:
            v = _KAYIT.get(k)
            if v and simdi - v[0] < ttl_sn:
                _KAYIT.move_to_end(k)
                SAYAC["isabet"] += 1
                return v[1]
    dosyadan = None if taze else _dosyadan(k, ttl_sn)
    if dosyadan is not None:
        with _KILIT:
            _KAYIT[k] = (simdi, dosyadan)
            SAYAC["dosya_isabet"] += 1
        return dosyadan
    from fastapi.encoders import jsonable_encoder
    deger = jsonable_encoder(uret())
    with _KILIT:
        _KAYIT[k] = (simdi, deger)
        SAYAC["iska"] += 1
    _dosyaya(k, deger)
    return deger


def temizle(dosyalar: bool = True) -> None:
    with _KILIT:
        _KAYIT.clear()
        _DAMGA.clear()
    for k in SAYAC:
        SAYAC[k] = 0
    d = _dizin() if dosyalar else None
    if d:
        for a in os.listdir(d):
            if a.endswith(".json"):
                with contextlib.suppress(OSError):
                    os.remove(os.path.join(d, a))
