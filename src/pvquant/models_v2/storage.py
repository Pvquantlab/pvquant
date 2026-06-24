"""
PVQuant - Calibration Storage
=============================

Kalibre edilmiş model katsayılarının kalıcı saklanması.

Phase 1: JSON dosyaları (yerel disk)
Phase 3: PostgreSQL (drop-in replacement)

Kullanım:
    storage = JsonCalibrationStorage(base_dir="./calibration_cache")
    storage.save(plant_id="merkas", model_name="barhdadi_bennis", params=...)
    params = storage.load(plant_id="merkas", model_name="barhdadi_bennis")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from .contracts import CalibrationParams


# ============================================================
# Storage Protocol (soyut sözleşme)
# ============================================================

@runtime_checkable
class CalibrationStorage(Protocol):
    """
    Kalibrasyon kayıtlarının saklandığı yerin soyutlaması.

    Phase 1: JsonCalibrationStorage (dosya tabanlı)
    Phase 3: PostgresCalibrationStorage (DB tabanlı)

    İkisi de aynı sözleşmeye uyduğu için, model kodu hangi backend
    olduğunu bilmek zorunda değil.
    """

    def save(
        self,
        plant_id: str,
        model_name: str,
        params: CalibrationParams,
    ) -> None:
        """Kalibrasyon parametrelerini kaydet."""
        ...

    def load(
        self,
        plant_id: str,
        model_name: str,
    ) -> Optional[CalibrationParams]:
        """
        Kayıtlı parametreleri yükle.
        Kayıt yoksa None döner (hata fırlatmaz).
        """
        ...

    def exists(self, plant_id: str, model_name: str) -> bool:
        """Kayıt var mı diye kontrol et."""
        ...

    def delete(self, plant_id: str, model_name: str) -> bool:
        """
        Kaydı sil. Silindiyse True, yoktuysa False döner.
        Genelde recalibration veya test için kullanılır.
        """
        ...


# ============================================================
# JSON tabanlı implementation
# ============================================================

class JsonCalibrationStorage:
    """
    JSON dosyaları üzerinde kalibrasyon saklama.

    Dosya yolu: {base_dir}/{plant_id}_{model_name}.json

    Örnek: calibration_cache/merkas_barhdadi_bennis.json
    """

    def __init__(self, base_dir: str | Path = "./calibration_cache"):
        """
        Args:
            base_dir: Kayıt dosyalarının tutulacağı klasör.
                      Yoksa otomatik oluşturulur.
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, plant_id: str, model_name: str) -> Path:
        """Bir kayıt için dosya yolunu hesapla."""
        # Güvenlik: plant_id ve model_name'de yol karakterleri olmasın
        safe_plant = plant_id.replace("/", "_").replace("\\", "_")
        safe_model = model_name.replace("/", "_").replace("\\", "_")
        return self.base_dir / f"{safe_plant}_{safe_model}.json"

    def save(
        self,
        plant_id: str,
        model_name: str,
        params: CalibrationParams,
    ) -> None:
        """Parametreleri JSON dosyasına yaz."""
        path = self._file_path(plant_id, model_name)
        # Pydantic v2: model_dump_json kullanır
        path.write_text(params.model_dump_json(indent=2), encoding="utf-8")

    def load(
        self,
        plant_id: str,
        model_name: str,
    ) -> Optional[CalibrationParams]:
        """
        JSON dosyasından parametreleri oku.
        Dosya yoksa None döner.
        """
        path = self._file_path(plant_id, model_name)
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8")
        return CalibrationParams.model_validate_json(raw)

    def exists(self, plant_id: str, model_name: str) -> bool:
        """Dosya var mı?"""
        return self._file_path(plant_id, model_name).exists()

    def delete(self, plant_id: str, model_name: str) -> bool:
        """Dosyayı sil. Sildiyse True, zaten yoktuysa False."""
        path = self._file_path(plant_id, model_name)
        if path.exists():
            path.unlink()
            return True
        return False