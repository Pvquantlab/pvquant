"""v2.599 (Faz 4 F4-D, Stage 5) — ZAMAN SÖZLEŞMESİ: tek yer.

Kurallar (docs/ZAMAN-SOZLESMESI.md):
  • Saklama UTC, tz-aware; her saatlik satır ARALIK BAŞI damgasıdır (10:00 = 10:00–11:00).
  • Piyasa günü ve kesimler İstanbul dilimindedir (`PIYASA_TZ`); santral günü santralin kendi dilimindedir (`plants.tz`).
  • Kaynak damgası aralık sonu ise (hour-ending 1–24, «24:00», sayaç OSOS) yükleme yolunda aralık başına çevrilir ve künyeye
    (`scada_hourly.kaynak_damga_tipi`) kaynağın kendi konvansiyonu yazılır.
  • Dönem kodları tek çözümleyiciden (`ext/platform/finans.donem_cozumle`) geçer; `aylik_rapor` ona devreder.
SAF: DB yok, ağ yok. Çekirdek (pipeline/models/ext/tahmin) bu modülü içe aktarabilir; tersi yok.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd

PIYASA_TZ = "Europe/Istanbul"                     # tek tanım — IST/IST_AD/PIYASA_TZ adları buna bağlanır
DAMGA_TIPLERI = ("aralik_basi", "aralik_sonu", "anlik")   # scada_hourly.kaynak_damga_tipi CHECK ile aynı
SAKLAMA_DAMGASI = "aralik_basi"                   # arşivde her satırın anlamı
SURUM = "2026-11-12"


def santral_tz(plant) -> str:
    """plants.tz (dict ya da satır benzeri); boşsa piyasa dilimi."""
    tz = plant.get("tz") if hasattr(plant, "get") else getattr(plant, "tz", None)
    return str(tz) if tz else PIYASA_TZ


def utc(ts) -> pd.Timestamp:
    """Herhangi bir damgayı tz-aware UTC'ye çevirir; naif damga UTC sayılır."""
    t = pd.Timestamp(ts)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def gun_basi_utc(gun: date | str, tz: str = PIYASA_TZ) -> pd.Timestamp:
    """Yerel günün başlangıcı (00:00 yerel) UTC olarak; yaz saati geçişli günlerde 23/25 saatlik gün doğal çıkar."""
    g = date.fromisoformat(str(gun)[:10]) if not isinstance(gun, date) else gun
    return pd.Timestamp(g).tz_localize(tz).tz_convert("UTC")


def gun_sonu_utc(gun: date | str, tz: str = PIYASA_TZ) -> pd.Timestamp:
    """Ertesi günün başlangıcı (hariç sınır)."""
    g = date.fromisoformat(str(gun)[:10]) if not isinstance(gun, date) else gun
    return pd.Timestamp(g + pd.Timedelta(days=1)).tz_localize(tz).tz_convert("UTC")


def santral_gunu(ts, tz: str) -> date:
    """UTC damganın santral dilimindeki takvim günü."""
    return utc(ts).tz_convert(tz).date()


def piyasa_gunu(ts) -> date:
    """UTC damganın piyasa (İstanbul) günü — uzlaştırma, KGÜP, DGP."""
    return santral_gunu(ts, PIYASA_TZ)


def program_kesimi(gun: date | str) -> pd.Timestamp:
    """Teslim günü D için D-1 KGÜP kesim anı (İstanbul; 1.1.2025'ten 15:30, öncesinde 16:00 — kural: ext/turkiye/kurallar.kgup_kesim)."""
    from pvquant.ext.turkiye import kurallar as kr
    g = date.fromisoformat(str(gun)[:10]) if not isinstance(gun, date) else gun
    (kh, km), _ = kr.kgup_kesim(g)
    return pd.Timestamp(g, tz=PIYASA_TZ) - pd.Timedelta(days=1) + pd.Timedelta(hours=kh, minutes=km)


def donem_cozumle(kod: str | None, bugun: date | None = None, tz: str = PIYASA_TZ) -> dict:
    """Dönem kodu (YYYY-MM-DD | YYYY-Wnn | YYYY-MM | YYYY-QN | YYYY) → {tur, bas, bit, bas_utc, bit_utc, etiket, kirpildi, gun, saat}.
    Tek çözümleyici: ext/platform/finans.donem_cozumle."""
    from pvquant.ext.platform import finans as fn
    return fn.donem_cozumle(kod, bugun, tz=tz)


def saat_damgasi_araliga(index: pd.DatetimeIndex, damga_tipi: str, adim_dk: int) -> pd.DatetimeIndex:
    """Kaynak damgasını aralık başına çevirir: 'aralik_sonu' → adım kadar geri; 'aralik_basi' / 'anlik' olduğu gibi (anlık ölçüm
    o anı izleyen aralığın temsilcisi sayılır; künyede belirtilir)."""
    if damga_tipi not in DAMGA_TIPLERI:
        raise ValueError(f"damga_tipi {damga_tipi!r} tanımsız (izinli: {', '.join(DAMGA_TIPLERI)})")
    if damga_tipi == "aralik_sonu":
        return index - pd.Timedelta(minutes=int(adim_dk))
    return index


def simdi_utc() -> datetime:
    """Tek «şimdi» kaynağı (testlerde yamalanır)."""
    return datetime.now(timezone.utc)
