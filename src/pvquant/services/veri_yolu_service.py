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

from pvquant.services import kalite_sozlugu as _ks  # v2.598 (F4-C): flag süzgeci tek sözlükten

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
    "inverter_bulut_api": {"etiket": "İnverter bulutu API (FusionSolar, SolarEdge, SolisCloud, iSolarCloud, Growatt)", "kisa": "İnverter bulutu API", "durum": "kurulmadi", "yon": "api", "tur_etiketi": "bulut bağlantısı",
                           "gerekenler": ["Üretici portalında yalnızca okuma izinli API hesabı / Northbound anahtarı", "Sahip onayı ve varsa veri erişim bedeli", "Santral ve cihaz kimlikleri (inverter listesi)", "Örnek 48 saatlik çıktı (alan adları, zaman dilimi, birimler)", "Alarm/durum kodu sözlüğü (inverter alarmlarının ortak kategoriye eşlenmesi için)"],
                           "not": "Beş bulut bağlantısı üreticilerin herkese açık belgelerine göre hazırlandı: Huawei FusionSolar (Northbound), SolarEdge V2 (filo anahtarı), SolisCloud, Sungrow iSolarCloud, Growatt OpenAPI v1. Anahtarla sınanabilir; sahibin iki onayıyla kimlik şifreli saklanır ve saatlik üretim düzenli çekilir; çekilen saatler birim doğrulanana kadar yalnız ham tabloda kalır. Hiçbiri gerçek hesapla doğrulanmadı. SolarEdge V1 API 3 Kasım 2026'da kapandı; devre dışı. GoodWe, Deye/Solarman ve Sofar anahtar ve örnek çıktı gelince."},
    "modbus_sunspec": {"etiket": "Modbus TCP / SunSpec (inverter, enerji sayacı, kirlenme sensörü)", "kisa": "Modbus TCP / SunSpec", "durum": "kurulmadi", "yon": "protokol", "tur_etiketi": "saha protokolü",
                       "gerekenler": ["Saha ağına yalnızca okuma erişimi (VPN ya da ağ geçidi), IP:port ve birim kimliği", "Kayıt haritası: SunSpec model numaraları ya da üretici Modbus tablosu", "Sahip onayı ve yazma kapalı siber güvenlik politikası", "Sorgu periyodu ve sayaç/sensör listesi"],
                       "not": "SolarPower Europe O&M v6.0 kirlenme sensörü ve enerji sayacı için Modbus önerir (öneri, zorunluluk değil). Cihaz adresi girilip yalnızca okuma onayı verilince bağlantı sınanabilir; «düzenli veri çekişini başlat» ile saatlik veri alınır. Kayıt haritası: SunSpec (1xx ve 7xx modelleri otomatik keşif) ya da üretici haritası (Huawei SmartLogger santral toplamı, Sungrow dizi inverteri, Growatt). Üretici haritaları herkese açık belgeden yazıldı; gerçek cihazla doğrulanmadı."},
    "iec104": {"etiket": "IEC 60870-5-104 (SCADA / PPC)", "kisa": "IEC 60870-5-104", "durum": "kurulmadi", "yon": "protokol", "tur_etiketi": "saha protokolü",
               "gerekenler": ["TEİAŞ/EDAŞ RTU hattından AYRI, yalnızca okuma istemci bağlantısı (sahibin SCADA ya da kayıt cihazı)", "İstasyonda PVQuant için tanımlanmış ayrı istemci yuvası (ikinci istemci birincil SCADA oturumunu düşürmesin)", "ASDU adresi ve bilgi nesnesi (IOA) listesi", "İşletmeci ve sahip yazılı onayı"],
               "not": "RTU → TEİAŞ/EDAŞ hattına dokunulmaz; PVQuant yalnız ayrı bir izleme istemcisi olabilir. Adres girilip onay verilince varsayılan sınama yalnız TCP bağlantısıdır; IEC 104 STARTDT yalnız sahibin «ayrı istemci yuvası tanımlandı» onayıyla gönderilir, çünkü ikinci bir istemcinin STARTDT'si bazı istasyonlarda mevcut SCADA oturumunu düşürebilir. Komut ve veri okuma yok; veri çekişi için ASDU adresi ve bilgi nesnesi listesi gerekir."},
    "opc_ua": {"etiket": "OPC UA (SCADA sunucusu)", "kisa": "OPC UA", "durum": "kurulmadi", "yon": "protokol", "tur_etiketi": "saha protokolü",
               "gerekenler": ["OPC UA uç noktası ve yalnızca okuma kullanıcı/sertifika", "Düğüm (node) listesi: güç, enerji, ışınım, sıcaklık", "Sahip onayı"],
               "not": "Saha SCADA'sı destekliyorsa en temiz yol; yazma kapalı. OPC UA istemcisi için ayrı bir kitaplık kararı gerekir (bağımlılık eklenmedi); uç nokta ve sertifika gelince."},
}
DURUM_ETIKET = {"mevcut": "uygulamada mevcut", "kurulmadi": "bağlantı henüz kurulmadı"}
# 09.11 inceleme III (faz 2/4): her yolun GERÇEK yetenekleri — arayüz bunu okur, varsayım yapmaz.
# sinama: None | kimlik (bulut girişi + santral listesi) | okuma (Modbus FC3 + SunSpec) | ulasilabilirlik (IEC 104 STARTDT; veri okunmaz)
# dogrulama: canli (üretimde çalışıyor) | sahte (yalnız sahte cihaz/sunucuyla sınandı; gerçek hesap/cihazla doğrulanmadı) | yok
YETENEKLER: dict[str, dict] = {
    "scada_dosya": {"yapilandirma": "Veri yükleme sihirbazı (kolon eşlemesi)", "sinama": None, "veri_okuma": True, "duzenli_cekis": False, "dogrulama": "canli",
                    "ozet": "Dosya yükleyince veri gelir; sürekli bağlantı değildir."},
    "epias_seffaflik": {"yapilandirma": "Santral ayarları › EPİAŞ santral kimliği", "sinama": None, "veri_okuma": True, "duzenli_cekis": True, "dogrulama": "canli",
                        "ozet": "Her gece bir önceki günlerin üretimi çekilir (lisanslı tesis)."},
    "sayac_dosya": {"yapilandirma": "Sayaç sayfası › dosya yükleme", "sinama": None, "veri_okuma": True, "duzenli_cekis": False, "dogrulama": "canli",
                    "ozet": "Dönem dosyası yüklenince sayaç verisi gelir."},
    "inverter_bulut_api": {"yapilandirma": "Sağlayıcı seçimi; kimlik sınamada kullanılır, yalnız iki onayla şifreli saklanır", "sinama": "kimlik", "veri_okuma": True, "duzenli_cekis": True, "dogrulama": "sahte",   # v2.556/v2.557 (K1/K2)
                           "ozet": "Beş bulut için giriş ve santral listesi sınanır; kimlik kaydedilince saatlik üretim düzenli çekilir. Çekilen saatler önce ham kalır, birim doğrulanınca kaynak kıyasına yazılır. SolarEdge V1 kapandı (devre dışı)."},
    "modbus_sunspec": {"yapilandirma": "Cihaz adresi, port, birim kimliği", "sinama": "okuma", "veri_okuma": True, "duzenli_cekis": True, "dogrulama": "sahte",
                       "ozet": "Sınamada ölçüm okunur (SunSpec 1xx/7xx ya da Huawei/Sungrow/Growatt haritası); «düzenli veri çekişini başlat» ile tam saatler üretim serisine, kısmi saatler yalnız kaynak kıyasına yazılır; gerçek cihazla doğrulanmadı."},
    "iec104": {"yapilandirma": "İstasyon adresi, port", "sinama": "ulasilabilirlik", "veri_okuma": False, "duzenli_cekis": False, "dogrulama": "sahte",
               "ozet": "Varsayılan sınama yalnız TCP bağlantısı; STARTDT yalnız sahibin ayrı istemci yuvası onayıyla. Komut gönderilmez, veri okunmaz."},
    "opc_ua": {"yapilandirma": None, "sinama": None, "veri_okuma": False, "duzenli_cekis": False, "dogrulama": "yok",
               "ozet": "İstemci kitaplığı kararı bekliyor; sınama ve veri okuma yok."},
}
YETENEK_ETIKET = {"sinama": {None: "sınama yok", "kimlik": "kimlikle sınama (giriş + santral listesi)", "okuma": "yalnızca okuma sınaması (anlık ölçüm)", "ulasilabilirlik": "ulaşılabilirlik sınaması (TCP; STARTDT yalnız onayla; veri okunmaz)"},
                  "dogrulama": {"canli": "üretimde çalışıyor", "sahte": "gerçek cihaz/hesapla doğrulanmadı", "yok": "uygulanmadı"}}
