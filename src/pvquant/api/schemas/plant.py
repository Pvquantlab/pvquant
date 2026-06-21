"""Santral spec için Pydantic şeması."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from pvquant.pipeline.forecast import PlantSpec


class PlantSpecSchema(BaseModel):
    """Santral teknik özellikleri (API girişi).

    PlantSpec dataclass'ının Pydantic karşılığı. API request/response için
    serileştirme/doğrulama yapar.
    """

    p_nom_kwp: float = Field(..., gt=0, description="DC nominal güç, kWp")
    latitude: float = Field(..., ge=-90, le=90, description="Enlem")
    longitude: float = Field(..., ge=-180, le=180, description="Boylam")
    tilt: float = Field(30.0, ge=0, le=90, description="Modül eğimi, derece")
    azimuth: float = Field(180.0, ge=0, le=360, description="Modül azimutu (180=güney)")
    module_tech: Literal[
        "mono_si", "multi_si", "topcon", "hjt", "a_si", "cdte", "cigs"
    ] = "mono_si"
    gamma_pdc: float | None = Field(
        None, description="Sıcaklık katsayısı override (None=teknolojiden)"
    )
    noct: float = Field(45.0, gt=0, le=80, description="NOCT, °C")
    bifacial_factor: float = Field(
        0.0, ge=0, le=1, description="BF (0=monofacial, 0.70=tipik bifacial)"
    )
    bifacial_gain_geometric: float = Field(
        0.347, ge=0, le=1, description="BG (geometrik arka yüz oranı)"
    )
    albedo: float = Field(0.25, ge=0, le=1, description="Saha albedosu")
    eta_bos: float = Field(0.93, gt=0, le=1, description="BoS verimi")
    eta_inv: float = Field(0.97, gt=0, le=1, description="Inverter verimi")
    p_ac_clip_kw: float | None = Field(None, gt=0, description="AC clip limiti, kW")
    altitude_m: float = Field(0.0, ge=0, description="Rakım, m")
    module_height_m: float = Field(2.0, gt=0, description="Modül yüksekliği, m")
    thermal_model: Literal["noct", "faiman"] = "faiman"
    power_model: Literal["barhdadi_bennis", "pvwatts", "skoplaki_palyvos"] = "barhdadi_bennis"

    def to_dataclass(self) -> PlantSpec:
        """Pydantic modeli → dataclass."""
        return PlantSpec(**self.model_dump())

    @classmethod
    def from_dataclass(cls, plant: PlantSpec) -> PlantSpecSchema:
        """dataclass → Pydantic modeli."""
        return cls(**{f: getattr(plant, f) for f in cls.model_fields})

    model_config = {
        "json_schema_extra": {
            "example": {
                "p_nom_kwp": 5000.0,
                "latitude": 37.87,
                "longitude": 32.49,
                "tilt": 30,
                "azimuth": 180,
                "module_tech": "topcon",
                "bifacial_factor": 0.70,
                "bifacial_gain_geometric": 0.347,
                "albedo": 0.25,
                "eta_bos": 0.93,
                "thermal_model": "faiman",
                "power_model": "barhdadi_bennis",
            }
        }
    }
