"""SCADA CSV okuyucusu.

FusionSolar (Huawei) ve genel CSV formatlarından üretim verisini yükler.
Üretim verisi PVQuant'ta iki amaçla kullanılır:

1. **Kalibrasyon**: 6+ ay tarihsel veri ile model parametrelerini sahaya kalibre et.
2. **Doğrulama**: Tahmin sonrası gerçek üretim ile karşılaştırma (MAPE, RMSE).

CSV'lerde beklenen iki temel alan: timestamp ve güç/enerji. POA ışınımı ve
ortam sıcaklığı varsa kalibrasyon kalitesi artar.

Kullanım:
    >>> from pvquant.io.scada import load_fusionsolar_csv
    >>> scada = load_fusionsolar_csv("merkas_2025.csv")
    >>> scada.power_kw.head()
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import logging
from rapidfuzz import fuzz, process


@dataclass(frozen=True)
class SCADAData:
    """SCADA üretim verisi konteyneri.

    Tüm seriler aynı zaman indeksini paylaşır.

    Attributes:
        power_kw: Anlık veya saatlik ortalama AC güç, kW.
        energy_kwh: Saatlik enerji üretimi, kWh (varsa).
        poa_irradiance: Ölçülen POA ışınımı, W/m² (varsa, kalibrasyon için).
        temp_ambient: Ortam sıcaklığı, °C (varsa).
        temp_module: Modül arka yüz sıcaklığı, °C (varsa, ileri kalibrasyon için).
        wind_speed: Rüzgar hızı, m/s (varsa).
        plant_name: Santral adı.
        timestep_minutes: Veri zaman adımı (15, 30, 60 dakika).
    """

    power_kw: pd.Series
    energy_kwh: pd.Series | None
    poa_irradiance: pd.Series | None
    temp_ambient: pd.Series | None
    temp_module: pd.Series | None
    wind_speed: pd.Series | None
    plant_name: str
    timestep_minutes: int

    @property
    def has_irradiance(self) -> bool:
        """POA ışınım ölçümü var mı? (Kalibrasyon kalitesi için kritik.)"""
        return self.poa_irradiance is not None and self.poa_irradiance.notna().any()

    @property
    def hours_count(self) -> int:
        """Geçerli (NaN olmayan) saat sayısı."""
        return int(self.power_kw.notna().sum())

    def to_hourly(self) -> SCADAData:
        """Sub-saatlik veriyi saatlik ortalamaya indirir.

        Güç ortalama alınır, enerji toplanır.
        """
        if self.timestep_minutes >= 60:
            return self

        def resample_mean(s: pd.Series | None) -> pd.Series | None:
            return s.resample("1h").mean() if s is not None else None

        def resample_sum(s: pd.Series | None) -> pd.Series | None:
            return s.resample("1h").sum() if s is not None else None

        return SCADAData(
            power_kw=self.power_kw.resample("1h").mean(),
            energy_kwh=resample_sum(self.energy_kwh),
            poa_irradiance=resample_mean(self.poa_irradiance),
            temp_ambient=resample_mean(self.temp_ambient),
            temp_module=resample_mean(self.temp_module),
            wind_speed=resample_mean(self.wind_speed),
            plant_name=self.plant_name,
            timestep_minutes=60,
        )




    def to_dataframe(self) -> pd.DataFrame:
            """SCADAData'yi app.py'in bekledigi DataFrame formatina cevirir.

            Sutun adlari mevcut app.py adlandirma ile uyumlu:
            - timestamp (DatetimeIndex'ten gelir)
            - power_kw (zorunlu)
            - poa_global (opsiyonel, poa_irradiance'tan)
            - t_air (opsiyonel, temp_ambient'tan)

            Returns:
                DataFrame with timestamp column and standardized data columns.
            """
            df = pd.DataFrame({"power_kw": self.power_kw})
            df.index.name = "timestamp"
            df = df.reset_index()

            if self.poa_irradiance is not None:
                df["poa_global"] = self.poa_irradiance.values
            if self.temp_ambient is not None:
                df["t_air"] = self.temp_ambient.values

            return df

# -----------------------------------------------------------------------------
# Genel CSV okuyucusu
# -----------------------------------------------------------------------------

# CSV'lerdeki kolon isimlerinin standart isimlere eşlemesi
# Buraya zaman içinde başka servislerin formatları eklenir
logger = logging.getLogger(__name__)


COLUMN_ALIASES: dict[str, list[str]] = {
    "timestamp": [
        "timestamp", "time", "datetime", "date", "tarih", "zaman",
        "Time", "Date Time", "Tarih Saat",
    ],
    "power_kw": [
        "power_kw", "ac_power", "active_power", "p_ac",
        "AC Active Power(kW)", "Active Power(kW)",
        "Aktif Güç(kW)", "Üretim(kW)",
    ],
    "energy_kwh": [
        "energy_kwh", "ac_energy", "yield",
        "Energy(kWh)", "Yield(kWh)",
        "Üretim(kWh)", "Enerji(kWh)",
    ],
    "poa_irradiance": [
        "poa_irradiance", "irradiance", "ghi", "g_poa",
        "POA Irradiance(W/m2)", "Irradiance(W/m2)",
        "Işınım(W/m2)", "poa_irradiance_kwh_m2"],
    "temp_ambient": [
        "temp_ambient", "temp_air_c", "ambient_temp", "t_amb", "t_air",
        "Ambient Temperature(°C)", "Ambient(°C)",
        "Ortam Sıcaklığı(°C)",
    ],
    "temp_module": [
        "temp_module", "module_temp", "t_mod",
        "Module Temperature(°C)",
        "Modül Sıcaklığı(°C)",
    ],
    "wind_speed": [
        "wind_speed", "ws",
        "Wind Speed(m/s)",
        "Rüzgar(m/s)",
    ],
}


def _detect_column(df: pd.DataFrame, target: str) -> str | None:
    """DataFrame'de hedef alan için olası kolonu bulur.

    Önce tam eşleşme (case-insensitive) denenir. Bulunamazsa rapidfuzz ile
    fuzzy eşleşme yapılır; skor eşiği (85) üstündeki en iyi aday döndürülür.
    Bu, "AC Active Power(kW)" gibi biçim farklarını tolere eder.
    """
    aliases = COLUMN_ALIASES.get(target, [])
    cols_lower = {c.lower(): c for c in df.columns}

    # 1. Tam eşleşme (mevcut davranış, hızlı yol)
    for alias in aliases:
        if alias.lower() in cols_lower:
            return cols_lower[alias.lower()]

    # 2. Fuzzy fallback: her sütun için en yüksek alias skorunu hesapla,
    #    genel en yüksek skorlu sütunu seç (eşik 85)
    if not aliases or df.columns.empty:
        return None

    best_col: str | None = None
    best_score: float = 0.0
    for col in df.columns:
        # process.extractOne: alias listesinden en iyi eşleşmeyi bulur
        result = process.extractOne(
            col.lower(),
            [a.lower() for a in aliases],
            scorer=fuzz.WRatio,
        )
        if result is None:
            continue
        _matched_alias, score, _idx = result
        if score > best_score:
            best_score = score
            best_col = col

    if best_col is not None and best_score >= 85:
        logger.info(
            "Fuzzy match: '%s' -> '%s' (score=%.1f)",
            best_col, target, best_score,
        )
        return best_col

    return None


def _normalize_poa_units(poa: pd.Series | None) -> pd.Series | None:
    """POA irradiance birimini otomatik olarak W/m²'ye normalize et.

    Bazı SCADA sistemleri POA'yı kWh/m² (saatlik integral) olarak raporlar
    (tipik pik: 0.8-1.2). PVQuant motoru W/m² bekler (tipik pik: 800-1100).
    Pik değere bakarak birim tespiti yapıp gerekirse ×1000 dönüşümü uygular.

    Args:
        poa: Ham POA serisi veya None.

    Returns:
        W/m² birimine normalize edilmiş seri, None ise None.
    """
    if poa is None:
        return None
    max_val = poa.dropna().abs().max()
    if pd.isna(max_val):
        return poa
    # Pik < 10 → kWh/m² varsayımı (asla W/m² olmaz), ×1000 dönüştür
    if max_val < 10:
        return poa * 1000.0
    return poa


def _detect_timestep_minutes(index: pd.DatetimeIndex) -> int:
    """Veri zaman adımını tespit eder."""
    if len(index) < 2:
        return 60
    diffs = index.to_series().diff().dropna()
    median_delta = diffs.median()
    return int(median_delta.total_seconds() / 60)


def load_csv(
    path: str | Path,
    plant_name: str | None = None,
    timestamp_column: str | None = None,
    power_column: str | None = None,
    delimiter: str = ",",
    decimal: str = ".",
) -> SCADAData:
    """Genel CSV okuyucusu.

    Yaygın kolon isimlerini otomatik olarak algılar (Türkçe ve İngilizce).
    Kolonlar otomatik bulunamazsa açıkça `timestamp_column` ve `power_column`
    verilebilir.

    Args:
        path: CSV dosya yolu.
        plant_name: Santral adı (verilmezse dosya adından alınır).
        timestamp_column: Tarih-saat kolonunu manuel belirt.
        power_column: Güç kolonunu manuel belirt.
        delimiter: CSV ayracı (virgül, noktalı virgül).
        decimal: Ondalık ayracı (nokta veya virgül - TR Excel için).

    Returns:
        SCADAData nesnesi.

    Raises:
        ValueError: Zorunlu kolonlar bulunamazsa.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dosya yok: {path}")

    df = pd.read_csv(path, delimiter=delimiter, decimal=decimal)

    ts_col = timestamp_column or _detect_column(df, "timestamp")
    if not ts_col:
        raise ValueError(
            f"Zaman kolonu bulunamadı. Mevcut kolonlar: {list(df.columns)}. "
            "timestamp_column parametresi ile manuel belirtin."
        )

    pwr_col = power_column or _detect_column(df, "power_kw")
    if not pwr_col:
        raise ValueError(
            f"Güç kolonu bulunamadı. Mevcut kolonlar: {list(df.columns)}. "
            "power_column parametresi ile manuel belirtin."
        )

    # Zaman indeksini kur
    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    df = df.dropna(subset=[ts_col]).set_index(ts_col).sort_index()

    def col_or_none(target: str) -> pd.Series | None:
        col = _detect_column(df, target)
        return df[col] if col else None

    return SCADAData(
        power_kw=df[pwr_col].astype(float),
        energy_kwh=col_or_none("energy_kwh"),
        poa_irradiance=_normalize_poa_units(col_or_none("poa_irradiance")),
        temp_ambient=col_or_none("temp_ambient"),
        temp_module=col_or_none("temp_module"),
        wind_speed=col_or_none("wind_speed"),
        plant_name=plant_name or path.stem,
        timestep_minutes=_detect_timestep_minutes(df.index),
    )


def load_fusionsolar_csv(path: str | Path, plant_name: str | None = None) -> SCADAData:
    """FusionSolar (Huawei) export CSV okuyucusu.

    FusionSolar genelde Türkçe yerel ayarlarla virgül ondalık kullanır,
    fakat dosyalar sistemden sisteme değişebilir. Bu wrapper genel
    `load_csv`'yi çağırır; özel format farkları çıkarsa burada handle edilir.

    Args:
        path: CSV dosya yolu.
        plant_name: Santral adı.

    Returns:
        SCADAData nesnesi.
    """
    return load_csv(path, plant_name=plant_name, delimiter=",", decimal=".")