# Hedef bağlantının tek durum kodu (faz 1/3): yapılandırma ≠ sınama ≠ veri akışı
BAGLANTI_DURUM_ETIKET = {"yapilandirilmadi": "bağlantı yapılandırılmadı", "dosya": "dosya kaynağı (bağlantı değil)", "mevcut": "uygulamada çalışıyor",
                         "sinanmadi": "yapılandırıldı, bağlantı sınanmadı", "sinama_ok": "bağlantı sınaması başarılı, veri çekişi yok",
                         "tcp_ok": "TCP bağlantısı açıldı; IEC 104 sınanmadı, veri çekişi yok", "cekis_acik": "düzenli veri çekişi açık, ilk veri bekleniyor",
                         "sinama_basarisiz": "bağlantı sınaması başarısız", "kimlik_hatasi": "kimlik doğrulanamadı", "desteklenmiyor": "bu sağlayıcı/protokol için bağlantı yok", "veri_akisi": "veri alınıyor"}
TAZELIK_ETIKET = {"guncel": "güncel", "gecikmis": "gecikmiş", "yok": "veri gelmedi", "dosya": "dosya yüklemesi", "dosya_eski": "yükleme 30 günden eski"}
ASAMA_ETIKET = {"secildi": "hedef seçildi", "ayar": "bağlantı ayarı girildi", "sinama": "bağlantı sınaması başarılı", "cekis": "düzenli veri çekişi açık", "akis": "veri alınıyor"}
NOT = ("Dosya kaynakları (SCADA, sayaç) geçmişe dönük çalışır: veri, yüklediğiniz güne kadar gelir; sürekli bağlantı değildir. EPİAŞ Şeffaflık bağlantısı "
       "lisanslı tesiste her gece bir önceki günlerin üretimini çeker. Modbus TCP / SunSpec için cihaz adresi girilip yalnızca okuma onayı verilince bağlantı "
       "sınanabilir; sınama cihaza erişildiğini gösterir, düzenli veri çekişi sahibin ayrıca başlattığı bir adımdır. IEC 60870-5-104 için varsayılan sınama yalnız TCP "
       "bağlantısıdır; STARTDT yalnız sahibin ayrı istemci yuvası onayıyla gönderilir (komut ve veri okuma yok). Bulut bağlantıları (FusionSolar, SolarEdge V2, SolisCloud, iSolarCloud, Growatt) anahtarla sınanır; "
       "kimlik yalnız sahibin iki onayıyla şifreli saklanır; hiçbiri gerçek hesapla henüz doğrulanmadı. SolarEdge V1 API 3 Kasım 2026'da kapandı; o bağlantı devre dışı. Diğer protokol ve bulut bağlantıları için gereken bilgiler listelenir; bağlantı, erişim bilgileri ve tesis sahibinin yalnızca okuma onayı "
       "geldikten sonra kurulur. Bu liste ne gerektiğini söyler, tarih vermez.")


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


