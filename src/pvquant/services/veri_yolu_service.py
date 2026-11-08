"""08.11.2026 v2.544 (dalga 3 kalanı; P4b protokol/inverter canlı alımı — hazırlık; IH-023, IH-088) — veri kaynakları, bağlantı durumu ve hazırlık listesi.

Uygulamada MEVCUT kaynak türleri: SCADA/izleme dosyası yükleme (dosya tabanlı — sürekli bağlantı değil), EPİAŞ Şeffaflık gerçek zamanlı üretim
(platform bağlantısı; lisanslı tesiste santral kimliğiyle gece çekişi), sayaç dosyası (OSOS / MASS / EPYS — dosya tabanlı). Protokol ve bulut API
alımı (Modbus TCP/SunSpec, IEC 60870-5-104, OPC UA, inverter bulutları) ayrı yatırım kararı: BAĞLANTI KURULMADI; cihaz/ağ erişimi, yalnızca okuma
izni ve sahip onayı gelmeden bağlayıcı yazılmaz (yol haritası P4 (b)).

Durum ayrımı (brif 08.11): kaynak türü mevcut mu (`durum`), bağlantı/eşleme tanımlı mı (`tanimli`), son başarılı veri geliş zamanı (`son`), tazelik
(`tazelik`: guncel ≤ 48 sa / gecikmis > 48 sa / yok), hazırlık (`kurulmadi`). «Canlı» sözü kullanılmaz: dosya yüklemesi geçmişe dönük bir kaynaktır.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

TAZE_SAAT = 48

VERI_YOLLARI: dict[str, dict] = {
    "scada_dosya": {"etiket": "SCADA / izleme dosyası yükleme (CSV, XLSX)", "kisa": "SCADA dosyası", "durum": "mevcut", "yon": "dosya", "tur_etiketi": "dosya kaynağı",
                    "gerekenler": ["Saatlik ya da daha sık dışa aktarım dosyası", "Veri yükleme sihirbazında kolon eşlemesi (bir kez)", "Düzenli yükleme ya da otomatik dışa aktarım klasörü"],
                    "not": "Bugün tüm segmentlerde çalışan yol. Dosya tabanlıdır: veri yüklediğiniz güne kadar gelir, sürekli bağlantı değildir. Cihaz/invertör bazlı geniş tablolar toplanarak alınır."},
    "epias_seffaflik": {"etiket": "EPİAŞ Şeffaflık gerçek zamanlı üretim (lisanslı tesis)", "kisa": "EPİAŞ Şeffaflık", "durum": "mevcut", "yon": "api", "tur_etiketi": "platform bağlantısı",
                        "gerekenler": ["Şeffaflık Platformu santral kimliği (Santral ayarları › EPİAŞ)", "Platform düzeyinde EPİAŞ kimliği (PVQuant'ta tanımlı)"],
                        "not": "Saatlik gerçekleşen üretim her gece çekilir; SCADA yüklemesi varsa o önceliklidir. Yalnız lisanslı tesislerde."},
    "sayac_dosya": {"etiket": "Sayaç dosyası (OSOS / MASS / EPYS dışa aktarımı)", "kisa": "Sayaç dosyası", "durum": "mevcut", "yon": "dosya", "tur_etiketi": "dosya kaynağı",
                    "gerekenler": ["Dağıtım şirketi OSOS portalı, MASS ya da EPYS'den dönem dosyası", "Sayaç türü beyanı (Sayaç sayfası)"],
                    "not": "Uzlaştırma girdisi ve SCADA–sayaç kıyası için; Sayaç sayfasından yüklenir. Dosya tabanlıdır."},
    "inverter_bulut_api": {"etiket": "İnverter bulutu API (FusionSolar, iSolarCloud, Sunny Portal, SolisCloud, GoodWe …)", "kisa": "İnverter bulutu API", "durum": "kurulmadi", "yon": "api", "tur_etiketi": "bulut bağlantısı",
                           "gerekenler": ["Üretici portalında yalnızca okuma izinli API hesabı / Northbound anahtarı", "Sahip onayı ve varsa veri erişim bedeli", "Santral ve cihaz kimlikleri (inverter listesi)", "Örnek 48 saatlik çıktı (alan adları, zaman dilimi, birimler)", "Alarm/durum kodu sözlüğü (inverter alarmlarının ortak kategoriye eşlenmesi için)"],
                           "not": "Üretici başına ayrı bağlayıcı gerekir; ilk bağlayıcı anahtar ve örnek çıktı geldikten sonra yazılır. Bağlantı henüz kurulmadı."},
    "modbus_sunspec": {"etiket": "Modbus TCP / SunSpec (inverter, enerji sayacı, kirlenme sensörü)", "kisa": "Modbus TCP / SunSpec", "durum": "kurulmadi", "yon": "protokol", "tur_etiketi": "saha protokolü",
                       "gerekenler": ["Saha ağına yalnızca okuma erişimi (VPN ya da ağ geçidi), IP:port ve birim kimliği", "Kayıt haritası: SunSpec model numaraları ya da üretici Modbus tablosu", "Sahip onayı ve yazma kapalı siber güvenlik politikası", "Sorgu periyodu ve sayaç/sensör listesi"],
                       "not": "SolarPower Europe O&M v6.0 kirlenme sensörü ve enerji sayacı için Modbus önerir (öneri, zorunluluk değil). Bağlantı henüz kurulmadı."},
    "iec104": {"etiket": "IEC 60870-5-104 (SCADA / PPC)", "kisa": "IEC 60870-5-104", "durum": "kurulmadi", "yon": "protokol", "tur_etiketi": "saha protokolü",
               "gerekenler": ["TEİAŞ RTU hattından AYRI, yalnızca okuma istemci bağlantısı", "ASDU adresi ve bilgi nesnesi (IOA) listesi", "İşletmeci ve sahip onayı"],
               "not": "RTU → TEİAŞ hattına dokunulmaz; PVQuant yalnız ayrı bir izleme istemcisi olabilir. Bağlantı henüz kurulmadı."},
    "opc_ua": {"etiket": "OPC UA (SCADA sunucusu)", "kisa": "OPC UA", "durum": "kurulmadi", "yon": "protokol", "tur_etiketi": "saha protokolü",
               "gerekenler": ["OPC UA uç noktası ve yalnızca okuma kullanıcı/sertifika", "Düğüm (node) listesi: güç, enerji, ışınım, sıcaklık", "Sahip onayı"],
               "not": "Saha SCADA'sı destekliyorsa en temiz yol; yazma kapalı. Bağlantı henüz kurulmadı."},
}
DURUM_ETIKET = {"mevcut": "uygulamada mevcut", "kurulmadi": "bağlantı henüz kurulmadı"}
TAZELIK_ETIKET = {"guncel": "güncel", "gecikmis": "gecikmiş", "yok": "veri gelmedi"}
NOT = ("Protokol ve bulut API alımı ayrı yatırım kararıdır (yol haritası P4 (b)): cihaz/ağ erişimi, yalnızca okuma izni ve sahip onayı gelmeden bağlayıcı "
       "yazılmaz; liste ne gerektiğini söyler, tarih vermez. Bugün veri dosya yükleme, EPİAŞ Şeffaflık bağlantısı (lisanslı) ve sayaç dosyasıyla gelir; "
       "dosya kaynakları geçmişe dönüktür, sürekli bağlantı değildir.")


def tazelik(son: datetime | None, simdi: datetime | None = None) -> dict:
    """SAF. Son başarılı veri gelişinden tazelik: guncel (≤ 48 sa) / gecikmis / yok."""
    simdi = simdi or datetime.now(timezone.utc)
    if son is None:
        return {"tazelik": "yok", "tazelik_etiketi": TAZELIK_ETIKET["yok"], "yas_saat": None}
    if son.tzinfo is None:
        son = son.replace(tzinfo=timezone.utc)
    yas = (simdi - son).total_seconds() / 3600.0
    kod = "guncel" if yas <= TAZE_SAAT else "gecikmis"
    return {"tazelik": kod, "tazelik_etiketi": TAZELIK_ETIKET[kod], "yas_saat": round(yas, 1)}


def dogrula(d: dict) -> dict:
    """SAF. Hedeflenen veri kaynağı beyanı: tur (VERI_YOLLARI), saglayici (≤64), periyot_dk (1–1440), salt_okuma_onayi (bool), not (≤300). tur None → silinir."""
    if not isinstance(d, dict):
        raise ValueError("veri kaynağı beyanı sözlük olmalı")
    tur = d.get("tur")
    if tur in (None, ""):
        return {"veri_yolu": None}
    tur = str(tur).strip()
    if tur not in VERI_YOLLARI:
        raise ValueError(f"tur {', '.join(VERI_YOLLARI)} arasından olmalı")
    sag = d.get("saglayici"); sag = (str(sag).strip()[:64] or None) if sag not in (None, "") else None
    per = d.get("periyot_dk"); per = None if per in (None, "") else int(per)
    if per is not None and not (1 <= per <= 1440):
        raise ValueError("periyot_dk 1–1440 arasında olmalı")
    nt = d.get("not"); nt = (str(nt).strip()[:300] or None) if nt not in (None, "") else None
    return {"veri_yolu": {"tur": tur, "saglayici": sag, "periyot_dk": per, "salt_okuma_onayi": bool(d.get("salt_okuma_onayi")), "not": nt,
                          "beyan_zamani": datetime.now(timezone.utc).isoformat(timespec="minutes")}}


def _pj(plant: dict) -> dict:
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    return pj


def _yol(tur: str) -> dict:
    v = VERI_YOLLARI[tur]
    return {"tur": tur, **v, "durum_etiketi": DURUM_ETIKET[v["durum"]]}


def etkin_yollar(tenant_id, plant: dict, simdi: datetime | None = None) -> list[dict]:
    """Santralın tanımlı/kullanılmış kaynakları: tür, tanımlı mı, son başarılı geliş, tazelik (DB)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    pj = _pj(plant); out = []
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT filename, created_at, format_json FROM ingestion_batches WHERE plant_id=:p ORDER BY created_at DESC LIMIT 20"), {"p": plant["id"]}).mappings().all()
        dosya = next((x for x in r if not (isinstance(x["format_json"], dict) and x["format_json"].get("kaynak") == "epias_realtime")), None)
        epias = next((x for x in r if isinstance(x["format_json"], dict) and x["format_json"].get("kaynak") == "epias_realtime"), None)
        try:
            sy = s.execute(text("SELECT kaynak, max(olusturma) AS son FROM sayac_yukleme WHERE plant_id=:p GROUP BY kaynak"), {"p": plant["id"]}).mappings().all()
        except Exception:   # noqa: BLE001 — tablo yoksa
            sy = []
    if dosya:
        out.append({"tur": "scada_dosya", "etiket": VERI_YOLLARI["scada_dosya"]["kisa"], "tur_etiketi": "dosya kaynağı", "tanimli": True,
                    "son": dosya["created_at"].isoformat() if dosya["created_at"] else None, "ayrinti": f"son dosya {dosya['filename']}", **tazelik(dosya["created_at"], simdi)})
    if pj.get("epias_santral_id"):
        son = epias["created_at"] if epias else None
        out.append({"tur": "epias_seffaflik", "etiket": VERI_YOLLARI["epias_seffaflik"]["kisa"], "tur_etiketi": "platform bağlantısı", "tanimli": True,
                    "son": son.isoformat() if son else None, "ayrinti": f"santral kimliği {pj['epias_santral_id']}" + ("" if epias else " — bağlantı tanımlı, henüz veri çekilmedi"), **tazelik(son, simdi)})
    for x in sy:
        out.append({"tur": "sayac_dosya", "etiket": VERI_YOLLARI["sayac_dosya"]["kisa"], "tur_etiketi": "dosya kaynağı", "tanimli": True,
                    "son": x["son"].isoformat() if x["son"] else None, "ayrinti": f"kaynak {x['kaynak']}", **tazelik(x["son"], simdi)})
    return out


def ozet(tenant_id, plant: dict, simdi: datetime | None = None) -> dict:
    pj = _pj(plant)
    beyan = pj.get("veri_yolu") if isinstance(pj.get("veri_yolu"), dict) else None
    hedef = _yol(beyan["tur"]) if beyan and beyan.get("tur") in VERI_YOLLARI else None
    return {"etkin": etkin_yollar(tenant_id, plant, simdi), "beyan": beyan, "hedef": hedef, "yollar": [_yol(k) for k in VERI_YOLLARI],
            "taze_saat": TAZE_SAAT, "not": NOT}
