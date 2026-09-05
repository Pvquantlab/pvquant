"""Open-Meteo Forecast API istemcisi.

Open-Meteo, anahtar gerektirmeyen ve günlük 10.000 ücretsiz çağrı sunan
açık bir meteoroloji servisidir. Güneş enerjisi modellemesi için gereken
GHI, sıcaklık, rüzgar gibi tüm değişkenleri sağlar.

API dokümantasyonu: https://open-meteo.com/en/docs

Kullanım:
    >>> from pvquant.io.meteo import OpenMeteoClient
    >>> client = OpenMeteoClient()
    >>> df = client.get_forecast(latitude=37.87, longitude=32.49, days=7)
    >>> df.columns
    Index(['ghi', 'temp_air', 'wind_speed_10m', ...], dtype='object')
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx
import pandas as pd

from pvquant.config import get_settings


@dataclass(frozen=True)
class MeteoData:
    """Meteorolojik veri konteyneri.

    Tüm seriler aynı zaman indeksini paylaşır (saatlik, UTC).

    Attributes:
        ghi: Yatay küresel ışınım, W/m².
        temp_air: 2m hava sıcaklığı, °C.
        wind_speed_10m: 10m yüksekliğinde rüzgar hızı, m/s.
        relative_humidity: Bağıl nem, % (opsiyonel).
        cloud_cover: Bulutluluk, % (opsiyonel).
        latitude: Sorgulanan enlem.
        longitude: Sorgulanan boylam.
        timezone: API'nin döndürdüğü zaman dilimi (genelde 'UTC').
    """

    ghi: pd.Series
    temp_air: pd.Series
    wind_speed_10m: pd.Series
    relative_humidity: pd.Series | None
    cloud_cover: pd.Series | None
    latitude: float
    longitude: float
    timezone: str
    precipitation: pd.Series | None = None   # v2.256 mm/saat
    snowfall: pd.Series | None = None        # v2.256 cm/saat

    def to_dataframe(self) -> pd.DataFrame:
        """Tüm seriler tek bir DataFrame'de döner."""
        data: dict[str, pd.Series] = {
            "ghi": self.ghi,
            "temp_air": self.temp_air,
            "wind_speed_10m": self.wind_speed_10m,
        }
        if self.relative_humidity is not None:
            data["relative_humidity"] = self.relative_humidity
        if self.cloud_cover is not None:
            data["cloud_cover"] = self.cloud_cover
        if self.precipitation is not None:
            data["precipitation"] = self.precipitation
        if self.snowfall is not None:
            data["snowfall"] = self.snowfall
        return pd.DataFrame(data)


class OpenMeteoError(Exception):
    """Open-Meteo API hatası."""


