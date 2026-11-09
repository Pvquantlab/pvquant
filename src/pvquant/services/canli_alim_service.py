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


ZAMAN_ASIMI_MIN_SN, ZAMAN_ASIMI_MAKS_SN = 1.0, 60.0   # v2.549 (D3): profil/bağlantı başına; Fronius Datamanager belgesi ≥10 sn önerir


def hedef_dogrula(host: str, port, birim, zaman_asimi_sn=None, profil=None, cihazlar=None) -> dict:
    """SAF (ağ çözümlemesi hariç). host: IP ya da ana makine adı; port 1–65535; birim 0–247; zaman_asimi_sn 1–60 (isteğe bağlı, varsayılan 5);
    profil: kayıt haritası (sunspec | huawei_smartlogger | sungrow_string | growatt_rtu; v2.552 S2), varsayılan sunspec."""
    from pvquant.io.canli.profiller import profil_al
    pr = profil_al(profil)["kod"]
    h = (host or "").strip()
    if not h or len(h) > 253:
        raise ValueError("host boş ya da çok uzun")
    try:
        p = int(port) if port not in (None, "") else VARSAYILAN_PORT
        b = int(birim) if birim not in (None, "") else VARSAYILAN_BIRIM
        za = float(zaman_asimi_sn) if zaman_asimi_sn not in (None, "") else None
    except (TypeError, ValueError) as e:
        raise ValueError("port, birim ve zaman aşımı sayı olmalı") from e
    if not (1 <= p <= 65535):
        raise ValueError("port 1–65535 arasında olmalı")
    if not (0 <= b <= 247):
        raise ValueError("birim kimliği 0–247 arasında olmalı")
    if za is not None and not (ZAMAN_ASIMI_MIN_SN <= za <= ZAMAN_ASIMI_MAKS_SN):
        raise ValueError("zaman aşımı 1–60 saniye arasında olmalı")
    out = {"host": h, "port": p, "birim": b}
    if za is not None:
        out["zaman_asimi_sn"] = za
    if pr != "sunspec":
        out["profil"] = pr
    if cihazlar:   # v2.558 (V3): aynı kayıt cihazında (host:port) ek inverterler — birim kimliği listesi; en çok 32, tekil, ana birimden farklı
        if not isinstance(cihazlar, list) or len(cihazlar) > 32:
            raise ValueError("ek cihaz listesi en çok 32 kayıt olmalı")
        liste, gorulen = [], {b}
        for c in cihazlar:
            c = c if isinstance(c, dict) else {"birim": c}
            try:
                cb = int(c.get("birim"))
            except (TypeError, ValueError) as e:
                raise ValueError("ek cihaz birim kimliği sayı olmalı") from e
            if not (0 <= cb <= 247):
                raise ValueError("ek cihaz birim kimliği 0–247 arasında olmalı")
            if cb in gorulen:
                raise ValueError(f"birim kimliği {cb} yineleniyor")
            gorulen.add(cb)
            e = {"birim": cb}
            ad = (str(c.get("ad") or "").strip()[:40]) or None
            if ad:
                e["ad"] = ad
            cp = profil_al(c.get("profil"))["kod"] if c.get("profil") else pr
            if cp != "sunspec":
                e["profil"] = cp
            liste.append(e)
        out["cihazlar"] = liste
    return out


def cihaz_oku(istemci, profil: str | None) -> dict:
    """Kayıt haritasına göre cihazı okur: SunSpec keşfi ya da üretici profili (v2.552)."""
    from pvquant.io.canli import sunspec
    from pvquant.io.canli.profiller import oku_cihaz_profil
    pr = (profil or "sunspec").strip().lower()
    return sunspec.oku_cihaz(istemci.oku) if pr == "sunspec" else oku_cihaz_profil(istemci, pr)


def zaman_asimi(h: dict) -> float:
    """Bağlantı kaydındaki zaman aşımı; yoksa genel varsayılan."""
    try:
        return float(h.get("zaman_asimi_sn") or ZAMAN_ASIMI_SN)
    except (TypeError, ValueError):
        return ZAMAN_ASIMI_SN


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


