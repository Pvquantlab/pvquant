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
