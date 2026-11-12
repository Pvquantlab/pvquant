"""v2.598 (Faz 4 F4-C, Stage 4) — VERİ KALİTESİ SÖZLÜĞÜ: tek yer.

Altı ayrı sözlük (scada_hourly.flag, kaynak_saatlik.tamlik, sayaç nitelik, ölçüm uygunluk nedeni, veri yolu durumu, rapor/web
etiketleri) tek `Nitelik` kümesine eşlenir; «hangi saat hangi amaç için geçerli» kararı (`gecerli_mi`) ve SQL süzgeci
(`sql_kosulu`) buradan çıkar. SAF: DB yok, ağ yok. Anlam değişmez: eski `flag='valid'` = `sql_kosulu('karne')`,
eski `flag IN ('valid','kisinti')` = `sql_kosulu('kayip')`; denklik testi `tests/test_kalite_sozlugu_v2598.py`.
Belge: docs/VERI-KALITESI.md.
"""
from __future__ import annotations

from enum import Enum

import pandas as pd

SOZLUK_SURUMU = "2026-11-12"


class Nitelik(str, Enum):
    DOGRULANMIS = "dogrulanmis"   # bağımsız kaynakla (sayaç/EPİAŞ) çapraz doğrulanmış ölçüm
    OLCULMUS = "olculmus"         # ölçülmüş, geçerli saat
    KISMI = "kismi"               # saatin bir kısmı ölçülü (<45 dk) — üretim serisine girmez
    TAHMINI = "tahmini"           # kaynak «tahmini» demiş (sayaç portalı Estimated)
    DOLDURULMUS = "doldurulmus"   # kaynak sonradan doldurmuş (FilledByDiff)
    ELLE = "elle"                 # elle girilmiş
    SUPHELI = "supheli"           # ölçüm var ama fiziksel/istatistiksel şüphe (gece üretimi, donmuş, kapasite üstü, anomali, gündüz sıfır)
    GECIKMIS = "gecikmis"         # beklenen saat geldi, veri henüz gelmedi (tazelik)
    EKSIK = "eksik"               # kaynakta o saat için satır yok
    GECERSIZ = "gecersiz"         # okunamaz / tekrar / günlük özet — saatlik seriye giremez


ETIKET = {
    Nitelik.DOGRULANMIS: ("doğrulanmış", "bağımsız bir kaynakla karşılaştırılmış ölçüm"),
    Nitelik.OLCULMUS: ("ölçülmüş", "sahadan gelen, kontrolleri geçen saatlik ölçüm"),
    Nitelik.KISMI: ("kısmi saat", "saatin 45 dakikasından azı ölçülü; toplamlara girmez"),
    Nitelik.TAHMINI: ("tahmini", "kaynak bu değeri tahmini olarak işaretlemiş"),
    Nitelik.DOLDURULMUS: ("doldurulmuş", "kaynak eksik değeri sonradan doldurmuş"),
    Nitelik.ELLE: ("elle girilmiş", "ölçüm cihazından değil, elle girilmiş"),
    Nitelik.SUPHELI: ("şüpheli", "ölçüm var ama fiziksel olarak beklenmedik; hesaplara girmez"),
    Nitelik.GECIKMIS: ("gecikmiş", "saat geçti, veri henüz gelmedi"),
    Nitelik.EKSIK: ("eksik", "bu saat için kaynakta kayıt yok"),
    Nitelik.GECERSIZ: ("geçersiz", "okunamayan, tekrarlanan ya da saatlik olmayan kayıt"),
}