def sina_iec104(ayar: dict, onay: bool, ulas=None, startdt_onayi: bool = False, nokta_tablosu: list | None = None, iec104_ayar: dict | None = None, sorgula=None) -> dict:
    """v2.547: IEC 60870-5-104 ulaşılabilirlik; ASDU/komut yok. v2.548 (Aşama 0, H2): varsayılan yalnız TCP bağlantısı — STARTDT gönderilmez, çünkü ikinci
    bir istemcinin STARTDT'si tek yedeklilik gruplu istasyonlarda birincil SCADA oturumunu düşürebilir (üretici davranışı doğrulanmadı). STARTDT yalnız
    `startdt_onayi` (sahip: PVQuant için ayrı istemci yuvası tanımlandı) ile gönderilir.
    Durumlar: ok (TCP açıldı; STARTDT kipinde con alındı) · protokol_yaniti_yok (STARTDT kipi: TCP var, con yok) · baglanti_hatasi · adres_reddedildi ·
    ayar_hatasi · onay_yok. `ulas` testler için enjekte edilir: (host, port, zaman_asimi, startdt) → dict."""
    from pvquant.io.canli import iec104
    simdi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not onay:
        return {"durum": "onay_yok", "zaman": simdi, "aciklama": "Yalnızca veri okuma izni onayı işaretlenmeden bağlantı sınanmaz."}
    try:
        h = hedef_dogrula(ayar.get("host"), ayar.get("port") or iec104.VARSAYILAN_PORT, 0)
        ip = _cozumle(h["host"])
        izin, neden = adres_izinli(ip)
        if not izin:
            return {"durum": "adres_reddedildi", "zaman": simdi, "aciklama": neden, "hedef": h}
    except ValueError as e:
        return {"durum": "ayar_hatasi", "zaman": simdi, "aciklama": str(e)}
    hedef = {"host": h["host"], "port": h["port"], "ip": ip, "ag": neden}
    # v2.554 (S4): sahip onayı + nokta tablosu varsa SALT-OKUR VERİ SINAMASI — genel sorgulama (C_IC_NA_1) ile noktalar okunur ve tabloyla eşlenir
    if startdt_onayi and nokta_tablosu:
        return _sina_iec104_gi(h, hedef, simdi, nokta_tablosu, iec104_ayar or {}, sorgula)
    try:
        r = (ulas or iec104.ulasilabilirlik)(h["host"], h["port"], ZAMAN_ASIMI_SN, bool(startdt_onayi))
    except OSError as e:
        return {"durum": "baglanti_hatasi", "zaman": simdi, "hedef": hedef, "aciklama": f"İstasyona ulaşılamadı ({type(e).__name__}: {e}). Adres, port (varsayılan 2404), VPN/ağ geçidi ve istemci bağlantısına izin verilen IP listesini denetleyin."}
    if not r.get("startdt_gonderildi"):
        return {"durum": "ok", "zaman": simdi, "hedef": hedef, "ozet": {"tcp": True, "startdt_con": None, "yontem": "tcp"},
                "not": "Yalnız TCP bağlantısı sınandı; IEC 104 STARTDT gönderilmedi (istasyonun mevcut SCADA oturumunu etkilememek için). İstasyonun 104 konuştuğu bu sınamayla kanıtlanmaz. STARTDT sınaması için sahibin «ayrı istemci yuvası tanımlandı» onayı gerekir."}
    if not r.get("startdt_con"):
        return {"durum": "protokol_yaniti_yok", "zaman": simdi, "hedef": hedef, "ozet": {"tcp": True, "startdt_con": False, "yontem": "startdt"},
                "aciklama": "TCP bağlantısı kuruldu, IEC 104 STARTDT onayı gelmedi: port başka bir hizmete ait olabilir ya da istasyon bu istemci IP'sine izin vermiyor."}
    return {"durum": "ok", "zaman": simdi, "hedef": hedef, "ozet": {"tcp": True, "startdt_con": True, "yontem": "startdt"},
            "not": "Ulaşılabilirlik sınaması: yalnız bağlantı katmanı (STARTDT/STOPDT); genel sorgulama dâhil hiçbir komut gönderilmedi, veri okunmadı. Veri çekişi için ASDU adresi ve bilgi nesnesi listesi gerekir."}


