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
ASAMA_ETIKET = {"secildi": "hedef seçildi", "ayar": "bağlantı ayarı girildi", "sinama": "bağlantı sınaması başarılı", "cekis": "düzenli veri çekişi açık", "akis": "veri alınıyor"}
NOT = ("Dosya kaynakları (SCADA, sayaç) geçmişe dönük çalışır: veri, yüklediğiniz güne kadar gelir; sürekli bağlantı değildir. EPİAŞ Şeffaflık bağlantısı "
       "lisanslı tesiste her gece bir önceki günlerin üretimini çeker. Modbus TCP / SunSpec için cihaz adresi girilip yalnızca okuma onayı verilince bağlantı "
       "sınanabilir; sınama cihaza erişildiğini gösterir, düzenli veri çekişi ayrı bir adımdır ve henüz yoktur. Diğer protokol ve bulut bağlantıları için "
       "gereken bilgiler listelenir; bağlantı, erişim bilgileri ve tesis sahibinin yalnızca okuma onayı geldikten sonra kurulur. Bu liste ne gerektiğini söyler, tarih vermez.")


def tazelik(son: datetime | None, simdi: datetime | None = None, yon: str = "api", esik_saat: float | None = None, dosya_eski_gun: int | None = None) -> dict:
    """SAF. Son başarılı veri gelişinden tazelik. Bağlantı kaynakları (api/protokol): guncel (≤ esik_saat, varsayılan 48 sa) / gecikmis / yok.
    Dosya kaynakları (yon='dosya'): 48 saat ölçütü uygulanmaz — yükleme ritmi müşterinindir; «dosya» (bilgi) ya da eşikten eskiyse «dosya_eski» (uyarı);
    eşik = müşterinin beyan ettiği yükleme sıklığının iki katı (v2.546 `dosya_yukleme_sikligi_gun`), beyan yoksa 30 gün."""
    simdi = simdi or datetime.now(timezone.utc)
    if son is None:
        return {"tazelik": "yok", "tazelik_etiketi": TAZELIK_ETIKET["yok"], "yas_saat": None}
    if son.tzinfo is None:
        son = son.replace(tzinfo=timezone.utc)
    yas = (simdi - son).total_seconds() / 3600.0
    if yon == "dosya":
        esik_gun = (2 * int(dosya_eski_gun)) if dosya_eski_gun else DOSYA_ESKI_GUN
        kod = "dosya_eski" if yas > esik_gun * 24 else "dosya"
        return {"tazelik": kod, "tazelik_etiketi": (f"yükleme {esik_gun} günden eski" if kod == "dosya_eski" else TAZELIK_ETIKET["dosya"]), "yas_saat": round(yas, 1), "esik_gun": esik_gun}
    kod = "guncel" if yas <= (esik_saat or TAZE_SAAT) else "gecikmis"
    return {"tazelik": kod, "tazelik_etiketi": TAZELIK_ETIKET[kod], "yas_saat": round(yas, 1)}


def veri_etiketi(t: dict) -> str:
    """SAF. Tazelik sözlüğünden müşteri cümlesi — bağlantıdan bağımsız VERİ durumu."""
    gun = int(round((t.get("yas_saat") or 0) / 24.0))
    kod = t.get("tazelik")
    if kod == "guncel":
        return "veri güncel"
    if kod == "gecikmis":
        return f"{gun} gündür yeni veri yok" if gun >= 1 else "yeni veri yok"
    if kod == "dosya":
        return f"son yükleme {gun} gün önce" if gun >= 1 else "bugün yüklendi"
    if kod == "dosya_eski":
        return t.get("tazelik_etiketi", "yükleme eski")
    return "veri gelmedi"


