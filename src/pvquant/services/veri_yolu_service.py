"""08.11.2026 v2.544 (dalga 3 kalanı; P4b protokol/inverter canlı alımı — hazırlık; IH-023, IH-088) — veri kaynakları, bağlantı durumu ve hazırlık listesi.

Uygulamada MEVCUT kaynak türleri: SCADA/izleme dosyası yükleme (dosya tabanlı — sürekli bağlantı değil), EPİAŞ Şeffaflık gerçek zamanlı üretim
(platform bağlantısı; lisanslı tesiste santral kimliğiyle gece çekişi), sayaç dosyası (OSOS / MASS / EPYS — dosya tabanlı). Protokol ve bulut API
alımı (Modbus TCP/SunSpec, IEC 60870-5-104, OPC UA, inverter bulutları) ayrı yatırım kararı: BAĞLANTI KURULMADI. v2.545: Modbus TCP / SunSpec için
salt-okuma bağlayıcı ve sahibin onayıyla bağlantı sınaması var (canli_alim_service); düzenli çekiş ayrı paket. Diğerleri için cihaz/ağ erişimi, yalnızca
okuma izni ve sahip onayı gelmeden bağlayıcı yazılmaz (yol haritası P4 (b)).

Durum ayrımı (brif 08.11): kaynak türü mevcut mu (`durum`), bağlantı/eşleme tanımlı mı (`tanimli`), son başarılı veri geliş zamanı (`son`), tazelik
(`tazelik`: guncel ≤ 48 sa / gecikmis > 48 sa / yok), hazırlık (`kurulmadi`). «Canlı» sözü kullanılmaz: dosya yüklemesi geçmişe dönük bir kaynaktır.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

TAZE_SAAT = 48
DOSYA_ESKI_GUN = 30   # 08.11 inceleme (faz 3): dosya kaynağında 48 saat ölçütü anlamsız (yükleme ritmi müşterinindir); 30 günden eski yükleme yalnız bilgi uyarısı
EPIAS_IS_ADI = "gece_epias_uretim"

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
                           "not": "Üretici başına ayrı bağlantı gerekir; ilk bağlantı, yalnızca okuma izinli anahtar ve örnek çıktı geldikten sonra kurulur. Bağlantı henüz kurulmadı."},
    "modbus_sunspec": {"etiket": "Modbus TCP / SunSpec (inverter, enerji sayacı, kirlenme sensörü)", "kisa": "Modbus TCP / SunSpec", "durum": "kurulmadi", "yon": "protokol", "tur_etiketi": "saha protokolü",
                       "gerekenler": ["Saha ağına yalnızca okuma erişimi (VPN ya da ağ geçidi), IP:port ve birim kimliği", "Kayıt haritası: SunSpec model numaraları ya da üretici Modbus tablosu", "Sahip onayı ve yazma kapalı siber güvenlik politikası", "Sorgu periyodu ve sayaç/sensör listesi"],
                       "not": "SolarPower Europe O&M v6.0 kirlenme sensörü ve enerji sayacı için Modbus önerir (öneri, zorunluluk değil). Cihaz adresi girilip yalnızca okuma onayı verilince bağlantı sınanabilir; düzenli veri çekişi henüz yok."},
    "iec104": {"etiket": "IEC 60870-5-104 (SCADA / PPC)", "kisa": "IEC 60870-5-104", "durum": "kurulmadi", "yon": "protokol", "tur_etiketi": "saha protokolü",
               "gerekenler": ["TEİAŞ RTU hattından AYRI, yalnızca okuma istemci bağlantısı", "ASDU adresi ve bilgi nesnesi (IOA) listesi", "İşletmeci ve sahip onayı"],
               "not": "RTU → TEİAŞ hattına dokunulmaz; PVQuant yalnız ayrı bir izleme istemcisi olabilir. Bağlantı henüz kurulmadı."},
    "opc_ua": {"etiket": "OPC UA (SCADA sunucusu)", "kisa": "OPC UA", "durum": "kurulmadi", "yon": "protokol", "tur_etiketi": "saha protokolü",
               "gerekenler": ["OPC UA uç noktası ve yalnızca okuma kullanıcı/sertifika", "Düğüm (node) listesi: güç, enerji, ışınım, sıcaklık", "Sahip onayı"],
               "not": "Saha SCADA'sı destekliyorsa en temiz yol; yazma kapalı. Bağlantı henüz kurulmadı."},
}
DURUM_ETIKET = {"mevcut": "uygulamada mevcut", "kurulmadi": "bağlantı henüz kurulmadı"}
TAZELIK_ETIKET = {"guncel": "güncel", "gecikmis": "gecikmiş", "yok": "veri gelmedi", "dosya": "dosya yüklemesi", "dosya_eski": "yükleme 30 günden eski"}
ASAMA_ETIKET = {"secildi": "hedef seçildi", "ayar": "bağlantı ayarı girildi", "sinama": "bağlantı sınaması başarılı", "akis": "veri alınıyor"}
NOT = ("Dosya kaynakları (SCADA, sayaç) geçmişe dönük çalışır: veri, yüklediğiniz güne kadar gelir; sürekli bağlantı değildir. EPİAŞ Şeffaflık bağlantısı "
       "lisanslı tesiste her gece bir önceki günlerin üretimini çeker. Modbus TCP / SunSpec için cihaz adresi girilip yalnızca okuma onayı verilince bağlantı "
       "sınanabilir; sınama cihaza erişildiğini gösterir, düzenli veri çekişi ayrı bir adımdır ve henüz yoktur. Diğer protokol ve bulut bağlantıları için "
       "gereken bilgiler listelenir; bağlantı, erişim bilgileri ve tesis sahibinin yalnızca okuma onayı geldikten sonra kurulur. Bu liste ne gerektiğini söyler, tarih vermez.")


def tazelik(son: datetime | None, simdi: datetime | None = None, yon: str = "api") -> dict:
    """SAF. Son başarılı veri gelişinden tazelik. Bağlantı kaynakları (api/protokol): guncel (≤ 48 sa) / gecikmis / yok.
    Dosya kaynakları (yon='dosya'): 48 saat ölçütü uygulanmaz — yükleme ritmi müşterinindir; «dosya» (bilgi) ya da 30 günden eskiyse «dosya_eski» (uyarı)."""
    simdi = simdi or datetime.now(timezone.utc)
    if son is None:
        return {"tazelik": "yok", "tazelik_etiketi": TAZELIK_ETIKET["yok"], "yas_saat": None}
    if son.tzinfo is None:
        son = son.replace(tzinfo=timezone.utc)
    yas = (simdi - son).total_seconds() / 3600.0
    if yon == "dosya":
        kod = "dosya_eski" if yas > DOSYA_ESKI_GUN * 24 else "dosya"
    else:
        kod = "guncel" if yas <= TAZE_SAAT else "gecikmis"
    return {"tazelik": kod, "tazelik_etiketi": TAZELIK_ETIKET[kod], "yas_saat": round(yas, 1)}


def epias_cekis_durumu(status: str | None, detail: str | None) -> dict:
    """SAF. jobs_log'daki son gece_epias_uretim satırından çekiş durumu: hata / yeni kayıt yok / yazılmadı (SCADA öncelikli) / başarılı / ayrıntısız.
    Bağlantı hatası ile «EPİAŞ'ta yeni kayıt yok» ayrılır (brif faz 3)."""
    if status is None:
        return {"kod": "yok", "etiket": "henüz çekiş yapılmadı"}
    if status != "ok":
        return {"kod": "hata", "etiket": "son çekiş hatayla bitti", "ayrinti": (detail or "")[:160] or None}
    d = detail or ""
    m = re.search(r"'durum':\s*'(\w+)'", d); n = re.search(r"'n_yazilan':\s*(\d+)", d)
    durum = m.group(1) if m else None; yazilan = int(n.group(1)) if n else None
    if durum == "veri_yok":
        return {"kod": "kayit_yok", "etiket": "çekiş başarılı, EPİAŞ'ta yeni kayıt yok"}
    if durum == "atlandi":
        return {"kod": "atlandi", "etiket": "çekiş atlandı (kimlik ya da eşleme eksik)"}
    if durum == "ok" and yazilan == 0:
        return {"kod": "yazilmadi", "etiket": "çekiş başarılı, yeni saat yazılmadı (SCADA verisi öncelikli)"}
    if durum == "ok":
        return {"kod": "ok", "etiket": f"son çekiş başarılı ({yazilan} saat yazıldı)"}
    return {"kod": "ok", "etiket": "son çekiş başarılı"}