class OpenMeteoClient:
    """Open-Meteo Forecast API istemcisi.

    Args:
        base_url: API kök adresi. Varsayılan yapılandırmadan okur.
        timeout: HTTP timeout, saniye.
    """

    # PVQuant için gerekli olan saatlik değişkenler
    # https://open-meteo.com/en/docs#hourly_variables
    HOURLY_VARS: tuple[str, ...] = (
        "shortwave_radiation",      # GHI, W/m²
        "temperature_2m",            # °C
        "wind_speed_10m",           # m/s
        "relative_humidity_2m",      # %
        "cloud_cover",              # %
        "direct_radiation",         # DNI'ye yakın, doğrulama için
        "diffuse_radiation",        # DHI'ye yakın, doğrulama için
        "precipitation",            # v2.256: mm/saat — kirlenme (Kimber) temizleme yağışı
        "snowfall",                 # v2.256: cm/saat — kar örtüsü (NREL)
    )


    # B7 (v2.165): istekte models= parametresi GONDERILMIYOR -> Open-Meteo
    # "best_match" kipinde kosar. Damganin tek kaynagi bu sabit; models=
    # parametresi eklenirse burasi da birlikte guncellenmeli.
    NWP_MODEL: str = "best_match"

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.meteo_base_url
        self.timeout = timeout or settings.meteo_timeout

    def _istekle(self, client: "httpx.Client", url: str, params: dict) -> "httpx.Response":
        """B-19 (Kutu 13): 3 deneme, artan bekleme. Yalniz GECICI hatalarda
        tekrar: 429, 5xx, ag kopmasi. Diger 4xx (kalici) aninda firlar."""
        import time
        from pvquant.config import get_settings as _gs
        _cfg = _gs()
        son_hata: Exception | None = None
        for deneme in range(_cfg.meteo_retry_attempts):
            try:
                r = client.get(url, params=params)
                r.raise_for_status()
                return r
            except httpx.HTTPStatusError as e:
                kod = e.response.status_code
                if kod != 429 and kod < 500:
                    raise                       # kalici 4xx — beklemek anlamsiz
                son_hata = e
            except httpx.RequestError as e:
                son_hata = e                    # ag kopmasi — gecici sayilir
            if deneme < _cfg.meteo_retry_attempts - 1:
                time.sleep(_cfg.meteo_retry_base_seconds * (3 ** deneme))
        raise son_hata  # denemeler bitti; mevcut except bloklari yakalar

    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        timezone: str = "UTC",
        past_days: int = 0,
    ) -> MeteoData:
        """Verilen koordinat için saatlik 7 günlük forecast getirir.
        v2.253: past_days (0–92) verilirse aynı modelin GEÇMİŞ günleri de döner —
        eğitim/servis kayma denetiminin 'servis tarafı' örneği (tahmin modelinin
        kısa ufuklu çıktısı; arşiv/analiz DEĞİL).

        Args:
            latitude: Enlem, derece (-90 ila 90).
            longitude: Boylam, derece (-180 ila 180).
            days: Forecast gün sayısı (1-16 arası, Open-Meteo limiti).
            timezone: Sonuçların döndürüleceği zaman dilimi.
                'UTC' veya 'auto' (koordinata göre) veya 'Europe/Istanbul' gibi.

        Returns:
            MeteoData nesnesi.

        Raises:
            OpenMeteoError: API'den hata dönerse veya bağlantı problemi olursa.
        """
        if not -90 <= latitude <= 90:
            raise ValueError(f"latitude {latitude} aralık dışı (-90..90)")
        if not -180 <= longitude <= 180:
            raise ValueError(f"longitude {longitude} aralık dışı (-180..180)")
        if not 1 <= days <= 16:
            raise ValueError(f"days {days} aralık dışı (1..16)")

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(self.HOURLY_VARS),
            "forecast_days": days,
            "timezone": timezone,
        }
        if not 0 <= past_days <= 92:
            raise ValueError(f"past_days {past_days} aralık dışı (0..92)")
        if past_days:
            params["past_days"] = past_days   # v2.253: kayma denetimi (servis tarafı örneği)

        url = f"{self.base_url}/forecast"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = self._istekle(client, url, params)   # B-19
                data = response.json()
        except httpx.HTTPStatusError as e:
            raise OpenMeteoError(f"API hata: {e.response.status_code} {e.response.text}") from e
        except httpx.RequestError as e:
            raise OpenMeteoError(f"Bağlantı hatası: {e}") from e

        return self._parse_response(data)

    def get_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        timezone: str = "UTC",
    ) -> MeteoData:
        """Tarihsel arşiv verisi getirir.

        Open-Meteo'nun ücretsiz arşiv API'sine başvurur. Forecast'ten farklı
        bir URL kullanır.

        Args:
            latitude: Enlem.
            longitude: Boylam.
            start_date: 'YYYY-MM-DD' formatında başlangıç.
            end_date: 'YYYY-MM-DD' formatında bitiş.
            timezone: Zaman dilimi.

        Returns:
            MeteoData nesnesi.
        """
        # Arşiv API'si farklı domain'de
        archive_url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(self.HOURLY_VARS),
            "timezone": timezone,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = self._istekle(client, archive_url, params)   # B-19
                data = response.json()
        except httpx.HTTPStatusError as e:
            raise OpenMeteoError(f"Arşiv API hata: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise OpenMeteoError(f"Bağlantı hatası: {e}") from e

        return self._parse_response(data)

    def _parse_response(self, data: dict) -> MeteoData:
        """API JSON yanıtını MeteoData'ya dönüştürür."""
        hourly = data.get("hourly", {})
        times_raw = hourly.get("time", [])
        if not times_raw:
            raise OpenMeteoError("API yanıtında saatlik veri bulunamadı")

        times = pd.to_datetime(times_raw)

        # --- Faz 1.7: DST duplicate cleanup ---
        # Open-Meteo DST gecis gunlerinde bazen ayni timestamp'i iki kez donduruyor
        # (orn: 2024-03-10 03:00:00 iki kez). Duplicate'lari temizle.
        if times.duplicated().any():
            # times bir DatetimeIndex, series olusturup mask uygulayacagiz
            dup_mask = ~pd.Series(times).duplicated().values
            times = times[dup_mask]
            # Ilgili hourly veri kolonlarini da ayni maske ile filtrele
            for k, v in list(hourly.items()):
                if k == "time":
                    hourly[k] = [t for i, t in enumerate(times_raw) if dup_mask[i]]
                elif isinstance(v, list):
                    hourly[k] = [x for i, x in enumerate(v) if dup_mask[i]]

        # --- Faz 1.7: tz-aware localize ---
        # Open-Meteo timestamp'leri belirtilen timezone'da (yerel saat) donuyor
        # ama tz bilgisi olmadan. pvlib.solarposition tz-aware bekliyor,
        # aksi halde UTC varsayip solar geometry hesabini bozuyor.
        response_tz = data.get("timezone", "UTC")
        if times.tz is None:
            try:
                times = times.tz_localize(response_tz, ambiguous="infer", nonexistent="shift_forward")
            except Exception:
                # DST bilinmezliginden kacinmak icin fallback: UTC olarak varsay
                times = times.tz_localize("UTC")

        def series_or_none(key: str) -> pd.Series | None:
            values = hourly.get(key)
            if values is None:
                return None
            return pd.Series(values, index=times, name=key)

        ghi = series_or_none("shortwave_radiation")
        temp_air = series_or_none("temperature_2m")
        wind_speed = series_or_none("wind_speed_10m")

        if ghi is None or temp_air is None or wind_speed is None:
            raise OpenMeteoError("Zorunlu değişkenlerden biri eksik (GHI/T/WS)")

        return MeteoData(
            ghi=ghi,
            temp_air=temp_air,
            wind_speed_10m=wind_speed,
            relative_humidity=series_or_none("relative_humidity_2m"),
            cloud_cover=series_or_none("cloud_cover"),
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            timezone=data.get("timezone", "UTC"),
            precipitation=series_or_none("precipitation"),
            snowfall=series_or_none("snowfall"),
        )
