"""v2.270 — Dalga 0: veri kaynakları ve lisans künyesi (Gizlilik Anayasası v2.245 istisnası).

Atıf yalnız üç yerde görünür: panel "Hakkında › Veri kaynakları ve lisanslar", rapor künye sayfası, README.
Liste GERÇEK kullanımı yansıtır: meteo ayarı, arşivde görülen kaynaklar, kalibrasyonların kaydettiği geçmiş
kaynağı, piyasa fiyatının kaynağı. Kullanılmayan kaynağa atıf yapılmaz; ticari kullanıma kapalı kaynak varsa uyarı.
"""
from __future__ import annotations

from pvquant.config import get_settings
from pvquant.ext.kaynak import atif

# Panel için okunur açıklama (ext not_ alanı README/teknik künye içindir; UI'da parametre adı geçmez)
ACIKLAMA = {
    "ecmwf": "Küresel sayısal hava tahmini; 0,25° ızgara, 15 gün ufuk, günde 2 koşu.",
    "icon": "Avrupa bölgesel modeli; ~7 km ızgara, 5 gün ufuk, günde 8 koşu; Türkiye alan içinde.",
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



# v2.295 — Tablo 3.4 "yasal metin kütüphanesi": madde referansları tek yerde, panelde görünür.
# Katsayılar burada YAZILMAZ (sabitlenmesin) — kod parametriktir, burası yalnız dayanağı gösterir.
MEVZUAT = [
    {"ad": "DUY — Dengeleme ve Uzlaştırma Yönetmeliği", "kapsam": "KGÜP bildirimi (md. 69, 69/A) · dengesizlik fiyatlandırması (md. 110–111)",
     "not": "Pozitif/negatif dengesizlik katsayıları parametredir; santral ayarından değiştirilebilir."},
    {"ad": "DUY geçici md. 40", "kapsam": "15 dakikalık uzlaştırma dönemi",
     "not": "Altyapı en geç 1 Ocak 2027; 15 dakikalık program çıktısı üründe hazırdır."},
    {"ad": "KÜPST — Kurul kararı", "kapsam": "KGÜP bildirmekle yükümlü birimlerde ayrı sapma kalemi",
     "not": "Katsayı ve tolerans santral ayarından değiştirilebilir; yalnız yükümlü segmentlerde işler."},
    {"ad": "LÜY — Lisanssız Üretim Yönetmeliği", "kapsam": "Dağıtım bağlı lisanssız üretici",
     "not": "Dengesizlik sorumluluğu görevli tedarik şirketi ya da toplayıcı portföyündedir; segment seçimi bu kuralları uygular."},
    {"ad": "Piyasa takvimi", "kapsam": "Günlük program akışı",
     "not": "Program bildirimi 14:00–15:30 · sistem işletmecisi teyidi 17:00 · gün içi revizyon kapı kapanışı + 30 dk."},
    {"ad": "IEC 61724-1 · IEC 61853 · ISO 15927-4 · ASTM E2848", "kapsam": "PR, güç matrisi, tipik yıl, kapasite testi",
     "not": "Sağlık ve rapor hesapları bu standartların tanımlarını izler."},
    {"ad": "Solar Forecast Arbiter metrik sözlüğü", "kapsam": "Karne metrikleri (nMAE, nRMSE, beceri, bant sınavı)",
     "not": "Doğruluk sayfasındaki tüm ölçüler bu ortak sözlükle hesaplanır — kıyas elma-elma olsun diye."},
]

def hakkinda() -> dict:
    from pvquant.io import acik_nwp
    kull = kullanilan_kaynaklar()
    try:
        arsiv = acik_nwp.arsiv_durumu()
    except Exception:   # noqa: BLE001
        arsiv = {}
    return {
        "urun": "PVQuant", "meteo_kaynak": get_settings().meteo_kaynak,
        "kaynaklar": [{"kimlik": k, "ad": atif.KAYNAKLAR[k].ad, "kurum": atif.KAYNAKLAR[k].kurum, "lisans": atif.KAYNAKLAR[k].lisans,
                       "lisans_url": atif.KAYNAKLAR[k].lisans_url, "veri_url": atif.KAYNAKLAR[k].veri_url,
                       "not": ACIKLAMA.get(k, atif.KAYNAKLAR[k].not_)}
                      for k in kull],
        "kunye": atif.kunye(kull), "uyarilar": atif.uyumluluk_denetimi(kull),
        "arsiv": {ARSIV_ETIKET.get(k, k): v for k, v in arsiv.items()},
        "mevzuat": MEVZUAT,
        "yontem": "Veriler PVQuant tarafından indirilmiş, birleştirilmiş ve işlenmiştir; kaynak kurumlar bu ürünü desteklemez ve sonuçlardan sorumlu değildir.",
    }


def rapor_kunye_satiri() -> str:
    """Rapor künye sayfası için tek satır (PDF/HTML): kaynak adları + lisans."""
    kull = [k for k in kullanilan_kaynaklar() if k != "epias"]
    return "Hava verisi: " + " · ".join(f"{atif.KAYNAKLAR[k].ad} ({atif.KAYNAKLAR[k].lisans})" for k in kull) + \
        " · Gerçekleşme: santral SCADA'sı · Fizik modeli: pvlib. Veriler PVQuant tarafından işlenmiştir; kaynaklar bu ürünü desteklemez."
