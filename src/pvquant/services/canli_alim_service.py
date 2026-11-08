"""08.11.2026 v2.545 (P4b ilk bağlayıcı; IH-023) — Modbus TCP / SunSpec bağlantı sınaması (sahibin tetiklediği, yalnız okuma).

Ne yapar: hedeflenen veri kaynağı `modbus_sunspec` ve bağlantı ayarı (host, port, birim) girildiyse, yalnızca okuma izni onayı varsa, cihaza bağlanıp
SunSpec keşfi + ortak model (üretici/model/seri) + inverter anlık ölçümlerini döner. Yazma yok (istemci yapısal olarak FC3). Düzenli çekiş (örnekleme işi
ve saatlik toplama) bu paketin DIŞINDA — sınama cihaz/ağ erişiminin çalıştığını kanıtlar; veri akışı sonraki pakette.
Güvenlik: hedef adres doğrulanır — loopback, link-local, multicast, ayrılmış ve belirsiz adresler reddedilir; ÖZEL ağ adreslerine izin verilir (saha
VPN'i tipik olarak özel ağdır; webhook SSRF kuralından bilinçli fark). Ana makine adı çözümlenip aynı kurala vurulur. Sahip onayı yoksa sınama yapılmaz.
Her sınama denetim izine yazılır (çağıran katman).
"""
from __future__ import annotations

import ipaddress
import socket
from datetime import datetime, timezone

VARSAYILAN_PORT = 502
VARSAYILAN_BIRIM = 1
ZAMAN_ASIMI_SN = 5.0


def hedef_dogrula(host: str, port, birim) -> dict:
    """SAF (ağ çözümlemesi hariç). host: IP ya da ana makine adı; port 1–65535; birim 0–247."""
    h = (host or "").strip()
    if not h or len(h) > 253:
        raise ValueError("host boş ya da çok uzun")
    try:
        p = int(port) if port not in (None, "") else VARSAYILAN_PORT
        b = int(birim) if birim not in (None, "") else VARSAYILAN_BIRIM
    except (TypeError, ValueError) as e:
        raise ValueError("port ve birim tam sayı olmalı") from e
    if not (1 <= p <= 65535):
        raise ValueError("port 1–65535 arasında olmalı")
    if not (0 <= b <= 247):
        raise ValueError("birim kimliği 0–247 arasında olmalı")
    return {"host": h, "port": p, "birim": b}


def adres_izinli(ip: str) -> tuple[bool, str]:
    """Loopback / link-local / multicast / ayrılmış / belirsiz → ret; özel ağ (VPN) ve genel adres → izin."""
    a = ipaddress.ip_address(ip)
    if a.is_loopback or a.is_link_local or a.is_multicast or a.is_reserved or a.is_unspecified:
        return False, "hedef adres yerel/ayrılmış aralıkta; sahadaki cihaz ya da VPN adresi gerekir"
    return True, "özel ağ (VPN) adresi" if a.is_private else "genel adres"


def _cozumle(host: str) -> str:
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    try:
        return socket.getaddrinfo(host, None)[0][4][0]
    except socket.gaierror as e:
        raise ValueError(f"ana makine adı çözümlenemedi: {host}") from e


def sina(ayar: dict, onay: bool, istemci_fabrikasi=None) -> dict:
    """Bağlantı sınaması. ayar: host/port/birim. onay False → yapılmaz. istemci_fabrikasi testler için (host, port, birim, zaman_asimi) → istemci."""
    from pvquant.io.canli import sunspec
    from pvquant.io.canli.modbus_tcp import ModbusHata, ModbusTcpIstemci
    simdi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not onay:
        return {"durum": "onay_yok", "zaman": simdi, "aciklama": "Yalnızca veri okuma izni onayı işaretlenmeden bağlantı sınanmaz."}
    try:
        h = hedef_dogrula(ayar.get("host"), ayar.get("port"), ayar.get("birim"))
        ip = _cozumle(h["host"])
        izin, neden = adres_izinli(ip)
        if not izin:
            return {"durum": "adres_reddedildi", "zaman": simdi, "aciklama": neden, "hedef": h}
    except ValueError as e:
        return {"durum": "ayar_hatasi", "zaman": simdi, "aciklama": str(e)}
    fabrika = istemci_fabrikasi or (lambda host, port, birim, za: ModbusTcpIstemci(host, port, birim, za))
    try:
        with fabrika(h["host"], h["port"], h["birim"], ZAMAN_ASIMI_SN) as c:
            cihaz = sunspec.oku_cihaz(c.oku)
    except (OSError, ModbusHata, ValueError) as e:
        return {"durum": "baglanti_hatasi", "zaman": simdi, "hedef": {**h, "ip": ip, "ag": neden}, "aciklama": f"{type(e).__name__}: {e}"}
    inv = cihaz.get("inverter") or {}
    return {"durum": "ok", "zaman": simdi, "hedef": {**h, "ip": ip, "ag": neden}, "cihaz": cihaz,
            "ozet": {"uretici": (cihaz.get("ortak") or {}).get("uretici"), "model": (cihaz.get("ortak") or {}).get("model"), "seri_no": (cihaz.get("ortak") or {}).get("seri_no"),
                     "guc_kw": (round(inv["guc_w"] / 1000.0, 3) if inv.get("guc_w") is not None else None), "enerji_mwh": (round(inv["enerji_wh"] / 1e6, 3) if inv.get("enerji_wh") is not None else None),
                     "durum": inv.get("durum"), "olaylar": inv.get("olaylar", []), "model_sayisi": len(cihaz.get("modeller", []))},
            "not": "Salt okuma sınaması: yalnız Modbus fonksiyon 3 kullanıldı, cihaza yazılmadı. Düzenli veri çekişi bu sınamayla başlamaz; ayrı pakette."}