def epias_cekis_durumu(status: str | None, detail: str | None, sonuc: dict | None = None) -> dict:
    """SAF. jobs_log'daki son gece_epias_uretim satırından çekiş durumu: hata / yeni kayıt yok / yazılmadı (SCADA öncelikli) / başarılı / ayrıntısız.
    Bağlantı hatası ile «EPİAŞ'ta yeni kayıt yok» ayrılır (brif faz 3). v2.598: yapılı `sonuc` (jobs_log.sonuc_json) varsa o okunur;
    eski satırlarda metin ayrıştırması geriye uyum için kalır."""
    if status is None:
        return {"kod": "yok", "etiket": "henüz çekiş yapılmadı"}
    if status != "ok":
        return {"kod": "hata", "etiket": "son çekiş hatayla bitti", "ayrinti": (detail or "")[:160] or None}
    if isinstance(sonuc, dict) and sonuc.get("durum"):
        durum = str(sonuc.get("durum")); yazilan = sonuc.get("n_yazilan"); yazilan = int(yazilan) if yazilan is not None else None
    else:
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
    """SAF. Hedef bağlantının aşamaları ayrı durumlarla: seçildi → ayar girildi → sınama başarılı → veri alınıyor → (bulutta) birim doğrulandı. Hiçbiri diğerini ima etmez."""
    if not beyan or not beyan.get("tur"):
        return []
    tur = beyan["tur"]; yon = VERI_YOLLARI.get(tur, {}).get("yon")
    akis = any(e.get("tur") == tur and e.get("son") for e in etkin)
    out = [{"kod": "secildi", "etiket": ASAMA_ETIKET["secildi"], "tamam": True, "zaman": beyan.get("beyan_zamani")}]
    if yon in ("protokol", "api") and VERI_YOLLARI.get(tur, {}).get("durum") == "kurulmadi":
        ss = beyan.get("son_sinama") or {}
        if tur == "inverter_bulut_api":   # v2.547: bulutta «ayar» = sağlayıcı seçimi (adres yok; kimlik saklanmaz)
            out.append({"kod": "ayar", "etiket": "sağlayıcı seçildi" if beyan.get("saglayici") else "sağlayıcı seçilmedi", "tamam": bool(beyan.get("saglayici")), "zaman": None})
        else:
            out.append({"kod": "ayar", "etiket": ASAMA_ETIKET["ayar"], "tamam": bool(beyan.get("baglanti")), "zaman": None})
        sd = ss.get("durum")
        tcp_kipi = sd == "ok" and (ss.get("ozet") or {}).get("yontem") == "tcp"   # v2.548 H2: yalnız TCP açıldı; 104 sınanmadı — «başarılı» denmez
        gi_kipi = sd == "ok" and (ss.get("ozet") or {}).get("yontem") == "gi"
        sin_etiket = ("TCP bağlantısı açıldı (STARTDT sınanmadı)" if tcp_kipi else f"genel sorgulama okundu ({(ss.get('ozet') or {}).get('eslesen', 0)} alan eşlendi)" if gi_kipi else ASAMA_ETIKET["sinama"] if sd == "ok" else "cihaza erişildi, veri modeli desteklenmiyor" if sd == "veri_modeli_yok" else
                      "cihaza erişildi, inverter modeli yok" if sd == "kismi" else "istasyona ulaşıldı, 104 onayı yok" if sd == "protokol_yaniti_yok" else
                      "kimlik doğrulanamadı" if sd == "kimlik_hatasi" else "sağlayıcı desteklenmiyor" if sd == "saglayici_desteklenmiyor" else "üretici API'si kapandı" if sd == "saglayici_kapandi" else
                      "bağlantı sınaması başarısız" if ss else "bağlantı sınanmadı")
        out.append({"kod": "sinama", "etiket": sin_etiket, "tamam": sd == "ok", "zaman": ss.get("zaman"), "durum": sd})
        if tur == "inverter_bulut_api":   # v2.556 (K1): kimlik kasası aşaması — params aynasından (gizli yok)
            bkm = beyan.get("bulut_kimlik") or {}
            out.append({"kod": "kimlik", "etiket": (("kimlik şifreli kayıtlı" + (" · çekiş açık" if bkm.get("cekis_acik") else " · çekiş kapalı")) if bkm.get("kayitli")
                                                    else "kimlik kaydedilmedi (yalnız sınama)"), "tamam": bool(bkm.get("kayitli")), "zaman": bkm.get("zaman")})
        if tur == "iec104":   # v2.554: nokta tablosu aşaması
            n = len(beyan.get("nokta_tablosu") or [])
            out.append({"kod": "nokta", "etiket": (f"nokta tablosu yüklendi ({n} IOA)" if n else "nokta tablosu yüklenmedi"), "tamam": n > 0, "zaman": None})
        if tur in ("modbus_sunspec", "iec104"):   # v2.546: çekiş sahibin ayrı kararı; sınama onu ima etmez
            out.append({"kod": "cekis", "etiket": ASAMA_ETIKET["cekis"] if beyan.get("ornekleme_acik") else "düzenli veri çekişi başlatılmadı", "tamam": bool(beyan.get("ornekleme_acik")), "zaman": None})
    out.append({"kod": "akis", "etiket": ASAMA_ETIKET["akis"] if akis else "veri alınmıyor", "tamam": akis, "zaman": None})
    bkm = (beyan.get("bulut_kimlik") or {}) if tur == "inverter_bulut_api" else {}
    if bkm.get("kayitli"):   # 10.11 inceleme II: «veri alınıyor» birimin doğrulandığını ima etmesin — ayrı, bekleyen adım
        bd = bool(bkm.get("birim_dogrulandi"))
        out.append({"kod": "birim", "etiket": "birim doğrulandı" if bd else "birim doğrulanmadı", "tamam": bd, "zaman": None})
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
        baglanti = hedef_dogrula(b.get("host"), b.get("port"), b.get("birim"), b.get("zaman_asimi_sn"), b.get("profil") if tur == "modbus_sunspec" else None,
                                   b.get("cihazlar") if tur == "modbus_sunspec" else None)   # v2.549 (D3) zaman aşımı; v2.552 (S2) kayıt haritası; v2.558 (V3) ek cihazlar
    onay = bool(d.get("salt_okuma_onayi"))
    # v2.548 (Aşama 0, H2): IEC 104 STARTDT yalnız sahibin «ayrı istemci yuvası tanımlandı» onayıyla; yalnız iec104 hedefinde ve okuma onayıyla anlamlı
    startdt = bool(d.get("startdt_onayi")) and tur == "iec104" and onay
    # v2.554 (S4): IEC 104 ayarları (CA, k/w/t, CA/IOA/COT boyları, ölçüm sınırı) ve nokta tablosu (ayrı uçtan yüklenir; burada korunur)
    iec = None
    nokta = d.get("nokta_tablosu") if tur == "iec104" and isinstance(d.get("nokta_tablosu"), list) and d.get("nokta_tablosu") else None
    if tur == "iec104":
        from pvquant.io.canli.iec104_istemci import Parametreler
        a = d.get("iec104") if isinstance(d.get("iec104"), dict) else {}
        try:
            ca = int(a.get("ca") or 1)
        except (TypeError, ValueError) as e:
            raise ValueError("ortak adres (CA) tam sayı olmalı") from e
        if not (1 <= ca <= 65534):
            raise ValueError("ortak adres (CA) 1–65534 arasında olmalı")
        prm = Parametreler.ayardan(a.get("parametreler"))
        sinir = a.get("sinir") or "plant_gross_ac"
        if sinir not in ("inverter_ac", "plant_gross_ac", "pcc_net"):
            raise ValueError("ölçüm sınırı inverter_ac | plant_gross_ac | pcc_net olmalı")
        iec = {"ca": ca, "sinir": sinir, "parametreler": {"k": prm.k, "w": prm.w, "t0": prm.t0, "t1": prm.t1, "t2": prm.t2, "t3": prm.t3, "ca_boy": prm.ca_boy, "ioa_boy": prm.ioa_boy, "cot_boy": prm.cot_boy}}
    # v2.546 (P4b-2): düzenli çekiş yalnız bağlantı ayarı ve onay varken; Modbus → her zaman, IEC 104 → STARTDT onayı + nokta tablosu ile (v2.554)
    ornekleme = bool(d.get("ornekleme_acik")) and baglanti is not None and onay and (tur == "modbus_sunspec" or (tur == "iec104" and startdt and nokta is not None))
    out = {"tur": tur, "saglayici": sag, "periyot_dk": per, "salt_okuma_onayi": onay, "not": nt,
           "baglanti": baglanti, "ornekleme_acik": ornekleme, "startdt_onayi": startdt, "beyan_zamani": datetime.now(timezone.utc).isoformat(timespec="minutes")}
    if iec:
        out["iec104"] = iec
    if nokta is not None:
        out["nokta_tablosu"] = nokta
    return {"veri_yolu": out}