def _sina_iec104_gi(h: dict, hedef: dict, simdi: str, nokta_tablosu: list, ayar: dict, sorgula=None) -> dict:
    from pvquant.io.canli import iec104_istemci as ic
    from pvquant.services import iec104_nokta_service as nk
    try:
        prm = ic.Parametreler.ayardan(ayar.get("parametreler"))
        ca = int(ayar.get("ca") or 1)
        if not (1 <= ca <= 65534):
            raise ValueError("ortak adres (CA) 1–65534 arasında olmalı")
        tablo = nk.dogrula(nokta_tablosu)
    except ValueError as e:
        return {"durum": "ayar_hatasi", "zaman": simdi, "hedef": hedef, "aciklama": str(e)}
    try:
        r = (sorgula or ic.genel_sorgulama)(h["host"], h["port"], ca, prm, None)
    except OSError as e:
        return {"durum": "baglanti_hatasi", "zaman": simdi, "hedef": hedef, "aciklama": f"İstasyona ulaşılamadı ({type(e).__name__}: {e})."}
    except ic.Iec104Hata as e:
        if e.kod == "protokol_yaniti_yok":
            return {"durum": "protokol_yaniti_yok", "zaman": simdi, "hedef": hedef, "ozet": {"yontem": "startdt", "startdt_con": False}, "aciklama": f"IEC 104 STARTDT onayı gelmedi: {e}"}
        return {"durum": "veri_modeli_yok", "zaman": simdi, "hedef": hedef, "hata_kodu": e.kod, "aciklama": f"IEC 104 çerçevesi çözülemedi ({e.kod}: {e}); CA/IOA/COT boylarını ve ortak adresi denetleyin."}
    e = nk.esle(r["noktalar"], tablo)
    ozet = {"yontem": "gi", "startdt_con": True, "nokta_sayisi": e["nokta_sayisi"], "tablo_sayisi": e["tablo_sayisi"], "eslesen": e["eslesen"], "ikame": e["ikame"],
            "eksik": e["eksik"][:20], "gelmeyen_ioa": e["gelmeyen_ioa"][:50], "sonlandi": r["sonlandi"], "bilinmeyen_asdu": r["bilinmeyen"], "gonderilen_tipler": r["gonderilen_tipler"],
            "guc_kw": (round(e["olcum"]["guc_w"] / 1000.0, 3) if e["olcum"].get("guc_w") is not None else None),
            "enerji_mwh": (round(e["olcum"]["enerji_wh"] / 1e6, 3) if e["olcum"].get("enerji_wh") is not None else None),
            "durum_kodu": e["olcum"].get("durum_kodu"), "sinir": (ayar.get("sinir") or "plant_gross_ac")}
    if not r["noktalar"]:
        return {"durum": "kismi", "zaman": simdi, "hedef": hedef, "ozet": ozet, "aciklama": "STARTDT onayı alındı ve genel sorgulama gönderildi, ama istasyon hiç nokta döndürmedi (yetki, CA ya da yedeklilik grubu). Komut gönderilmedi."}
    if e["eslesen"] == 0:
        return {"durum": "kismi", "zaman": simdi, "hedef": hedef, "ozet": ozet, "aciklama": f"{e['nokta_sayisi']} nokta geldi, nokta tablosundaki hiçbir IOA ile eşleşmedi; tabloyu istasyonun IOA listesiyle karşılaştırın."}
    return {"durum": "ok", "zaman": simdi, "hedef": hedef, "ozet": ozet,
            "not": f"Salt-okur veri sınaması: genel sorgulama (tip 100) gönderildi, {e['nokta_sayisi']} nokta alındı, {e['eslesen']} alan eşlendi; başka hiçbir komut gönderilmedi. Düzenli çekiş «düzenli veri çekişini başlat» ile ayrıca açılır."}


