"""v2.270 — Dalga 0: veri kaynakları ve lisans künyesi (Gizlilik Anayasası v2.245 istisnası).

Atıf yalnız üç yerde görünür: panel "Hakkında › Veri kaynakları ve lisanslar", rapor künye sayfası, README.
Liste GERÇEK kullanımı yansıtır: meteo ayarı, arşivde görülen kaynaklar, kalibrasyonların kaydettiği geçmiş
kaynağı, piyasa fiyatının kaynağı. Kullanılmayan kaynağa atıf yapılmaz; ticari kullanıma kapalı kaynak varsa uyarı.
"""
from __future__ import annotations

from pvquant.config import get_settings
from pvquant.ext.kaynak import atif
from pvquant.ext.turkiye import kunye as _kunye   # v2.535: mevzuat listesi künyeli

# Panel için okunur açıklama (ext not_ alanı README/teknik künye içindir; UI'da parametre adı geçmez)
ACIKLAMA = {
    "ecmwf": "Küresel sayısal hava tahmini; 0,25° ızgara, 15 gün ufuk, günde 2 güncelleme.",
    "icon": "Avrupa bölgesel modeli; ~7 km ızgara, 5 gün ufuk, günde 8 güncelleme; Türkiye alan içinde.",
    "gfs": "Küresel model (NOAA); 0,25° ızgara, 16 gün ufuk.",
    "cams": "Uydu türevli ışınım serisi; ~2 gün gecikme — kalibrasyon geçmişi.",
    "pvgis": "Uydu türevli ışınım arşivi 2005–2023 — iklim zarfı ve kalibrasyon geçmişi.",
    "era5": "Yeniden analiz arşivi; 0,25°, saatlik.",
    "nasa_power": "Kaba (1°) ışınım arşivi; yalnız eski dönem ve kıyas.",
    "epias": "Piyasa fiyatları (PTF/SMF) — dengesizlik hesabı.",
    "open_meteo": "Ücretsiz katman; ticari kullanıma kapalı.",
}
ARSIV_ETIKET = {"acik-nwp": "Açık NWP harmanı (ECMWF IFS + ICON-EU + GFS)", "gefs": "GEFS üyeleri (31)"}

ESLEME = {"acik-nwp": ["ecmwf", "icon"], "cams": ["cams"], "pvgis-sarah3": ["pvgis"], "nasa-power": ["nasa_power"],
          "open-meteo": ["open_meteo"], "epias": ["epias"]}


def kullanilan_kaynaklar() -> list[str]:
    cfg = get_settings()
    k: list[str] = ["ecmwf", "icon", "gfs", "pvgis"] if cfg.meteo_kaynak == "acik" else ["open_meteo"]
    try:
        from sqlalchemy import text
        from pvquant.db import sistem_baglami
        with sistem_baglami() as s:
            for (ad,) in s.execute(text("SELECT DISTINCT kaynak FROM meteo_arsiv")):
                k += ESLEME.get(ad, [])
            for (q,) in s.execute(text("SELECT DISTINCT quality_json->>'meteo_kaynak' FROM calibrations WHERE quality_json ? 'meteo_kaynak'")):
                k += ESLEME.get(q, [])
            if s.execute(text("SELECT 1 FROM piyasa_fiyat WHERE kaynak='epias' LIMIT 1")).first() or \
               s.execute(text("SELECT 1 FROM ingestion_batches WHERE filename='epias_realtime' LIMIT 1")).first():
                k.append("epias")
    except Exception:   # noqa: BLE001 — DB yoksa (test/örnek kip) ayar listesi yeter
        pass
    sira = list(atif.KAYNAKLAR)
    return sorted(set(k), key=sira.index)