def _pj(plant: dict) -> dict:
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    return pj


def _yol(tur: str) -> dict:
    v = VERI_YOLLARI[tur]; y = YETENEKLER[tur]
    return {"tur": tur, **v, "durum_etiketi": DURUM_ETIKET[v["durum"]],
            "yetenekler": {**y, "sinama_etiketi": YETENEK_ETIKET["sinama"][y["sinama"]], "dogrulama_etiketi": YETENEK_ETIKET["dogrulama"][y["dogrulama"]]}}


def baglanti_durumu(beyan: dict | None, etkin: list[dict]) -> dict:
    """SAF. Hedef bağlantının tek durum kodu. Eski veri bağlantıyı bozmaz; başarılı sınama veri akışı demek değildir."""
    if not beyan or not beyan.get("tur") or beyan["tur"] not in VERI_YOLLARI:
        return {"kod": "yapilandirilmadi", "etiket": BAGLANTI_DURUM_ETIKET["yapilandirilmadi"]}
    tur = beyan["tur"]; v = VERI_YOLLARI[tur]
    if v["yon"] == "dosya":
        return {"kod": "dosya", "etiket": BAGLANTI_DURUM_ETIKET["dosya"]}
    if v["durum"] == "mevcut":
        return {"kod": "mevcut", "etiket": BAGLANTI_DURUM_ETIKET["mevcut"]}
    if tur == "inverter_bulut_api":
        from pvquant.io.bulut import AKTIF_SAGLAYICILAR
        if (beyan.get("saglayici") or "").strip().lower() not in AKTIF_SAGLAYICILAR:   # v2.548: kapanan sağlayıcı (SolarEdge V1) da «bağlantı yok»
            return {"kod": "desteklenmiyor", "etiket": BAGLANTI_DURUM_ETIKET["desteklenmiyor"]}
    if YETENEKLER[tur]["sinama"] is None:
        return {"kod": "desteklenmiyor", "etiket": BAGLANTI_DURUM_ETIKET["desteklenmiyor"]}
    if any(e.get("tur") == tur and e.get("son") for e in etkin):
        return {"kod": "veri_akisi", "etiket": BAGLANTI_DURUM_ETIKET["veri_akisi"]}
    if beyan.get("ornekleme_acik") or (tur == "inverter_bulut_api" and (beyan.get("bulut_kimlik") or {}).get("cekis_acik")):   # v2.557: bulut çekişi de
        return {"kod": "cekis_acik", "etiket": BAGLANTI_DURUM_ETIKET["cekis_acik"]}
    # v2.554: IEC 104 veri akışı canli_ornek'e profil=iec104 ile yazılır; etkin satırı 'iec104' türüyle gelir (veri_akisi yukarıda yakalanır)
    ss = beyan.get("son_sinama") or {}
    if ss.get("durum") == "ok" and (ss.get("ozet") or {}).get("yontem") == "tcp":   # v2.548 H2
        return {"kod": "tcp_ok", "etiket": BAGLANTI_DURUM_ETIKET["tcp_ok"]}
    if ss.get("durum") == "ok":
        return {"kod": "sinama_ok", "etiket": BAGLANTI_DURUM_ETIKET["sinama_ok"]}
    if ss.get("durum") == "kimlik_hatasi":
        return {"kod": "kimlik_hatasi", "etiket": BAGLANTI_DURUM_ETIKET["kimlik_hatasi"]}
    if ss:
        return {"kod": "sinama_basarisiz", "etiket": BAGLANTI_DURUM_ETIKET["sinama_basarisiz"]}
    return {"kod": "sinanmadi", "etiket": BAGLANTI_DURUM_ETIKET["sinanmadi"]}