def sina(ayar: dict, onay: bool, istemci_fabrikasi=None) -> dict:
    """Bağlantı sınaması. ayar: host/port/birim. onay False → yapılmaz. istemci_fabrikasi testler için (host, port, birim, zaman_asimi) → istemci."""
    from pvquant.io.canli import sunspec
    from pvquant.io.canli.modbus_tcp import ModbusHata, ModbusTcpIstemci
    simdi = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not onay:
        return {"durum": "onay_yok", "zaman": simdi, "aciklama": "Yalnızca veri okuma izni onayı işaretlenmeden bağlantı sınanmaz."}
    try:
        h = hedef_dogrula(ayar.get("host"), ayar.get("port"), ayar.get("birim"), ayar.get("zaman_asimi_sn"), ayar.get("profil"))
        ip = _cozumle(h["host"])
        izin, neden = adres_izinli(ip)
        if not izin:
            return {"durum": "adres_reddedildi", "zaman": simdi, "aciklama": neden, "hedef": h}
    except ValueError as e:
        return {"durum": "ayar_hatasi", "zaman": simdi, "aciklama": str(e)}
    fabrika = istemci_fabrikasi or (lambda host, port, birim, za: ModbusTcpIstemci(host, port, birim, za))
    hedef = {**h, "ip": ip, "ag": neden}
    # 08.11 inceleme II (faz 4): «cihaza ulaşılamadı» ile «cihaza erişildi ama veri modeli desteklenmiyor» ayrı durumlardır
    try:
        with fabrika(h["host"], h["port"], h["birim"], zaman_asimi(h)) as c:
            try:
                cihaz = cihaz_oku(c, h.get("profil"))   # v2.552: SunSpec ya da üretici profili
            except ModbusHata as e:   # v2.549 (D3): yapısal hata sınıfı sonuca düşer (protokol_hatasi / cihaz_istisnasi / cihaz_mesgul / zaman_asimi)
                return {"durum": "veri_modeli_yok", "zaman": simdi, "hedef": hedef, "hata_kodu": e.kod,
                        "aciklama": f"Cihaza erişildi; Modbus okuması tamamlanamadı ({e.kod}: {e}). Birim kimliği, zaman aşımı ve cihazın Modbus TCP ayarını denetleyin."}
            except ValueError as e:
                return {"durum": "veri_modeli_yok", "zaman": simdi, "hedef": hedef, "hata_kodu": "veri_modeli_yok",
                        "aciklama": f"Cihaza erişildi; SunSpec veri modeli okunamadı ({e}). Üreticinin Modbus kayıt haritası gerekir; düzenli çekiş bu cihazla kurulamaz."}
    except OSError as e:
        return {"durum": "baglanti_hatasi", "zaman": simdi, "hedef": hedef, "aciklama": f"Cihaza ulaşılamadı ({type(e).__name__}: {e}). Adres, port, VPN/ağ geçidi ve cihazın Modbus TCP ayarını denetleyin."}
    inv = cihaz.get("inverter") or {}
    if not inv:
        return {"durum": "kismi", "zaman": simdi, "hedef": hedef, "cihaz": cihaz,
                "ozet": {"uretici": (cihaz.get("ortak") or {}).get("uretici"), "model": (cihaz.get("ortak") or {}).get("model"), "seri_no": (cihaz.get("ortak") or {}).get("seri_no"),
                         "guc_kw": None, "enerji_mwh": None, "durum": None, "olaylar": [], "model_sayisi": len(cihaz.get("modeller", []))},
                "aciklama": "Cihaza erişildi ve SunSpec ortak modeli okundu; ölçüm modeli (701 ya da 101–103 / 111–113) bulunamadı. Düzenli çekiş için bu model gerekir.",
                "not": "Yalnızca okuma sınaması: yalnız Modbus fonksiyon 3 kullanıldı, cihaza yazılmadı."}
    return {"durum": "ok", "zaman": simdi, "hedef": hedef, "cihaz": cihaz,
            "ozet": {"uretici": (cihaz.get("ortak") or {}).get("uretici"), "model": (cihaz.get("ortak") or {}).get("model"), "seri_no": (cihaz.get("ortak") or {}).get("seri_no"),
                     "guc_kw": (round(inv["guc_w"] / 1000.0, 3) if inv.get("guc_w") is not None else None), "enerji_mwh": (round(inv["enerji_wh"] / 1e6, 3) if inv.get("enerji_wh") is not None else None),
                     "durum": inv.get("durum"), "olaylar": inv.get("olaylar", []), "model_sayisi": len(cihaz.get("modeller", [])),
                     "profil": cihaz.get("profil"), "enerji_yolu": cihaz.get("enerji_yolu"), "uygulanmayan": inv.get("uygulanmayan", []),
                     "sinir": cihaz.get("sinir", "inverter_ac"), "uretici_durum": inv.get("uretici_durum")},   # v2.551/v2.552: profil, enerji kaynağı, ölçüm sınırı
            "not": "Yalnızca okuma sınaması: yalnız Modbus fonksiyon 3 kullanıldı, cihaza yazılmadı. Düzenli veri çekişi bu sınamayla başlamaz; «düzenli veri çekişini başlat» ile ayrıca açılır."
                   + ("" if cihaz.get("enerji_yolu") != "yok" else " Cihaz kümülatif enerji vermiyor; saatlik enerji güç entegrasyonuyla hesaplanır ve «entegrasyon» niteliğiyle işaretlenir.")}