# v2.295 — Tablo 3.4 "yasal metin kütüphanesi": madde referansları tek yerde, panelde görünür. v2.535: her satırda birincil künye (kunye.py sicili;
# 03.11.2026 doğrulama arşivi 03_Kaynak_Envanteri ile eş) — Hakkında sayfası arşivle aynı kaynakları anar.
# Katsayılar burada YAZILMAZ (sabitlenmesin) — kod parametriktir, burası yalnız dayanağı gösterir.
MEVZUAT = [
    {"ad": "DUY — Dengeleme ve Uzlaştırma Yönetmeliği", "kapsam": "KGÜP bildirimi (m.69, 69/A) · dengesizlik fiyatlandırması (m.110–111) · uzlaştırma ve fatura takvimi (m.132–133)",
     "kunye": _kunye.kunye("DUY"), "not": "Pozitif/negatif dengesizlik katsayıları (k/l), V ve fiyat sınırları kural tablosundan (kural motoru) gelir; santral ayarından değişmez."},
    {"ad": "DUY geçici m.40", "kapsam": "15 dakikalık uzlaştırma dönemi", "kunye": "RG 21.01.2025-32789 Md.19; 15 dakikalık DGP en erken 1.1.2027 (RG 19.10.2026-33405 Geçici m.40)",
     "not": "Altyapı en geç 1.1.2027'ye kadar tamamlanır; uygulama 1.1.2027'den önce başlatılmaz; fiilî başlangıç duyurulmadı. 15 dakikalık çıktı saatlik tahminin profille bölünmesidir."},
    {"ad": "KÜPST — Kurul kararları", "kapsam": "KGÜP bildirmekle yükümlü birimlerde ayrı sapma kalemi",
     "kunye": _kunye.kunye("KARAR_13025") + " · " + _kunye.kunye("KARAR_14029") + " · " + _kunye.kunye("KARAR_14907"),
     "not": "Katsayı (n) ve tolerans santral ayarından geçersiz kılınabilir (Doğruluk'ta etiketlenir); yalnız yükümlü segmentlerde işler."},
    {"ad": "Dengesizlik katsayıları ve fiyat sınırları — Kurul kararları", "kapsam": "k/l (yöne bağlı), V tabanı, azami fiyat limiti, DSG üye oranı",
     "kunye": _kunye.kunye("KARAR_14030") + " · " + _kunye.kunye("KARAR_14911") + " · " + _kunye.kunye("KARAR_13869") + " · " + _kunye.kunye("AFL_UE"),
     "not": "Değerler kural tablosunda tarihe göre seçilir (Hakkında › Kural tablosu)."},
    {"ad": "LÜY — Lisanssız Üretim Yönetmeliği", "kapsam": "Dağıtım bağlı lisanssız üretici", "kunye": _kunye.kunye("LUY"),
     "not": "Dengesizlik sorumluluğu görevli tedarik şirketi ya da toplayıcı portföyündedir; segment seçimi bu kuralları uygular."},
    {"ad": "YEKDEM — 5346 sayılı Kanun, YEK Yönetmeliği, Cumhurbaşkanı kararları", "kapsam": "Fiyat rejimi (Cetvel I / 7189), destek süreleri, m.23(6)",
     "kunye": _kunye.kunye("5346") + " · " + _kunye.kunye("YEK_YON") + " · " + _kunye.kunye("CK7189") + " · " + _kunye.kunye("CK2949") + " · " + _kunye.kunye("KARAR_5905"),
     "not": "YEK fiyatı Cetvel I'de günün TCMB kuruyla, 7189'da aylık EPİAŞ ilanıyla; süreler takvimde."},
    {"ad": "Lisans Yönetmeliği ve 6446 sayılı Kanun", "kapsam": "Lisans bedeli taksitleri, ilerleme raporu, bildirim yükümlülükleri, idari yaptırım",
     "kunye": _kunye.kunye("LISANS") + " · " + _kunye.kunye("6446"), "not": "Takvim sayfasındaki uyum adımları; yaptırım tutarı yazılmaz (yıllık tebliğ)."},
    {"ad": "Ölçüm Sistemleri Yönetmeliği ve sayaç usul-esasları", "kapsam": "Sayaç verisinin geliş süresi, OSOS/MASS kaynakları",
     "kunye": _kunye.kunye("OLCUM") + " · " + _kunye.kunye("OSOS_UE") + " · " + _kunye.kunye("KARAR_13995"), "not": "Sayaç sayfasındaki geliş beklentisi ve eksik sayaç alarmı."},
    {"ad": "Teminat Usul ve Esasları", "kapsam": "Dengesizlik teminatı göstergesi", "kunye": _kunye.kunye("TUE"),
     "not": "Risk katsayısının güncel değeri kamuya açık kaynakta yok; Santral ayarlarından girilir."},
    {"ad": "Şeffaflık Platformu veri listesi", "kapsam": "Piyasa fiyatı ve gerçekleşen üretim akışı", "kunye": _kunye.kunye("KARAR_14968") + " · " + _kunye.kunye("SEFFAFLIK"),
     "not": "1.1.2027'den yeni veri listesi; bugünkü akış Karar 10711 kalemleriyle."},
    {"ad": "Piyasa takvimi", "kapsam": "Günlük program akışı", "kunye": "DUY m.69(1), (4) · " + _kunye.kunye("GIP_KAPI") + " · " + _kunye.kunye("TPYS"),
     "not": "Program bildirimi 14:00–15:30 · sistem işletmecisi teyidi 17:00 · gün içi revizyon kapı kapanışı + 30 dk."},
    {"ad": "Resmî tatil ve saat dilimi", "kapsam": "İş günü sayımı, saat etiketleri", "kunye": _kunye.kunye("2429") + " · " + _kunye.kunye("YAZ_SAATI"),
     "not": "Dinî bayramlar Diyanet takvimine göre; Türkiye yıl boyu UTC+3."},
    {"ad": "IEC 61724-1 · IEC 61853 · ISO 15927-4 · ASTM E2848", "kapsam": "PR, güç matrisi, tipik yıl, kapasite testi", "kunye": "uluslararası standartlar (sürüm: IEC 61724-1:2021, IEC 61853-1:2011, ISO 15927-4:2005, ASTM E2848-13)",
     "not": "Sağlık ve rapor hesapları bu standartların tanımlarını izler."},
    {"ad": "Solar Forecast Arbiter metrik sözlüğü", "kapsam": "Karne metrikleri (nMAE, nRMSE, beceri, bant sınavı)", "kunye": "solarforecastarbiter.org — açık metrik tanımları",
     "not": "Doğruluk sayfasındaki tüm ölçüler bu ortak sözlükle hesaplanır — kıyas elma-elma olsun diye."},
]