def veri_kodu(t: dict, son_olcum=None, yon: str = "api") -> str:
    """SAF. Veri durumu kodu (bağlantıdan bağımsız): guncel | gecikmis | dosya | dosya_eski | yuklenmedi | olcum_bilinmiyor."""
    kod = t.get("tazelik")
    if kod == "yok":
        return "yuklenmedi" if yon == "dosya" else "gelmedi"
    if kod in ("guncel", "gecikmis") and son_olcum is None and yon != "dosya":
        return "olcum_bilinmiyor"
    return kod or "gelmedi"


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
                f"FROM scada_hourly sh JOIN ingestion_batches b ON b.id = sh.batch_id WHERE sh.plant_id=:p AND {_ks.sql_kosulu('tazelik', 'sh')} GROUP BY 1"), {"p": plant["id"]}).mappings().all()
            son_olcum = {r["k"]: r["son"] for r in olc}
        except Exception:   # noqa: BLE001
            son_olcum = {}
    cekis = None
    if pj.get("epias_santral_id"):
        try:
            from pvquant.db import sistem_baglami
            with sistem_baglami() as s2:
                j = s2.execute(text("SELECT started, status, detail, sonuc_json FROM jobs_log WHERE job=:j AND plant_id=CAST(:p AS uuid) ORDER BY started DESC LIMIT 1"),
                               {"j": EPIAS_IS_ADI, "p": plant["id"]}).mappings().first()
            cekis = {**epias_cekis_durumu(j["status"] if j else None, j["detail"] if j else None, j["sonuc_json"] if j else None),
                     "zaman": (j["started"].isoformat() if j and j["started"] else None)}
        except Exception as e:   # noqa: BLE001 — iş günlüğü okunamazsa durum bilinmez, uydurulmaz
            cekis = {"kod": "bilinmiyor", "etiket": f"çekiş durumu okunamadı ({type(e).__name__})", "zaman": None}
    sik = pj.get("dosya_yukleme_sikligi_gun")   # v2.546: müşterinin beyan ettiği yükleme sıklığı (gün); eşik iki katı
    if dosya:
        so = son_olcum.get("dosya")
        tzd = tazelik(dosya["created_at"], simdi, "dosya", dosya_eski_gun=sik)
        out.append({"tur": "scada_dosya", "etiket": VERI_YOLLARI["scada_dosya"]["kisa"], "tur_etiketi": "dosya kaynağı", "tanimli": True,
                    "son": dosya["created_at"].isoformat() if dosya["created_at"] else None, "son_olcum": so.isoformat() if so else None,
                    "ayrinti": f"son dosya {dosya['filename']}" + (f" · beyan edilen yükleme sıklığı {int(sik)} gün" if sik else ""),
                    "veri_kodu": veri_kodu(tzd, so, "dosya"), "veri_etiketi": "geçmişe dönük dosya · " + veri_etiketi(tzd), **tzd})
    # v2.546 (P4b-2): Modbus TCP / SunSpec düzenli örnekleme etkinse canlı protokol satırı — eşik 3 × periyot (en az 1 saat)
    vyb = pj.get("veri_yolu") if isinstance(pj.get("veri_yolu"), dict) else None
    edge_var = False   # v2.561 (E1): saha toplayıcısı örnek gönderiyorsa düzenli çekiş açık olmasa da canlı satır
    if vyb and vyb.get("tur") == "modbus_sunspec" and not vyb.get("ornekleme_acik"):
        try:
            from pvquant.services import edge_service
            edge_var = any(x["durum"] == "etkin" and x.get("son_gorulme") for x in edge_service.toplayici_listele(tenant_id, plant["id"]))
        except Exception:   # noqa: BLE001
            edge_var = False
    if vyb and vyb.get("tur") in ("modbus_sunspec", "iec104") and (vyb.get("ornekleme_acik") or edge_var):   # v2.554: IEC 104 düzenli çekişi de canlı protokol satırı
        from pvquant.services import canli_ornekleme_service as co
        d = co.durum(tenant_id, plant)
        if d is not None:
            per = co.periyot_dk(vyb); esik = max(3 * per, 60) / 60.0
            tz = tazelik(d["son_ornek"], simdi, "protokol", esik_saat=esik)
            bag = ({"durum": "yok", "etiket": "henüz örnek alınmadı", "zaman": None} if not d["son_ornek"] else
                   {"durum": "ok", "etiket": "son örnek alındı", "zaman": d["son_ornek"].isoformat()} if tz["tazelik"] == "guncel" else
                   {"durum": "hata", "etiket": "örnek alınamıyor", "zaman": d["son_ornek"].isoformat()})
            out.append({"tur": vyb["tur"], "etiket": VERI_YOLLARI[vyb["tur"]]["kisa"], "tur_etiketi": "saha protokolü", "tanimli": True,
                        "son": d["son_ornek"].isoformat() if d["son_ornek"] else None, "son_olcum": d["son_saat"].isoformat() if d["son_saat"] else None,
                        "baglanti": bag, "veri_kodu": veri_kodu(tz, d["son_saat"], "protokol"), "veri_etiketi": (f"son saat {d['son_saat'].isoformat()}" if d["son_saat"] else "henüz saatlik veri yazılmadı"),
                        "ayrinti": (("saha toplayıcısı · " if edge_var else f"örnekleme {per} dk · ") + f"son 24 saatte {d['n24']} örnek") + (f" · {d['n_cihaz']} cihaz" if d.get("n_cihaz") else "")
                                   + (f" · {d['n_kismi_24']} kısmi saat (üretim serisine yazılmadı)" if d.get("n_kismi_24") else ""), **tz})   # v2.550 (D4/D5)
    if vyb and vyb.get("tur") == "inverter_bulut_api" and (vyb.get("bulut_kimlik") or {}).get("kayitli"):   # v2.557 (K2): bulut çekişi satırı
        from pvquant.services import bulut_cekis_service as bc
        from pvquant.services import bulut_kimlik_service as bk
        kay = next(iter(bk.listele(tenant_id, plant["id"])), None)
        if kay:
            ham = bc.ham_son(tenant_id, plant["id"], kay["saglayici"], 1)
            son_alinma = datetime.fromisoformat(ham[0]["alinma"]) if ham else None
            son_ts = datetime.fromisoformat(ham[0]["ts_utc"]) if ham else None
            tz = tazelik(son_alinma, simdi, "api")
            bag = ({"durum": "yok", "etiket": "düzenli çekiş açılmadı", "zaman": None} if not kay.get("cekis_acik") else
                   {"durum": "ok", "etiket": "son çekiş başarılı", "zaman": kay.get("son_cekis")} if kay.get("son_durum") == "ok" else
                   {"durum": "hata", "etiket": kay.get("son_durum_etiketi") or "çekiş hatası", "zaman": kay.get("son_cekis")} if kay.get("son_durum") else
                   {"durum": "yok", "etiket": "çekiş açık, ilk tur bekleniyor", "zaman": None})
            out.append({"tur": "inverter_bulut_api", "etiket": VERI_YOLLARI["inverter_bulut_api"]["kisa"], "tur_etiketi": "bulut bağlantısı", "tanimli": True,
                        "son": son_alinma.isoformat() if son_alinma else None, "son_olcum": son_ts.isoformat() if son_ts else None, "baglanti": bag,
                        "veri_kodu": veri_kodu(tz, son_ts, "api"),
                        "veri_etiketi": (("ham saatler · birim doğrulandı, kaynak kıyasına yazılıyor" if kay.get("birim_dogrulandi") else
                                          "ham saatler (birim doğrulanmadı; kaynak kıyasına yazılmıyor)") if ham else "henüz saatlik veri çekilmedi"),
                        "saglayici": kay["saglayici"], "birim_dogrulandi": bool(kay.get("birim_dogrulandi")), "son_cekis_ok": bool(ham) and kay.get("son_durum") == "ok",   # 10.11 inceleme II: rozet rengi ve hesap durumu buradan
                        "ayrinti": f"{kay.get('saglayici_adi')} · hesap {kay.get('etiket')} · bugün {kay.get('kota_sayac') or 0}/{bc.GUNLUK_TAVAN} çağrı", **tz})
    if pj.get("epias_santral_id"):
        son = epias["created_at"] if epias else None; so = son_olcum.get("epias")
        tz = tazelik(son, simdi, "api")
        ve = veri_etiketi(tz)
        if cekis and cekis.get("kod") == "kayit_yok" and tz["tazelik"] == "gecikmis":
            ve += " · kaynakta yeni kayıt yok"   # yalnız servis yanıtı «veri_yok» dediğinde (jobs_log ayrıntısı)
        out.append({"tur": "epias_seffaflik", "etiket": VERI_YOLLARI["epias_seffaflik"]["kisa"], "tur_etiketi": "platform bağlantısı", "tanimli": True,
                    "son": son.isoformat() if son else None, "son_olcum": so.isoformat() if so else None, "cekis": cekis, "veri_kodu": veri_kodu(tz, so, "api"),
                    "baglanti": epias_baglanti(cekis), "veri_etiketi": ve,
                    "ayrinti": f"santral kimliği {pj['epias_santral_id']}" + ("" if epias else " — bağlantı tanımlı, henüz veri çekilmedi"), **tz})
    for x in sy:
        tzs = tazelik(x["son"], simdi, "dosya", dosya_eski_gun=sik)
        out.append({"tur": "sayac_dosya", "etiket": VERI_YOLLARI["sayac_dosya"]["kisa"], "tur_etiketi": "dosya kaynağı", "tanimli": True,
                    "son": x["son"].isoformat() if x["son"] else None, "son_olcum": None, "ayrinti": f"kaynak {x['kaynak']}",
                    "veri_kodu": veri_kodu(tzs, None, "dosya"), "veri_etiketi": "geçmişe dönük dosya · " + veri_etiketi(tzs), **tzs})
    return out


