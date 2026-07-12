"""Ingestion katmanı — çekirdek veri yapıları.

Akışın her aşaması bu yapılar üzerinden konuşur:

    ham dosya → FileFormat (algılama) → ColumnMapping (eşleme)
             → TransformSpec (dönüştürme) → QualityReport (doğrulama)
             → IngestionResult (SCADAData + rapor + şablon)

Tasarım ilkesi: hiçbir aşama sessiz karar vermez. Her otomatik tespit
bu yapılarda kayda geçer, kullanıcıya gösterilir ve onaydan sonra
uygulanır. Şüpheli satırlar silinmez, bayraklanır.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

import pandas as pd


class RowFlag(str, Enum):
    """Satır düzeyi kalite bayrakları. VALID dışındakiler eğitime girmez."""

    VALID = "valid"
    NEGATIVE_POWER = "negative_power"        # güç < 0
    NIGHT_PRODUCTION = "night_production"    # gece saatinde üretim > 0 (tz hatası işareti!)
    OVER_CAPACITY = "over_capacity"          # kurulu gücün belirgin üstünde
    FROZEN_VALUE = "frozen_value"            # aynı değer saatlerce tekrar (iletişim arızası)
    DUPLICATE_TIME = "duplicate_time"        # tekrarlanan timestamp
    DST_AMBIGUOUS = "dst_ambiguous"          # yaz saati geçişinde belirsiz/eksik saat
    UNPARSEABLE = "unparseable"              # sayıya/tarihe çevrilemedi


@dataclass
class FileFormat:
    """Aşama 1 çıktısı: dosyanın fiziksel formatı.

    Tüm alanlar otomatik tespit edilir ama kullanıcı/şablon override
    edebilir. `confidence` alanları UI'da 'emin değilim, kontrol et'
    uyarısı göstermek içindir.
    """

    encoding: str = "utf-8"
    delimiter: str = ","
    decimal: str = "."
    header_row: int = 0            # 0-tabanlı; FusionSolar'da 3-5 olabilir
    sheet_name: Optional[str] = None  # Excel ise
    n_preview_rows: int = 0
    confidence: float = 1.0        # 0-1; sezgisellerin kendine güveni

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ColumnMapping:
    """Aşama 2 çıktısı: dosya kolonları → kanonik alanlar.

    Kanonik alanlar SCADAData ile birebir aynıdır. `power_unit` ve
    `energy_column` ayrımı Aşama 3'te dönüşümü belirler.
    """

    timestamp: str
    power: Optional[str] = None       # anlık güç kolonu (varsa)
    energy: Optional[str] = None      # aralık enerjisi kolonu (varsa)
    poa_irradiance: Optional[str] = None
    temp_ambient: Optional[str] = None
    temp_module: Optional[str] = None
    wind_speed: Optional[str] = None
    ghi: Optional[str] = None         # saha GHI ölçümü (hibrit kalibrasyonda altın değerinde)

    #: Otomatik önerinin alan bazında güveni: {"power": 0.95, ...}
    confidence: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def has_power_source(self) -> bool:
        return self.power is not None or self.energy is not None


@dataclass
class TransformSpec:
    """Aşama 3 çıktısı: uygulanacak dönüşümler.

    Attributes:
        source_timezone: Dosyadaki zamanların dilimi (IANA). "UTC" veya
            santralin yerel dilimi. None ise kullanıcıya sorulmalıdır.
        power_unit: "kW" | "MW" | "W". Otomatik tespit kurulu güce göre.
        timestep_minutes: Kaynak verinin zaman adımı.
        energy_to_power: Enerji kolonundan güç türetildi mi?
        energy_cumulative: Kaynak enerji kolonu kümülatif (ömür) sayaç
            mıydı? True ise diff alınarak aralık enerjisine çevrildi
            (SolarEdge Etotal, Enphase whLifetime deseni).
    """

    source_timezone: Optional[str] = None
    power_unit: str = "kW"
    timestep_minutes: int = 60
    energy_to_power: bool = False
    energy_cumulative: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QualityReport:
    """Aşama 4 çıktısı: kullanıcıya gösterilecek kalite karnesi.

    Satır sayıları bayrak bazında tutulur; `flags` serisi satır düzeyi
    detayı taşır (index = timestamp).
    """

    n_rows_read: int = 0
    n_rows_valid: int = 0
    flag_counts: dict[str, int] = field(default_factory=dict)
    gap_hours: int = 0
    gap_periods: list[tuple[str, str]] = field(default_factory=list)  # (başlangıç, bitiş) ISO
    coverage_start: Optional[str] = None
    coverage_end: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    @property
    def valid_fraction(self) -> float:
        return self.n_rows_valid / self.n_rows_read if self.n_rows_read else 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    def summary_tr(self) -> str:
        """Kullanıcıya gösterilecek tek paragraflık Türkçe özet."""
        parts = [
            f"{self.n_rows_read:,} satır okundu, {self.n_rows_valid:,} geçerli "
            f"(%{100 * self.valid_fraction:.1f})."
        ]
        if self.gap_hours:
            parts.append(f"{self.gap_hours} saatlik boşluk var.")
        for flag, n in sorted(self.flag_counts.items(), key=lambda kv: -kv[1]):
            if flag != RowFlag.VALID.value and n > 0:
                label = {
                    "negative_power": "negatif güç",
                    "night_production": "gece üretimi (saat dilimi hatası olabilir!)",
                    "over_capacity": "kapasite üstü değer",
                    "frozen_value": "donmuş değer (iletişim arızası olabilir)",
                    "duplicate_time": "tekrarlanan zaman damgası",
                    "dst_ambiguous": "yaz saati geçişi belirsizliği",
                    "unparseable": "okunamayan satır",
                }.get(flag, flag)
                parts.append(f"{n} satır: {label}.")
        parts.extend(self.warnings)
        return " ".join(parts)


@dataclass
class IngestionResult:
    """Nihai çıktı: normalize veri + tüm karar izleri.

    Attributes:
        data: Saatlik, UTC, kanonik kolonlu DataFrame. Kolonlar:
            power_kw (zorunlu) + varsa energy_kwh, poa_global, t_air,
            t_module, wind_speed, ghi + flag (RowFlag değeri).
        file_format / mapping / transform: Uygulanan kararların kaydı;
            şablon olarak saklanır, denetim izi (audit trail) sağlar.
        report: Kalite karnesi.
    """

    data: pd.DataFrame
    file_format: FileFormat
    mapping: ColumnMapping
    transform: TransformSpec
    report: QualityReport

    def to_clean_frame(self) -> pd.DataFrame:
        """Yalnızca VALID satırları, flag kolonu olmadan döner.

        Kalibrasyon ve hibrit eğitimi bu frame'i kullanır; models_v2
        HistoricalData.data doğrudan bunu kabul eder (timestamp kolonu
        reset_index ile eklenir).
        """
        clean = self.data[self.data["flag"] == RowFlag.VALID.value].drop(columns=["flag"])
        clean = clean.rename_axis("timestamp")   # index adı kaynaktan miras kalabilir
        return clean.reset_index()

    def to_template(self) -> dict:
        """Bu ingestion'ın kararlarını yeniden kullanılabilir şablon yapar."""
        return {
            "file_format": self.file_format.to_dict(),
            "mapping": self.mapping.to_dict(),
            "transform": self.transform.to_dict(),
        }