# v2.535: Hakkında «Meteoroloji arşivi» kartında gösterilen iş — gece_meteo = NWP indirme/arşivleme (tahminden 1 saat önce,
# apps/worker/main.py; GEFS üyeleri de aynı işin içinde). Arşivdeki «son koşu» model başlangıç saatidir (meteo_arsiv.kosu_zamani);
# indirmenin ne zaman denendiği ve başarılı olup olmadığı yalnız jobs_log'dan okunur — ikisi ekranda ayrı gösterilir.
IZLENEN_ARSIV_ISLERI = {"gece_meteo": "Gece hava tahmini indirme ve arşivleme"}


def is_tazeligi(isler: dict[str, str] | None = None) -> dict:
    """{job: {ad, son_basarili, son_deneme, son_durum, son_ayrinti}} — jobs_log'dan (tenant'sız küresel satırlar). Hiçbir değer uydurulmaz:
    kayıt yoksa alanlar None kalır."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    isler = isler or IZLENEN_ARSIV_ISLERI
    out = {j: {"ad": ad, "son_basarili": None, "son_deneme": None, "son_durum": None, "son_ayrinti": None} for j, ad in isler.items()}
    with sistem_baglami() as s:
        for r in s.execute(text("SELECT job, max(started) AS son FROM jobs_log WHERE status = 'ok' AND job = ANY(:g) GROUP BY job"),
                           {"g": list(isler)}).mappings():
            out[r["job"]]["son_basarili"] = r["son"].isoformat() if r["son"] is not None else None
        for r in s.execute(text("SELECT DISTINCT ON (job) job, started, status, detail FROM jobs_log WHERE job = ANY(:g) "
                                "ORDER BY job, started DESC"), {"g": list(isler)}).mappings():
            out[r["job"]].update(son_deneme=r["started"].isoformat() if r["started"] is not None else None,
                                 son_durum=r["status"], son_ayrinti=(r["detail"] or "")[:200] or None)
    return out


def hakkinda() -> dict:
    from pvquant.io import acik_nwp
    kull = kullanilan_kaynaklar()
    try:
        arsiv = acik_nwp.arsiv_durumu()
    except Exception:   # noqa: BLE001
        arsiv = {}
    try:
        isler = is_tazeligi()
    except Exception:   # noqa: BLE001
        isler = {}
    return {
        "urun": "PVQuant", "meteo_kaynak": get_settings().meteo_kaynak,
        "kaynaklar": [{"kimlik": k, "ad": atif.KAYNAKLAR[k].ad, "kurum": atif.KAYNAKLAR[k].kurum, "lisans": atif.KAYNAKLAR[k].lisans,
                       "lisans_url": atif.KAYNAKLAR[k].lisans_url, "veri_url": atif.KAYNAKLAR[k].veri_url,
                       "not": ACIKLAMA.get(k, atif.KAYNAKLAR[k].not_),
                       # v2.535: lisans sayfasının son doğrulama tarihi ve notu (yalnız gerçekten okunan sayfalar; yoksa None)
                       "lisans_dogrulama": (atif.LISANS_DOGRULAMA[k][0] if k in atif.LISANS_DOGRULAMA else None),
                       "lisans_notu": (atif.LISANS_DOGRULAMA[k][1] if k in atif.LISANS_DOGRULAMA else None)}
                      for k in kull],
        "kunye": atif.kunye(kull), "uyarilar": atif.uyumluluk_denetimi(kull),
        "arsiv": {ARSIV_ETIKET.get(k, k): v for k, v in arsiv.items()},
        "isler": isler,   # v2.535: indirme işinin son başarılı koşusu / son denemesi (arşivdeki model koşu saatinden ayrı)
        "mevzuat": MEVZUAT,
        "yontem": "Veriler PVQuant tarafından indirilmiş, birleştirilmiş ve işlenmiştir; kaynak kurumlar bu ürünü desteklemez ve sonuçlardan sorumlu değildir.",
    }


def rapor_kunye_satiri() -> str:
    """Rapor künye sayfası için tek satır (PDF/HTML): kaynak adları + lisans."""
    kull = [k for k in kullanilan_kaynaklar() if k != "epias"]
    return "Hava verisi: " + " · ".join(f"{atif.KAYNAKLAR[k].ad} ({atif.KAYNAKLAR[k].lisans})" for k in kull) + \
        " · Gerçekleşme: santral SCADA'sı · Fizik modeli: pvlib. Veriler PVQuant tarafından işlenmiştir; kaynaklar bu ürünü desteklemez."
