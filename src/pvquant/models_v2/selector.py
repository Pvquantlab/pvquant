"""
PVQuant - Model Selector
========================

Santral profiline ve veri durumuna göre otomatik model seçimi.

Karar matrisi (PVQuant_Global_Strategy_v2.0.docx §3.3):
  - Bifacial panel → barhdadi_bennis
  - Mono, < 300 kWp → pvwatts
  - Mono, >= 300 kWp → sapm

Operasyon modu:
  - 3+ ay SCADA verisi varsa → calibrated
  - Yoksa → pure_forecast
"""

from __future__ import annotations

from typing import Literal

from .contracts import PlantProfile
from .protocol import PVModel
from .registry import ModelRegistry


# ============================================================
# Eşikler ve sabitler
# ============================================================

MINI_CAPACITY_THRESHOLD_KWP = 300  # Bunun altı "mini", üstü "medium/large"
MIN_SCADA_MONTHS_FOR_CALIBRATION = 3
MIN_VALID_HOURS_FOR_CALIBRATION = 1500


# ============================================================
# Hatalar
# ============================================================

class NoSuitableModelError(Exception):
    """Santral profili için uygun model bulunamadığında."""
    pass


# ============================================================
# Selector
# ============================================================

class ModelSelector:
    """
    Santral profili → uygun model + operasyon modu eşleştirmesi.

    İki ana karar verir:
      1. Hangi model? (panel tipi + kapasiteye göre)
      2. Hangi mod? (SCADA durumuna göre)
    """

    @staticmethod
    def select_model_name(plant: PlantProfile) -> str:
        """
        Karar matrisini uygula, model adını döner.

        Args:
            plant: Santral profili

        Returns:
            Registry'de kayıtlı model adı, örn: "barhdadi_bennis"

        Raises:
            NoSuitableModelError: Hiçbir model uymuyorsa
        """
        panel_tech = plant.panel.technology
        capacity = plant.dc_capacity_kwp

        # Bifacial → her zaman Barhdadi-Bennis
        if panel_tech == "bifacial":
            return "barhdadi_bennis"

        # Mono → kapasiteye göre
        if panel_tech == "mono":
            if capacity < MINI_CAPACITY_THRESHOLD_KWP:
                return "pvwatts"
            else:
                return "sapm"

        # Thin film → henüz desteklemiyoruz (Phase 4+)
        if panel_tech == "thin_film":
            raise NoSuitableModelError(
                f"İnce film paneller henüz desteklenmiyor "
                f"(plant_id={plant.plant_id}). Roadmap: Phase 4+."
            )

        # Beklenmeyen değer
        raise NoSuitableModelError(
            f"Bilinmeyen panel teknolojisi: '{panel_tech}' "
            f"(plant_id={plant.plant_id})"
        )

    @staticmethod
    def select_operation_mode(
        has_sufficient_scada: bool,
    ) -> Literal["pure_forecast", "calibrated"]:
        """
        SCADA durumuna göre operasyon modu seç.

        Args:
            has_sufficient_scada: 3+ ay ve 1500+ valid saat varsa True

        Returns:
            "calibrated" veya "pure_forecast"
        """
        return "calibrated" if has_sufficient_scada else "pure_forecast"

    @classmethod
    def create_model(
        cls,
        plant: PlantProfile,
    ) -> PVModel:
        """
        Tam pipeline: karar mat. → registry → instantiate.

        Args:
            plant: Santral profili

        Returns:
            Hazır model örneği (henüz kalibre değil)

        Raises:
            NoSuitableModelError: Hiçbir model uymuyorsa
            ModelNotFoundError: Karar matrisi modeli seçti ama
                                registry'de yok (kayıt eksik)
        """
        model_name = cls.select_model_name(plant)
        model_class = ModelRegistry.get(model_name)
        return model_class(plant=plant)