def hesap_durumu(etkin: list[dict]) -> dict | None:
    """SAF. 10.11 inceleme II: bu santralın bulut hesabında son çekiş başarılıysa tür düzeyindeki «gerçek hesapla doğrulanmadı» cümlesi yerine
    hesabın kendi durumu gösterilir. Birim ayrı adımdır; çekiş başarısı birimi doğrulamaz. Çekiş yoksa ya da son tur başarısızsa None (genel etiket kalır)."""
    e = next((x for x in etkin if x.get("tur") == "inverter_bulut_api" and x.get("son_cekis_ok")), None)
    if not e:
        return None
    bd = bool(e.get("birim_dogrulandi"))
    return {"saglayici": e.get("saglayici"), "birim_dogrulandi": bd,
            "etiket": "bu hesapta çekiş başarılı; birim doğrulandı" if bd else "bu hesapta çekiş başarılı; birim doğrulaması bekliyor"}


def ozet(tenant_id, plant: dict, simdi: datetime | None = None) -> dict:
    pj = _pj(plant)
    beyan = pj.get("veri_yolu") if isinstance(pj.get("veri_yolu"), dict) else None
    hedef = _yol(beyan["tur"]) if beyan and beyan.get("tur") in VERI_YOLLARI else None
    etkin = etkin_yollar(tenant_id, plant, simdi)
    sik = pj.get("dosya_yukleme_sikligi_gun")
    from pvquant.io.bulut import HENUZ_YOK, SAGLAYICILAR
    from pvquant.io.bulut.fusionsolar import BOLGELER
    # faz 2: sağlayıcı matrisi — «uygulandı, doğrulanmadı» / «planlandı» / «desteklenmiyor»; hiçbiri «üretime hazır» demez
    bulut = {"saglayicilar": [{"kod": k, "ad": v["ad"], "kimlik_alanlari": v["kimlik_alanlari"], "kimlik_etiketleri": v.get("kimlik_etiketleri") or {}, "gizli_alanlar": v.get("gizli_alanlar") or [],
                               "bolge": v["bolge"], "bolgeler": v.get("bolgeler") or [], "varsayilan_bolge": v.get("varsayilan_bolge"), "not": v["not"],
                               "durum": v["durum"], "durum_etiketi": v["durum_etiketi"], "oauth": bool(v.get("oauth")), "elle_giris": v.get("elle_giris", True)} for k, v in SAGLAYICILAR.items()],   # v2.564: sahip onayı yolu   # v2.548: durum sicilden (kapandi dâhil); v2.562: alan etiketleri, bölgeler
             "bolgeler": list(BOLGELER), "henuz_yok": HENUZ_YOK, "henuz_yok_etiketi": "Planlandı (anahtar ve örnek çıktı gelince)",
             "kasa": __import__("pvquant.guvenlik.kasa", fromlist=["kek_durum"]).kek_durum(),   # v2.556 (K1): şifreli saklama bu kurulumda açık mı (anahtar dönmez)
             "hesap_durumu": hesap_durumu(etkin),
             "diger_etiketi": "desteklenmiyor — kaydederseniz talep olarak not edilir", "not": "Anahtar sınamada kullanılır; yalnız sahibin iki onayıyla şifreli saklanır ve düzenli çekişte çözülür."}
    from pvquant.io.canli.profiller import liste as profil_listesi
    return {"etkin": etkin, "beyan": beyan, "hedef": hedef, "asamalar": asamalar(beyan, etkin), "baglanti_durumu": baglanti_durumu(beyan, etkin), "profiller": profil_listesi(),
            "yollar": [_yol(k) for k in VERI_YOLLARI], "bulut": bulut,
            "taze_saat": TAZE_SAAT, "dosya_eski_gun": (2 * int(sik) if sik else DOSYA_ESKI_GUN), "dosya_yukleme_sikligi_gun": sik, "not": NOT}