def asamalar(beyan: dict | None, etkin: list[dict]) -> list[dict]:
    """SAF. Hedef bağlantının aşamaları ayrı durumlarla: seçildi → ayar girildi → sınama başarılı → veri alınıyor. Hiçbiri diğerini ima etmez."""
    if not beyan or not beyan.get("tur"):
        return []
    tur = beyan["tur"]; yon = VERI_YOLLARI.get(tur, {}).get("yon")
    akis = any(e.get("tur") == tur and e.get("son") for e in etkin)
    out = [{"kod": "secildi", "etiket": ASAMA_ETIKET["secildi"], "tamam": True, "zaman": beyan.get("beyan_zamani")}]
    if yon in ("protokol", "api") and VERI_YOLLARI.get(tur, {}).get("durum") == "kurulmadi":
        ss = beyan.get("son_sinama") or {}
        out.append({"kod": "ayar", "etiket": ASAMA_ETIKET["ayar"], "tamam": bool(beyan.get("baglanti")), "zaman": None})
        out.append({"kod": "sinama", "etiket": ASAMA_ETIKET["sinama"] if ss.get("durum") == "ok" else ("bağlantı sınaması başarısız" if ss else "bağlantı sınanmadı"),
                    "tamam": ss.get("durum") == "ok", "zaman": ss.get("zaman"), "durum": ss.get("durum")})
    out.append({"kod": "akis", "etiket": ASAMA_ETIKET["akis"] if akis else "veri alınmıyor", "tamam": akis, "zaman": None})
    return out


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
    baglanti = None
    b = d.get("baglanti")
    if isinstance(b, dict) and (b.get("host") or "").strip():   # v2.545: Modbus TCP/SunSpec hedefi (host, port, birim) — yalnız sınama için; parola yok
        from pvquant.services.canli_alim_service import hedef_dogrula
        baglanti = hedef_dogrula(b.get("host"), b.get("port"), b.get("birim"))
    return {"veri_yolu": {"tur": tur, "saglayici": sag, "periyot_dk": per, "salt_okuma_onayi": bool(d.get("salt_okuma_onayi")), "not": nt,
                          "baglanti": baglanti, "beyan_zamani": datetime.now(timezone.utc).isoformat(timespec="minutes")}}


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
        # 08.11 inceleme (faz 3): «son veri gelişi» (yükleme/çekiş anı) ile «son ölçüm zamanı» (verinin kendi damgası) ayrı
        try:
            olc = s.execute(text(
                "SELECT CASE WHEN b.format_json->>'kaynak' = 'epias_realtime' THEN 'epias' ELSE 'dosya' END AS k, max(sh.ts_utc) AS son "
                "FROM scada_hourly sh JOIN ingestion_batches b ON b.id = sh.batch_id WHERE sh.plant_id=:p AND sh.flag='valid' GROUP BY 1"), {"p": plant["id"]}).mappings().all()
            son_olcum = {r["k"]: r["son"] for r in olc}
        except Exception:   # noqa: BLE001
            son_olcum = {}
    cekis = None
    if pj.get("epias_santral_id"):
        try:
            from pvquant.db import sistem_baglami
            with sistem_baglami() as s2:
                j = s2.execute(text("SELECT started, status, detail FROM jobs_log WHERE job=:j AND plant_id=CAST(:p AS uuid) ORDER BY started DESC LIMIT 1"),
                               {"j": EPIAS_IS_ADI, "p": plant["id"]}).mappings().first()
            cekis = {**epias_cekis_durumu(j["status"] if j else None, j["detail"] if j else None), "zaman": (j["started"].isoformat() if j and j["started"] else None)}
        except Exception as e:   # noqa: BLE001 — iş günlüğü okunamazsa durum bilinmez, uydurulmaz
            cekis = {"kod": "bilinmiyor", "etiket": f"çekiş durumu okunamadı ({type(e).__name__})", "zaman": None}
    if dosya:
        so = son_olcum.get("dosya")
        out.append({"tur": "scada_dosya", "etiket": VERI_YOLLARI["scada_dosya"]["kisa"], "tur_etiketi": "dosya kaynağı", "tanimli": True,
                    "son": dosya["created_at"].isoformat() if dosya["created_at"] else None, "son_olcum": so.isoformat() if so else None,
                    "ayrinti": f"son dosya {dosya['filename']}", **tazelik(dosya["created_at"], simdi, "dosya")})
    if pj.get("epias_santral_id"):
        son = epias["created_at"] if epias else None; so = son_olcum.get("epias")
        out.append({"tur": "epias_seffaflik", "etiket": VERI_YOLLARI["epias_seffaflik"]["kisa"], "tur_etiketi": "platform bağlantısı", "tanimli": True,
                    "son": son.isoformat() if son else None, "son_olcum": so.isoformat() if so else None, "cekis": cekis,
                    "ayrinti": f"santral kimliği {pj['epias_santral_id']}" + ("" if epias else " — bağlantı tanımlı, henüz veri çekilmedi"), **tazelik(son, simdi, "api")})
    for x in sy:
        out.append({"tur": "sayac_dosya", "etiket": VERI_YOLLARI["sayac_dosya"]["kisa"], "tur_etiketi": "dosya kaynağı", "tanimli": True,
                    "son": x["son"].isoformat() if x["son"] else None, "son_olcum": None, "ayrinti": f"kaynak {x['kaynak']}", **tazelik(x["son"], simdi, "dosya")})
    return out


def ozet(tenant_id, plant: dict, simdi: datetime | None = None) -> dict:
    pj = _pj(plant)
    beyan = pj.get("veri_yolu") if isinstance(pj.get("veri_yolu"), dict) else None
    hedef = _yol(beyan["tur"]) if beyan and beyan.get("tur") in VERI_YOLLARI else None
    etkin = etkin_yollar(tenant_id, plant, simdi)
    return {"etkin": etkin, "beyan": beyan, "hedef": hedef, "asamalar": asamalar(beyan, etkin), "yollar": [_yol(k) for k in VERI_YOLLARI],
            "taze_saat": TAZE_SAAT, "dosya_eski_gun": DOSYA_ESKI_GUN, "not": NOT}