def epias_baglanti(cekis: dict | None) -> dict:
    """SAF. Çekiş kaydından BAĞLANTI sağlığı (veri tazeliğinden ayrı): başarılı sorgu, veri eski olsa bile başarılıdır."""
    if not cekis:
        return {"durum": "bilinmiyor", "etiket": "sorgu durumu okunamadı", "zaman": None}
    kod = cekis.get("kod")
    if kod in ("ok", "kayit_yok", "yazilmadi"):
        return {"durum": "ok", "etiket": "son sorgu başarılı", "zaman": cekis.get("zaman")}
    if kod == "hata":
        return {"durum": "hata", "etiket": "son sorgu hatalı", "zaman": cekis.get("zaman")}
    if kod == "atlandi":
        return {"durum": "yok", "etiket": "sorgu atlandı (kimlik/eşleme eksik)", "zaman": cekis.get("zaman")}
    if kod == "yok":
        return {"durum": "yok", "etiket": "henüz sorgu yapılmadı", "zaman": None}
    return {"durum": "bilinmiyor", "etiket": cekis.get("etiket", "sorgu durumu okunamadı"), "zaman": cekis.get("zaman")}


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
        sd = ss.get("durum")
        sin_etiket = (ASAMA_ETIKET["sinama"] if sd == "ok" else "cihaza erişildi, veri modeli desteklenmiyor" if sd == "veri_modeli_yok" else
                      "cihaza erişildi, inverter modeli yok" if sd == "kismi" else "bağlantı sınaması başarısız" if ss else "bağlantı sınanmadı")
        out.append({"kod": "sinama", "etiket": sin_etiket, "tamam": sd == "ok", "zaman": ss.get("zaman"), "durum": sd})
        if tur == "modbus_sunspec":   # v2.546: çekiş sahibin ayrı kararı; sınama onu ima etmez
            out.append({"kod": "cekis", "etiket": ASAMA_ETIKET["cekis"] if beyan.get("ornekleme_acik") else "düzenli veri çekişi başlatılmadı", "tamam": bool(beyan.get("ornekleme_acik")), "zaman": None})
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
    onay = bool(d.get("salt_okuma_onayi"))
    # v2.546 (P4b-2): düzenli çekiş yalnız Modbus hedefinde, bağlantı ayarı ve onay varken açılabilir; sınama tek başına çekiş başlatmaz
    ornekleme = bool(d.get("ornekleme_acik")) and tur == "modbus_sunspec" and baglanti is not None and onay
    return {"veri_yolu": {"tur": tur, "saglayici": sag, "periyot_dk": per, "salt_okuma_onayi": onay, "not": nt,
                          "baglanti": baglanti, "ornekleme_acik": ornekleme, "beyan_zamani": datetime.now(timezone.utc).isoformat(timespec="minutes")}}


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
    sik = pj.get("dosya_yukleme_sikligi_gun")   # v2.546: müşterinin beyan ettiği yükleme sıklığı (gün); eşik iki katı
    if dosya:
        so = son_olcum.get("dosya")
        out.append({"tur": "scada_dosya", "etiket": VERI_YOLLARI["scada_dosya"]["kisa"], "tur_etiketi": "dosya kaynağı", "tanimli": True,
                    "son": dosya["created_at"].isoformat() if dosya["created_at"] else None, "son_olcum": so.isoformat() if so else None,
                    "ayrinti": f"son dosya {dosya['filename']}" + (f" · beyan edilen yükleme sıklığı {int(sik)} gün" if sik else ""),
                    **tazelik(dosya["created_at"], simdi, "dosya", dosya_eski_gun=sik)})
    # v2.546 (P4b-2): Modbus TCP / SunSpec düzenli örnekleme etkinse canlı protokol satırı — eşik 3 × periyot (en az 1 saat)
    vyb = pj.get("veri_yolu") if isinstance(pj.get("veri_yolu"), dict) else None
    if vyb and vyb.get("tur") == "modbus_sunspec" and vyb.get("ornekleme_acik"):
        from pvquant.services import canli_ornekleme_service as co
        d = co.durum(tenant_id, plant)
        if d is not None:
            per = co.periyot_dk(vyb); esik = max(3 * per, 60) / 60.0
            tz = tazelik(d["son_ornek"], simdi, "protokol", esik_saat=esik)
            bag = ({"durum": "yok", "etiket": "henüz örnek alınmadı", "zaman": None} if not d["son_ornek"] else
                   {"durum": "ok", "etiket": "son örnek alındı", "zaman": d["son_ornek"].isoformat()} if tz["tazelik"] == "guncel" else
                   {"durum": "hata", "etiket": "örnek alınamıyor", "zaman": d["son_ornek"].isoformat()})
            out.append({"tur": "modbus_sunspec", "etiket": VERI_YOLLARI["modbus_sunspec"]["kisa"], "tur_etiketi": "saha protokolü", "tanimli": True,
                        "son": d["son_ornek"].isoformat() if d["son_ornek"] else None, "son_olcum": d["son_saat"].isoformat() if d["son_saat"] else None,
                        "baglanti": bag, "veri_etiketi": (f"son saat {d['son_saat'].isoformat()}" if d["son_saat"] else "henüz saatlik veri yazılmadı"),
                        "ayrinti": f"örnekleme {per} dk · son 24 saatte {d['n24']} örnek", **tz})
    if pj.get("epias_santral_id"):
        son = epias["created_at"] if epias else None; so = son_olcum.get("epias")
        tz = tazelik(son, simdi, "api")
        out.append({"tur": "epias_seffaflik", "etiket": VERI_YOLLARI["epias_seffaflik"]["kisa"], "tur_etiketi": "platform bağlantısı", "tanimli": True,
                    "son": son.isoformat() if son else None, "son_olcum": so.isoformat() if so else None, "cekis": cekis,
                    "baglanti": epias_baglanti(cekis), "veri_etiketi": veri_etiketi(tz),
                    "ayrinti": f"santral kimliği {pj['epias_santral_id']}" + ("" if epias else " — bağlantı tanımlı, henüz veri çekilmedi"), **tz})
    for x in sy:
        out.append({"tur": "sayac_dosya", "etiket": VERI_YOLLARI["sayac_dosya"]["kisa"], "tur_etiketi": "dosya kaynağı", "tanimli": True,
                    "son": x["son"].isoformat() if x["son"] else None, "son_olcum": None, "ayrinti": f"kaynak {x['kaynak']}", **tazelik(x["son"], simdi, "dosya", dosya_eski_gun=sik)})
    return out


def ozet(tenant_id, plant: dict, simdi: datetime | None = None) -> dict:
    pj = _pj(plant)
    beyan = pj.get("veri_yolu") if isinstance(pj.get("veri_yolu"), dict) else None
    hedef = _yol(beyan["tur"]) if beyan and beyan.get("tur") in VERI_YOLLARI else None
    etkin = etkin_yollar(tenant_id, plant, simdi)
    sik = pj.get("dosya_yukleme_sikligi_gun")
    return {"etkin": etkin, "beyan": beyan, "hedef": hedef, "asamalar": asamalar(beyan, etkin), "yollar": [_yol(k) for k in VERI_YOLLARI],
            "taze_saat": TAZE_SAAT, "dosya_eski_gun": (2 * int(sik) if sik else DOSYA_ESKI_GUN), "dosya_yukleme_sikligi_gun": sik, "not": NOT}