# ---- scada_hourly.flag sözlüğü (CHECK kısıtı bu kümedir; eski yazımlar eşlenir, yeni satırda kullanılmaz) --------------
FLAG_NITELIK: dict[str, Nitelik] = {
    "valid": Nitelik.OLCULMUS,
    "kisinti": Nitelik.OLCULMUS,          # ölçüm geçerli; kısıntı boyutu ayrı (hijyen) — karne/kalibrasyon dışı, kayıp analizi içi
    "partial_hour": Nitelik.KISMI,
    "anomali": Nitelik.SUPHELI,           # EPİAŞ gerçek zamanlı üretim anomali bayrağı
    "sifir_gunduz": Nitelik.SUPHELI,      # v2.598: gündüz, ışınım var, güç 0
    "negative_power": Nitelik.SUPHELI,
    "night_production": Nitelik.SUPHELI,
    "over_capacity": Nitelik.SUPHELI,
    "frozen_value": Nitelik.SUPHELI,
    "dst_ambiguous": Nitelik.SUPHELI,
    "eksik": Nitelik.EKSIK,               # v2.598: boş saat (kaynakta satır yok) — artık 'unparseable' değil
    "unparseable": Nitelik.GECERSIZ,
    "duplicate_time": Nitelik.GECERSIZ,
    "gunluk_ozet": Nitelik.GECERSIZ,      # saatlik seriye giremez; aylık toplama girer (ayrı yol)
    # eski yazımlar (v2.108 öncesi raporlar / göç öncesi satırlar olabilir) — yeni satırda yazılmaz
    "frozen": Nitelik.SUPHELI,
    "yanlis_yil": Nitelik.GECERSIZ,
    "yanlis_yil_2006": Nitelik.GECERSIZ,
}
FLAGLAR: tuple[str, ...] = tuple(FLAG_NITELIK)
ESKI_FLAGLAR = frozenset({"frozen", "yanlis_yil", "yanlis_yil_2006"})

# ---- amaç → kabul edilen flag kümesi (ESKİ süzgeçlerle birebir) ------------------------------------------------------
_V = ("valid",)
_VK = ("valid", "kisinti")
AMAC_FLAGLARI: dict[str, tuple[str, ...]] = {
    "karne": _V,            # doğruluk karnesi, konformal/ufuk/sapma öğrenme — yalnız geçerli ölçüm
    "kalibrasyon": _V,
    "uzlastirma": _V,       # program sapması, finansal etki ölçüm serisi
    "rapor": _V,            # rapor ve özet üretim toplamları
    "tazelik": _V,          # son ölçüm zamanı, veri yolu durumu
    "kayip": _VK,           # kayıp ayrışımı, hijyen, fizik beklentisi karşılaştırması: kısıntılı saat de ölçümdür
    "kullanilabilirlik": _VK,
    "hijyen": _VK,
}
AMACLAR = tuple(AMAC_FLAGLARI)


def gecerli_flaglar(amac: str) -> tuple[str, ...]:
    if amac not in AMAC_FLAGLARI:
        raise KeyError(f"bilinmeyen amaç: {amac!r} (izinli: {', '.join(AMACLAR)})")
    return AMAC_FLAGLARI[amac]


def gecerli_mi(nitelik_veya_flag: str | Nitelik, amac: str) -> bool:
    """Bir saat bu amaç için geçerli mi? flag değeri verilirse doğrudan küme üyeliği; Nitelik verilirse OLCULMUS/DOGRULANMIS
    (kısıntı bayrağı Nitelik düzeyinde ayrışmaz: 'kayip' amaçları için flag verin)."""
    kabul = gecerli_flaglar(amac)
    if isinstance(nitelik_veya_flag, Nitelik):
        return nitelik_veya_flag in (Nitelik.OLCULMUS, Nitelik.DOGRULANMIS)
    s = str(nitelik_veya_flag)
    if s in FLAG_NITELIK:
        return s in kabul
    try:
        return Nitelik(s) in (Nitelik.OLCULMUS, Nitelik.DOGRULANMIS)
    except ValueError:
        return False


def sql_kosulu(amac: str, alias: str = "") -> str:
    """SQL parçası: `alias.flag IN ('valid')` / `IN ('valid','kisinti')` — eski elle yazılmış süzgeçlerin TEK kaynağı.
    Parametre taşımaz (sabit sözlük); `f"... WHERE {sql_kosulu('karne', 's')} ..."` biçiminde eklenir."""
    a = f"{alias}." if alias else ""
    return f"{a}flag IN ({', '.join(repr(f) for f in gecerli_flaglar(amac))})"


def pandas_maskesi(flag: pd.Series, amac: str) -> pd.Series:
    """Aynı karar pandas tarafında."""
    return flag.isin(gecerli_flaglar(amac))


# ---- diğer sözlüklerden Nitelik'e eşlemeler --------------------------------------------------------------------------
TAMLIK_NITELIK = {"measured_complete": Nitelik.OLCULMUS, "measured_partial": Nitelik.KISMI, "estimated": Nitelik.TAHMINI}
SAYAC_NITELIK = {"olculmus": Nitelik.OLCULMUS, "tahmini": Nitelik.TAHMINI, "doldurulmus": Nitelik.DOLDURULMUS, "elle": Nitelik.ELLE, "yok": Nitelik.EKSIK}


