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

    # ----- Meteoroloji kaynağı (v2.268, Dalga 0) -----
    # 'acik' (varsayılan): ECMWF Open Data IFS + DWD ICON-EU (CC BY 4.0) — koşu arşivi meteo_arsiv tablosunda.
    # 'open_meteo': eski ücretsiz katman — ticari kullanımda uyumluluk borcu; yalnız geliştirme/geriye dönük kıyas.
    meteo_kaynak: Literal["acik", "open_meteo"] = "acik"
    nwp_dizin: str = "var/nwp"              # GRIB önbelleği (worker ./var bağlı hacmi); arşiv DB'de
    nwp_kosu_tut: int = 2                   # kaynak başına diskte tutulan koşu sayısı
    cams_email: str | None = None           # v2.269: CAMS Radiation (SoDa) kayıtlı e-posta — kalibrasyon geçmişi için
    # v2.273 (Dalga 2, ★): P10–P90 bandının kaynağı — 'otomatik': taze GEFS üyeleri (≥ensemble_min_uye) varsa üye başına
    # fizik koşusundan ampirik kantil, yoksa model bandı; 'model': eski yol; 'ensemble': üye yoksa bant yok (None).
    bant_kaynagi: Literal["otomatik", "model", "ensemble"] = "otomatik"
    ensemble_min_uye: int = 20
    # v2.274 (Dalga 2, ★): trend/sapma düzeltme katmanı — 'otomatik' (taze SCADA + anlamlı sapma varsa) | 'kapali'
    sapma_katmani: Literal["otomatik", "kapali"] = "otomatik"
    # ----- Open-Meteo (yalnız meteo_kaynak='open_meteo') -----
    meteo_base_url: str = "https://api.open-meteo.com/v1"
    meteo_timeout: int = 30

    # ----- Cache -----
    cache_ttl_seconds: int = 3600

    # ----- Rapor künyesi (v2.195) -----
    # s16 "İletişim" satırı — OPERATÖR (rapor üreticisi) adresidir, kiracıya
    # göre değişmez (kullanıcı kararı). Boşsa rapor dürüst "—" basar (kural 3).
    rapor_iletisim: str = ""

    # ----- Kapi ve bekci esikleri (v2.53 — Sozlesme 9) -----
    gate_wmape_ceiling: float = 25.0        # hibrit mutlak taban (birincil, WMAPE)
    gate_mape_ceiling: float = 35.0         # eski MAPE tavani — yedek yol
    gate_min_improvement_pct: float = 3.0   # goreli kapi esigi
    guard_capacity_tolerance: float = 0.20  # v2.41 kapasite-celiski bekcisi
    min_valid_hours_calibration: int = 1500 # Mod B icin asgari saglam saat
    skill_naive_ratio_clip: float = 4.0     # v2.55: berrak-gok orani kelepcesi
    # v2.255 (Dalga 3.10, ★): rezidüel modelin gök açıklığı endeksi referansı — 'toa' (atmosfer üstü,
    # eski/varsayılan) ya da 'ineichen' (açık gök modeli: kt bulutluluğu daha temiz ölçer). DİKKAT:
    # eğitim ve servis AYNI ayarla çalışmalı; değiştirmek YENİDEN KALİBRASYON gerektirir (ml_models eski kt ile eğitildi).
    kt_referans: str = "toa"
    # v2.258 (Dalga 4.14): EPİAŞ Şeffaflık kimliği (PVQUANT_EPIAS_KULLANICI / PVQUANT_EPIAS_SIFRE). Yoksa
    # fiyatlar 'senaryo' (EPDK 2025 yıllık ortalamaları) — UI bunu açıkça söyler. Şifre asla loglanmaz.
    epias_kullanici: str | None = None
    epias_sifre: str | None = None
    # C-3b (v2.152): s08 butunluk kurallarinin makine esikleri — worker ve
    # servis TEK kaynaktan okur. reporting/html/veri.py KARNE_ESIK aynasidir
    # (rapor katmani bagimsizdir; sapma D19/D20 verisinde yakalanir).
    karne_kapsama_esik_pct: int = 60        # gun ici gecerli saat orani tabani
    karne_kucuk_orneklem_gun: int = 14      # pencerede asgari gecerli gun
    karne_gunduz_bas: int = 6               # gun ici tanimi: yerel 06–19
    karne_gunduz_son: int = 19              # (B5 mae penceresiyle ayni, 14 saat)
    worker_hour_skill: int = 0              # v2.56: gece skill (UTC, dakika 30)
    worker_hour_forecast: int = 2           # v2.56: sabah tahmin (UTC)
    worker_hour_alarm: int = 4              # v2.56: alarm taramasi (UTC)
    worker_day_calibration: int = 1         # v2.56: aylik kalibrasyon gunu
    worker_hour_calibration: int = 3        # v2.56: aylik kalibrasyon saati (UTC)
    forecast_horizon_days: int = 15         # v2.156 (kullanıcı kararı 18 Ağu):
                                            # open-meteo RADYASYON ufku ~15 gündür;
                                            # 16. gün NaN dönüyor ve eski fillna(0)
                                            # onu 'üretim 0' yalanına çeviriyordu.
                                            # Vaat gerçeğe çekildi (eski: v2.69
                                            # KUTU-2 16g/384s); Kitap KUTU-2
                                            # kaydı 15g/360s (18 Ağu 2026).
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
