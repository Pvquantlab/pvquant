"""Uygulama yapılandırması.

Tüm yapılandırma çevre değişkenlerinden (.env) okunur. Bu sayede kod
test/staging/production ortamlarında değişmeden çalışır.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """PVQuant ana yapılandırma sınıfı.

    Çevre değişkenleri `PVQUANT_` ön ekiyle başlar.
    Örn: `PVQUANT_API_PORT=8000`.
    """

    model_config = SettingsConfigDict(
        env_prefix="PVQUANT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----- Uygulama -----
    env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ----- API -----
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # ----- Open-Meteo -----
    meteo_base_url: str = "https://api.open-meteo.com/v1"
    meteo_timeout: int = 30

    # ----- Cache -----
    cache_ttl_seconds: int = 3600

    # ----- Kapi ve bekci esikleri (v2.53 — Sozlesme 9) -----
    gate_wmape_ceiling: float = 25.0        # hibrit mutlak taban (birincil, WMAPE)
    gate_mape_ceiling: float = 35.0         # eski MAPE tavani — yedek yol
    gate_min_improvement_pct: float = 3.0   # goreli kapi esigi
    guard_capacity_tolerance: float = 0.20  # v2.41 kapasite-celiski bekcisi
    min_valid_hours_calibration: int = 1500 # Mod B icin asgari saglam saat
    skill_naive_ratio_clip: float = 4.0     # v2.55: berrak-gok orani kelepcesi
    worker_hour_skill: int = 0              # v2.56: gece skill (UTC, dakika 30)
    worker_hour_forecast: int = 2           # v2.56: sabah tahmin (UTC)
    worker_hour_alarm: int = 4              # v2.56: alarm taramasi (UTC)
    worker_day_calibration: int = 1         # v2.56: aylik kalibrasyon gunu
    worker_hour_calibration: int = 3        # v2.56: aylik kalibrasyon saati (UTC)
    forecast_horizon_days: int = 16         # v2.69: Kitap KUTU-2 / Kilavuz Adim-5 (16g, 384 saat)
    meteo_retry_attempts: int = 3           # B-19: gecici hatada deneme sayisi
    meteo_retry_base_seconds: float = 2.0   # B-19: bekleme tabani (2,6,18 sn)
    quantile_coverage_target_pct: float = 80.0  # v2.57: P10-P90 gunduz kapsama hedefi
    guard_stale_data_years: float = 3.0     # v2.59: tum damgalar bundan eskiyse uyar
    guard_future_days: float = 2.0          # v2.59: damgalar gelecekteyse uyar

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS origins virgülle ayrılmış stringi listeye çevirir."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Yapılandırmayı tek seferlik yükler ve önbelleğe alır.

    FastAPI bağımlılık enjeksiyonunda kullanılır:
        ```python
        @app.get("/")
        def root(settings: Settings = Depends(get_settings)):
            ...
        ```
    """
    return Settings()