def flag_nitelik(flag: str | None) -> Nitelik:
    if flag is None:
        return Nitelik.EKSIK
    return FLAG_NITELIK.get(str(flag), Nitelik.GECERSIZ)


def tamlik_nitelik(tamlik: str | None) -> Nitelik:
    return TAMLIK_NITELIK.get(str(tamlik), Nitelik.EKSIK) if tamlik is not None else Nitelik.EKSIK


def sayac_nitelik(nitelik: str | None) -> Nitelik:
    return SAYAC_NITELIK.get(str(nitelik), Nitelik.EKSIK) if nitelik is not None else Nitelik.EKSIK


def uygunluk_nitelik(neden: str | None) -> Nitelik:
    """olcum_uygunluk_service.siniflandir çıktısındaki `neden` → Nitelik.
    'olculdu' → ölçülmüş; 'eksik' → eksik; 'kismi_saat' → kısmi; 'bayrak:<flag>' → o bayrağın niteliği;
    'sayac:<nitelik>' → sayaç niteliği; 'olay:<tur>' → ölçüm var ama olay (kısıt/arıza) saati → şüpheli (amaç için dışlanır)."""
    if not neden:
        return Nitelik.EKSIK
    n = str(neden)
    if n == "olculdu":
        return Nitelik.OLCULMUS
    if n == "eksik":
        return Nitelik.EKSIK
    if n == "kismi_saat":
        return Nitelik.KISMI
    if n.startswith("bayrak:"):
        return flag_nitelik(n.split(":", 1)[1])
    if n.startswith("sayac:"):
        return sayac_nitelik(n.split(":", 1)[1])
    if n.startswith("olay:"):
        return Nitelik.SUPHELI
    return Nitelik.GECERSIZ


# ---- tazelik ---------------------------------------------------------------------------------------------------------
TAZELIK_ESIK_SAAT = 48.0   # son geçerli ölçümden bu kadar saat geçtiyse «gecikmiş» (Portföy satırındaki 2 gün eşiğiyle aynı)


def tazelik_durumu(son_olcum, simdi=None, esik_saat: float = TAZELIK_ESIK_SAAT) -> dict:
    """Son geçerli ölçüm zamanından tazelik: {kod: taze|gecikmis|eksik, nitelik, etiket, yas_saat}."""
    if son_olcum is None or (isinstance(son_olcum, float) and pd.isna(son_olcum)):
        return {"kod": "eksik", "nitelik": Nitelik.EKSIK.value, "etiket": "ölçüm yok", "yas_saat": None}
    simdi = pd.Timestamp(simdi) if simdi is not None else pd.Timestamp.now(tz="UTC")
    simdi = simdi.tz_localize("UTC") if simdi.tzinfo is None else simdi.tz_convert("UTC")
    s = pd.Timestamp(son_olcum); s = s.tz_localize("UTC") if s.tzinfo is None else s.tz_convert("UTC")
    yas = round(float((simdi - s).total_seconds() / 3600.0), 1)
    if yas > esik_saat:
        return {"kod": "gecikmis", "nitelik": Nitelik.GECIKMIS.value, "etiket": f"son ölçüm {int(yas // 24)} gün önce", "yas_saat": yas}
    return {"kod": "taze", "nitelik": Nitelik.OLCULMUS.value, "etiket": "veri güncel", "yas_saat": yas}


def sozluk() -> dict:
    """API/arayüz için sözlüğün tamamı (GET /v1/sozluk/kalite)."""
    return {
        "surum": SOZLUK_SURUMU,
        "nitelikler": [{"kod": n.value, "etiket": ETIKET[n][0], "aciklama": ETIKET[n][1],
                        "hesaba_girer": n in (Nitelik.OLCULMUS, Nitelik.DOGRULANMIS)} for n in Nitelik],
        "bayraklar": {f: {"nitelik": n.value, "etiket": ETIKET[n][0], "eski": f in ESKI_FLAGLAR} for f, n in FLAG_NITELIK.items()},
        "amaclar": {a: list(fl) for a, fl in AMAC_FLAGLARI.items()},
        "tamlik": {k: v.value for k, v in TAMLIK_NITELIK.items()},
        "sayac": {k: v.value for k, v in SAYAC_NITELIK.items()},
        "tazelik_esik_saat": TAZELIK_ESIK_SAAT,
    }
