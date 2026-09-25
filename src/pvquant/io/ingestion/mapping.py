"""Aşama 2 — Kolon eşleme.

Dosya kolonlarını kanonik alanlara (timestamp, power, energy, ...)
eşler. Üç katmanlı strateji:

  1. Sözlük eşleşmesi: 16+ vendor'un CSV/API formatlarından derlenmiş
     çok dilli sözlük (marka referans dokümanından). Tam eşleşme > 
     kelime-sınırlı içerme > düz içerme.
  2. Fuzzy yedeği: rapidfuzz varsa Levenshtein, yoksa difflib. Sadece
     biçim varyantlarını (büyük/küçük harf, alt çizgi, birim eki)
     yakalar — anlamsal çeviri YAPMAZ.
  3. İçerik doğrulaması: aday kolonun İÇERİĞİ iddiaya uymalı —
     "timestamp" diye eşlenen kolon gerçekten tarihe çevrilebiliyor mu,
     "power" eşlenen kolon sayısal mı? İçerik tutmuyorsa güven düşer.

ÖNEMLİ TASARIM NOTU (GHI vs POA):
  GHI (Global Horizontal Irradiance) yatay düzlem ışınımıdır;
  POA (Plane of Array) eğik panel düzlemi ışınımıdır. Kalibrasyon
  fizik zinciri POA bekler; GHI'yi POA sanıp beslemek modeli bozar.
  Bu yüzden iki alan AYRI sözlüklerde tutulur; marka referansındaki
  öneriye rağmen 'ghi' asla poa_irradiance'a alias olarak eklenmez.
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

from .contracts import ColumnMapping

#: Kanonik alan → eşanlamlılar. Küçük harf, aksansız karşılaştırılır.
#: Birime dair ekler ("(kW)", "[MW]") karşılaştırmadan önce soyulur.
SYNONYMS: dict[str, list[str]] = {
    "timestamp": [
        "timestamp", "time", "datetime", "date time", "date", "tarih",
        "zaman", "tarih saat", "saat", "period", "interval start",
        "zeit", "fecha", "data", "collection time", "statistical period",
        # Marka referansı
        "reading_time", "measured_at", "sample time", "log time",
        "date_time", "log date", "record time",
        # NREL PVDAQ (1853 sistem, tüm dosyalar): 'measured_at' değil 'measured_on'
        "measured_on",
        # v2.357: KENDİ dışa aktarımımız (ingest_service.DISA_KOLONLAR) geri
        # okunabilmeli — "Veriniz sizindir" CSV'si yuvarlak yolculukta kayıpsız.
        "ts_utc",
        # REFPLANT / Türkçe yıllık üretim raporları
        "dönem", "donem", "istatistiksel donem", "istatistiksel dönem",
    ],
    "power": [
        "power", "active power", "ac power", "ac active power", "p_ac",
        "pac", "guc", "aktif guc", "cikis gucu", "uretim gucu",
        "leistung", "wirkleistung", "potencia", "puissance",
        "grid power", "output power", "total active power", "power kw",
        # Marka referansı (SolarEdge, Fronius, Enphase, SMA, Sungrow)
        "powerreal_p_sum", "wnow", "w_now", "pac_total", "p_total",
        "ac_power", "invout_power", "power_ac", "inverter power",
        "instant power", "current power", "actual power", "pv power",
    ],
    "energy": [
        "energy", "yield", "production", "generation", "enerji",
        "uretim", "gunluk uretim", "toplam uretim", "ertrag",
        "energia", "total yield", "daily yield", "inverter yield",
        "feed-in energy", "on-grid energy", "kwh",
        # v2.366: SMA Sunny Explorer ad satırı (T6 canlı)
        "day yield",
        # Marka referansı (SolarEdge, Enphase, Fronius, Sungrow)
        "etotal", "e_total", "e-total", "whlifetime", "wh_lifetime",
        "wh lifetime", "lifetime energy", "cumulative energy",
        "energyreal_wac_sum_produced", "day_energy", "energy_today",
        "eday", "e_day", "ac_energy", "total_energy_generated",
        # v2.357: kendi dışa aktarım adı (yuvarlak yolculuk)
        "energy_kwh",
        # REFPLANT / Türkçe yıllık üretim raporları
        "kazanç", "kazanc", "inverter kazanç", "inverter kazanc",
        "inverter kazancı", "inverter kazanci",
        "pv kazancı", "pv kazanci", "teorik kazanç", "teorik kazanc",
    ],
    "poa_irradiance": [
        "poa", "poa irradiance", "plane of array", "tilted irradiance",
        "gpoa", "g_poa", "isinim", "panel isinimi", "egik isinim",
        "einstrahlung", "irradiancia", "pyranometer tilted",
        # Marka referansı
        "irradiation", "irradiance_poa", "gti", "g_tilted",
        "poa_global", "poa global", "irradiance tilted",
        # v2.357: kendi dışa aktarım adı (yuvarlak yolculuk)
        "poa_wm2",
        # REFPLANT Türkçe - "işıma" genel PV konteksinde POA/tilted
        # anlamında kullanılır; kullanıcı onay ekranında düzeltebilir
        "işıma", "isima", "toplam işıma", "toplam isima",
        # DİKKAT: 'ghi', 'global horizontal' BURAYA EKLENMEZ (bkz. modül docstring)
    ],
    "ghi": [
        "ghi", "global horizontal", "horizontal irradiance",
        "yatay isinim", "global isinim", "pyranometer horizontal",
        "g_horizontal", "horizontal_irradiance", "irradiance_ghi",
        "solar_ghi", "shortwave_radiation",
        # Sungrow iSolarCloud: 'Transient/Daily/Total Horizontal Irradiation' —
        # '-ation' eki yüzünden yukarıdakilerin hiçbiri eşleşmiyor, POA'ya kayıyordu (Bulgu 8A)
        "horizontal irradiation", "global horizontal irradiation",
    ],
    "temp_ambient": [
        "ambient", "ambient temperature", "air temperature", "t_amb",
        "tamb", "ortam sicakligi", "hava sicakligi", "dis sicaklik",
        "umgebungstemperatur", "temperatura ambiente",
        # DİKKAT: çıplak 'temp' BURAYA EKLENMEZ — her sıcaklık kolonunu
        # (CellTemp, pv_temperature, ModuleTemperature…) ortam sanıyordu (Bulgu 8C)
        # Marka referansı
        "ambient_temperature", "outdoor_temp", "environment temp",
        "t_ambient", "air_temp",
        # v2.357: kendi dışa aktarım adı 't_air' LİSTEDE YOKTU — "Veriniz
        # sizindir" CSV'si geri yüklenince ortam sıcaklığı sessizce düşüyordu
        # (24 Eyl canlı önizlemede yakalandı: "Eşlenmeyen kolonlar: t_air").
        "t_air",
        # REFPLANT
        "ortalama sicaklik", "ortalama sıcaklık",
    ],
    "temp_module": [
        "module temperature", "panel temperature", "cell temperature",
        "t_mod", "tmod", "modul sicakligi", "panel sicakligi",
        "back sheet temperature", "bom temperature",
        # Marka referansı
        "module_temp", "panel_temp", "t_module", "temp_module",
        "backsheet_temp", "cell_temp", "pv_temp",
        # skytron PVGuard (Almanca)
        "modultemperatur", "modul temperatur",
    ],
    "wind_speed": [
        # DİKKAT: çıplak 'wind' BURAYA EKLENMEZ — üretim dosyalarında 'wind'
        # rüzgâr SANTRALİ üretimidir (MW), hız değil (Bulgu 8C, Türkiye ülke geneli)
        "wind speed", "ws", "ruzgar", "ruzgar hizi",
        "windgeschwindigkeit", "velocidad del viento",
        # Marka referansı
        "wind_speed", "windspeed", "ws_10m", "wind_ms",
    ],
}

#: Alan bazlı DIŞLAMA: kolon adı bunlardan birini içeriyorsa o alana aday
#: olamaz. Hepsi envanterde ölçülmüş gerçek çarpışmalar (Bulgu 7, 8A, 8C):
#: power_factor → power (2000x hata), Horizontal Irradiation → poa,
#: CellTemp → temp_ambient, wind (santral üretimi) → wind_speed.
_EXCLUDE: dict[str, list[str]] = {
    "power": ["power factor", "reactive", "apparent", "radiation", "irradia",
              "cos phi", "derating", "reduction"],
    "energy": ["radiation", "irradia", "einstrahlung"],
    "poa_irradiance": ["horizontal", "ghi", "diffuse", "direct normal", "dni", "dhi"],
    "ghi": ["tilt", "poa", "plane of array"],
    "temp_ambient": ["module", "modul", "cell", "panel", "pv", "bom", "inverter",
                     "internal", "cabinet", "heat sink", "battery"],
    "temp_module": ["ambient", "air", "ortam", "inverter", "internal", "cabinet",
                    "battery"],
    "wind_speed": ["power", "energy", "generation", "direction", "dir", "guc",
                   "uretim"],
}

#: Parantez/köşeli ayraç içi yalnızca BİRİM gibi görünüyorsa soyulur
#: ("(kW)", "[W/m2]", "(°C)"); sözcük taşıyorsa korunur ("(PV module)",
#: "(reactive)"). Koşulsuz silmek 'Temp. (PV module)' → 'temp' yapıp modül
#: sıcaklığını 1.0 güvenle ortam sıcaklığı olarak eşliyordu (Bulgu 8B).
_BRACKET = re.compile(r"[\(\[\{]([^\)\]\}]*)[\)\]\}]")
_UNIT_LIKE = re.compile(
    r"^\s*[kMGmµ]?(w|wh|va|var|v|a|hz|°?c|%|m/s|w/m[²2]|k?wh/m[²2]|mj/m[²2]|ms|s|min|h)\s*$",
    re.IGNORECASE,
)


def _strip_units(s: str) -> str:
    """Birim parantezlerini atar, anlam taşıyan parantez içini sözcük olarak bırakır."""
    def _repl(m: re.Match) -> str:
        inner = m.group(1)
        return " " if _UNIT_LIKE.match(inner) else f" {inner} "
    return _BRACKET.sub(_repl, s)


def _excluded(col_norm: str, field: str) -> bool:
    """Normalize edilmiş kolon adı bu alan için dışlanmış mı?"""
    for x in _EXCLUDE.get(field, ()):
        if re.search(rf"\b{re.escape(x)}\b", col_norm) or (len(x) >= 6 and x in col_norm):
            return True
    return False

#: Fuzzy eşleşme eşiği (0-100). Marka biçim varyantlarını yakalar
#: ("AC_POWER" ↔ "ac power"), anlamsal çeviri yapmaz.
_FUZZY_THRESHOLD = 88

# rapidfuzz yoksa difflib'e düş
try:
    from rapidfuzz import fuzz as _rapidfuzz
    def _fuzzy_score(a: str, b: str) -> float:
        return _rapidfuzz.ratio(a, b)
except ImportError:
    from difflib import SequenceMatcher
    def _fuzzy_score(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio() * 100.0


def normalize_name(name: str) -> str:
    """Kolon adını karşılaştırma formuna indirger.

    Küçük harf, Türkçe/aksanlı karakterler sadeleştirilir (İ→i, ş→s),
    birim ekleri ve fazla boşluklar atılır, alt çizgi boşluğa çevrilir.
    """
    s = _strip_units(str(name))
    s = s.replace("_", " ").replace("-", " ").replace(".", " ")
    # Türkçe özel: 'ı' aksan ayrıştırmasında kaybolur, önce elle çevir
    s = s.replace("ı", "i").replace("İ", "i")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip().lower()


#: SYNONYMS'in normalize edilmiş kopyası (alt çizgi → boşluk, aksan atılır).
#: Kolon adı normalize edilip eşanlamlı HAM bırakılınca "module_temp" ile
#: "module temp" hiçbir aşamada tutmuyor, yalnız fuzzy yedeğine (0.5)
#: düşüyordu — 'measured_on' dahil. Sözlük burada bir kez normalize edilir.
_SYNONYMS_NORM: dict[object, list[str]] = {}


def _syn_norm(field: str | None, synonyms: list[str]) -> list[str]:
    """Alanın eşanlamlılarını normalize edilmiş hâliyle döner (önbellekli)."""
    key = field if field is not None else id(synonyms)
    cached = _SYNONYMS_NORM.get(key)
    if cached is None:
        cached = list(dict.fromkeys(normalize_name(s) for s in synonyms))
        _SYNONYMS_NORM[key] = cached
    return cached


def _match_detail(col_norm: str, synonyms: list[str],
                  field: str | None = None) -> tuple[float, int]:
    """(skor, özgüllük) döner.

    Skor: tam=1.0, kelime sınırlı içerme=0.8, sırasız token eşleşmesi=0.7
    ("module temp" ⊂ "temp pv module"), düz içerme=0.6, fuzzy yedek=0.5.
    Özgüllük = eşleşen eşanlamlının uzunluğu: eşit skorda daha uzun (daha
    özgül) eşanlamlı kazanır. Eskiden eşitlik alfabetik kolon adına düşüyor,
    'power_factor__596' > 'ac_power__584' olduğu için güç faktörü güç
    seçiliyordu (Bulgu 7).
    `field` verilirse _EXCLUDE uygulanır; dışlanan ad o alana aday olamaz.
    """
    if field is not None and _excluded(col_norm, field):
        return 0.0, 0
    synonyms = _syn_norm(field, synonyms)
    for syn in synonyms:
        if col_norm == syn:
            return 1.0, len(syn)
    best: tuple[float, int] = (0.0, 0)
    for syn in synonyms:
        if re.search(rf"\b{re.escape(syn)}\b", col_norm):
            best = max(best, (0.8, len(syn)))
    if best[0]:
        return best
    # Sırasız token eşleşmesi — parantez içi sözcükler korununca sıra bozulur
    tokens = set(col_norm.split())
    for syn in synonyms:
        parts = syn.split()
        if len(parts) >= 2 and all(len(p) >= 3 for p in parts) and set(parts) <= tokens:
            best = max(best, (0.7, len(syn)))
    if best[0]:
        return best
    for syn in synonyms:
        if syn in col_norm and len(syn) >= 4:
            best = max(best, (0.6, len(syn)))
    if best[0]:
        return best
    # Fuzzy yedek — sadece biçim varyantları için (case, underscore, birim)
    best_fuzzy = 0.0
    for syn in synonyms:
        if len(syn) < 4:
            continue
        s = _fuzzy_score(col_norm, syn)
        if s > best_fuzzy:
            best_fuzzy = s
    return (0.5, 0) if best_fuzzy >= _FUZZY_THRESHOLD else (0.0, 0)


def _match_score(col_norm: str, synonyms: list[str]) -> float:
    """Eşleşme gücü (0-1). Geriye dönük uyumlu sarmalayıcı; dışlama uygulamaz."""
    return _match_detail(col_norm, synonyms)[0]


def _content_check(series: pd.Series, field: str) -> float:
    """İçerik iddiaya uyuyor mu? 0-1 arası çarpan döner."""
    sample = series.dropna().head(50)
    if sample.empty:
        return 0.5
    if field == "timestamp":
        from .transform import _parse_datetime_robust
        return float(_parse_datetime_robust(sample).notna().mean())
    # Sayısal alanlar: ondalık virgül ihtimaline karşı çevirip dene
    as_num = pd.to_numeric(
        sample.astype(str).str.replace(",", ".", regex=False), errors="coerce"
    )
    return float(as_num.notna().mean())


def suggest_mapping(df: pd.DataFrame) -> tuple[ColumnMapping, list[str]]:
    """Kolon eşlemesi önerir.

    Her kanonik alan için en yüksek skorlu kolon seçilir; skor =
    isim eşleşmesi × içerik doğrulaması. Bir kolon yalnızca bir alana
    eşlenir (en güçlü iddia kazanır).

    Returns:
        (ColumnMapping, eşlenemeyen kolonların listesi)

    Raises:
        ValueError: timestamp veya güç/enerji kaynağı bulunamazsa —
            bu durumda UI kullanıcıdan manuel eşleme istemelidir.
    """
    # (skor, özgüllük, -kolon sırası, alan, kolon): eşit skorda daha özgül
    # eşanlamlı, o da eşitse dosyada ÖNCE gelen kolon kazanır. Alan ve kolon
    # adı sıralamaya etki etmez — alfabetik şansa bırakılmaz (Bulgu 7).
    candidates: list[tuple[float, int, int, str, str]] = []
    for idx, col in enumerate(df.columns):
        col_norm = normalize_name(col)
        for field, syns in SYNONYMS.items():
            name_score, specificity = _match_detail(col_norm, syns, field)
            if name_score == 0.0:
                continue
            score = name_score * max(_content_check(df[col], field), 0.1)
            if score > 0.10:  # fuzzy yedeğine izin vermek için eşiği düşürdük
                candidates.append((score, specificity, -idx, field, str(col)))

    # Güçlü iddialar önce; her alan ve her kolon en fazla bir kez
    candidates.sort(reverse=True)
    assigned_fields: dict[str, tuple[str, float]] = {}
    used_columns: set[str] = set()
    for score, _specificity, _neg_idx, field, col in candidates:
        if field in assigned_fields or col in used_columns:
            continue
        assigned_fields[field] = (col, round(score, 2))
        used_columns.add(col)

    if "timestamp" not in assigned_fields:
        # v2.366 — İÇERİK YEDEĞİ: adı boş/anlamsız ("Unnamed: 0") zaman kolonu
        # ad eşleşmesiyle bulunamaz. SMA Sunny Explorer'ın adsız tarih kolonu
        # (T6 canlı) ve PVDAQ boş-başlık ailesi (Growatt/FIMER/KACO/Delta/Chint,
        # envanter 'başlık onarıcı') böyle. Atanmamış kolonlar arasında örneklemi
        # hem tarih desenine uyan hem tarihe çözülen İLK kolon zaman sayılır.
        import re as _re
        _desen = _re.compile(r"^\s*\d{1,4}[-/.:]\d{1,2}[-/.]\d{2,4}")
        for col in df.columns:
            if str(col) in used_columns:
                continue
            ornek = df[col].dropna().astype(str).head(20)
            # çok satırlı başlığın veri tarafına sızan tip/birim artıkları
            # ('dd/MM/yyyy', 'Counter') oranı bozmasın — sözlükle elenir
            from .detection import _AD_DISI_HUCRELER
            ornek = ornek[~ornek.str.strip().str.lower().isin(_AD_DISI_HUCRELER)]
            if len(ornek) < 3:
                continue
            desen_orani = ornek.str.match(_desen).mean()
            if desen_orani < 0.9:
                continue
            cozulen = pd.to_datetime(ornek, errors="coerce", dayfirst=True)
            if cozulen.notna().mean() >= 0.9:
                assigned_fields["timestamp"] = (str(col), 0.7)
                used_columns.add(str(col))
                break
    if "timestamp" not in assigned_fields:
        raise ValueError(
            "Zaman kolonu otomatik bulunamadı. "
            f"Mevcut kolonlar: {list(df.columns)}"
        )
    if "power" not in assigned_fields and "energy" not in assigned_fields:
        raise ValueError(
            "Güç veya enerji kolonu otomatik bulunamadı. "
            f"Mevcut kolonlar: {list(df.columns)}"
        )

    mapping = ColumnMapping(
        timestamp=assigned_fields["timestamp"][0],
        power=assigned_fields.get("power", (None,))[0],
        energy=assigned_fields.get("energy", (None,))[0],
        poa_irradiance=assigned_fields.get("poa_irradiance", (None,))[0],
        temp_ambient=assigned_fields.get("temp_ambient", (None,))[0],
        temp_module=assigned_fields.get("temp_module", (None,))[0],
        wind_speed=assigned_fields.get("wind_speed", (None,))[0],
        ghi=assigned_fields.get("ghi", (None,))[0],
        confidence={f: s for f, (_, s) in assigned_fields.items()},
    )
    unmapped = [str(c) for c in df.columns if str(c) not in used_columns]
    return mapping, unmapped