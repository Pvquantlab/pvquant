"""Kaynak atfı — Gizlilik Anayasası istisnası (v2.245) uyarınca künye üretimi.

Atıf yalnız üç yerde görünür: panel "Hakkında › Veri kaynakları ve lisanslar",
rapor künye sayfası, README. Bu modül o metni tek biçimde üretir; kaynak
listesi GERÇEK kullanımı yansıtmalıdır (kullanılmayan kaynağa atıf yapılmaz).
"""
from __future__ import annotations

from .ortak import KaynakBilgisi

KAYNAKLAR: dict[str, KaynakBilgisi] = {
    "ecmwf": KaynakBilgisi("ECMWF Open Data (IFS / AIFS)", "ECMWF", "CC BY 4.0",
        "https://creativecommons.org/licenses/by/4.0/", "https://www.ecmwf.int/en/forecasts/datasets/open-data", True,
        "0.25°, 15 gün; ssrd/2t/10u/10v/tcc; ENS 50+1 üye; yalnız son ~2–3 gün koşu tutulur"),
    "icon": KaynakBilgisi("ICON-EU (DWD Open Data)", "Deutscher Wetterdienst", "CC BY 4.0",
        "https://www.dwd.de/EN/service/legal_notice/legal_notice.html", "https://opendata.dwd.de/weather/nwp/", True,
        "0.0625° (~7 km), +120 s, 8 koşu/gün; aswdir_s/aswdifd_s; alan 23,5°B–45°D, Türkiye içinde"),
    "gfs": KaynakBilgisi("GFS / GEFS (NOAA NCEP)", "NOAA / NWS", "Kamu malı (public domain)",
        "https://www.weather.gov/disclaimer", "https://nomads.ncep.noaa.gov/", True,
        "0.25°, 16 gün; DSWRF/TMP/UGRD/VGRD/TCDC; GEFS 30+1 üye"),
    "cams": KaynakBilgisi("CAMS Solar Radiation Time-Series", "Copernicus / ECMWF", "CC BY 4.0",
        "https://ads.atmosphere.copernicus.eu/", "https://ads.atmosphere.copernicus.eu/datasets/cams-solar-radiation-timeseries", True,
        "2004→, 1 dk–1 saat; GHI/BHI/DHI/BNI + açık gök; Meteosat alanı (Türkiye dâhil); ~2 gün gecikme"),
    "pvgis": KaynakBilgisi("PVGIS v5.3 (SARAH-3, ERA5)", "Avrupa Komisyonu JRC", "CC BY 4.0",
        "https://commission.europa.eu/legal-notice_en", "https://re.jrc.ec.europa.eu/pvg_tools/en/", True,
        "SARAH-3 2005–2023 saatlik; TMY; 30 çağrı/sn/IP"),
    "era5": KaynakBilgisi("ERA5 (Copernicus CDS)", "Copernicus / ECMWF", "CC BY 4.0 (Copernicus lisansı)",
        "https://cds.climate.copernicus.eu/", "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels", True,
        "1940→, 0.25°, saatlik; ssrd/t2m/u10/v10/tcc; ~5 gün gecikme"),
    "nasa_power": KaynakBilgisi("NASA POWER", "NASA LaRC", "Açık (NASA veri politikası)",
        "https://power.larc.nasa.gov/docs/services/", "https://power.larc.nasa.gov/", True,
        "2001→ saatlik; 1° ışınım (kaba); atıf önerilir"),
    "epias": KaynakBilgisi("EPİAŞ Şeffaflık Platformu", "EPİAŞ", "Kullanım şartları (kayıtlı erişim)",
        "https://seffaflik.epias.com.tr/", "https://seffaflik.epias.com.tr/electricity-service/technical/tr/index.html", True,
        "PTF/SMF/KGÜP/gerçek zamanlı üretim/dengesizlik; TGT kimlik; CAS limitleri"),
    "open_meteo": KaynakBilgisi("Open-Meteo", "Open-Meteo", "CC BY 4.0 (veri); ücretsiz katman ticari ✗",
        "https://open-meteo.com/en/terms", "https://open-meteo.com/", False,
        "GEÇİŞ TAMAMLANANA KADAR: ücretsiz katman ticari üründe uyumluluk borcu"),
}


def kunye(kullanilan: list[str], urun: str = "PVQuant") -> str:
    """Künye metni (TR). Lisansın üç şartı: kaynak adı, lisans + bağlantı, 'işlenmiştir' notu."""
    satirlar = []
    for k in kullanilan:
        b = KAYNAKLAR[k]
        satirlar.append(f"• {b.ad} — {b.kurum}; lisans: {b.lisans} ({b.lisans_url})")
    govde = "\n".join(satirlar)
    return (
        "Veri kaynakları ve lisanslar\n"
        f"{govde}\n"
        f"Veriler {urun} tarafından indirilmiş, birleştirilmiş ve işlenmiştir; kaynak kurumlar bu ürünü "
        "desteklemez ve sonuçlardan sorumlu değildir. Ham veriler ilgili kurumların şartlarıyla erişilebilir."
    )


def readme_bolumu(kullanilan: list[str]) -> str:
    """README 'Veri kaynakları' bölümü (Markdown)."""
    satirlar = ["## Veri kaynakları", ""]
    for k in kullanilan:
        b = KAYNAKLAR[k]
        satirlar.append(f"- **{b.ad}** — {b.kurum} · [{b.lisans}]({b.lisans_url}) · [veri]({b.veri_url}) · {b.not_}")
    satirlar += ["", "Veriler PVQuant tarafından işlenmiştir; kaynak kurumlar bu ürünü desteklemez."]
    return "\n".join(satirlar)


def uyumluluk_denetimi(kullanilan: list[str]) -> list[str]:
    """Ticari kullanıma kapalı kaynak varsa uyarı listesi döner (boş = temiz)."""
    return [f"{KAYNAKLAR[k].ad}: ticari kullanım izni yok — {KAYNAKLAR[k].not_}"
            for k in kullanilan if not KAYNAKLAR[k].ticari_kullanim]
