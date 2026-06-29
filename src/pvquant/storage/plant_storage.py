"""
Plant + Calibration persistence (JSON tabanli).

Format:
{
  "plant_id": "GUNES_TARLA_1",
  "saved_at": "2026-06-29T17:15:00",
  "profile": { ...PlantProfile JSON... },
  "calibration": {
    "params": { "bg": 0.05, "eta_bos": 0.99 },
    "metrics": { "yillik_sapma_pct": -3.82, ... },
    "calibrated_at": "2026-06-29T17:10:00"
  }
}

calibration alani None olabilir (kalibrasyon yapilmadiysa).
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Saklama klasoru - repo koku altinda data/santraller/
# Bu klasor .gitignore'da, GitHub'a sizmaz.
STORAGE_DIR = Path(__file__).resolve().parents[3] / "data" / "santraller"


def _safe_plant_id(plant_id: str) -> str:
    """Dosya adi olarak guvenli hale getir: bosluk, slash, vb. temizle."""
    # Sadece harf, rakam, alt cizgi, tire birak
    safe = re.sub(r"[^A-Za-z0-9_\-]", "_", plant_id.strip())
    if not safe:
        raise ValueError(f"Gecersiz plant_id: {plant_id!r}")
    return safe


def _file_path(plant_id: str) -> Path:
    """Bir santralin JSON dosya yolunu hesapla."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return STORAGE_DIR / f"{_safe_plant_id(plant_id)}.json"


def save_plant(
    plant_id: str,
    profile: Any,
    calibration: Optional[dict] = None,
) -> Path:
    """
    Santral profilini (ve varsa kalibrasyon sonuclarini) JSON'a yaz.

    Args:
        plant_id: Santralin unique ID'si (ornek: "GUNES_TARLA_1").
        profile: PlantProfile Pydantic objesi VEYA dict.
        calibration: Opsiyonel kalibrasyon sonuclari.
            {
                "params": {"bg": ..., "eta_bos": ...},
                "metrics": {"yillik_sapma_pct": ..., ...},
                "calibrated_at": "ISO timestamp"
            }

    Returns:
        Yazilan dosyanin yolu.
    """
    # Profile Pydantic objesiyse dict'e cevir
    if hasattr(profile, "model_dump"):
        profile_dict = profile.model_dump(mode="json")
    elif isinstance(profile, dict):
        profile_dict = profile
    else:
        raise TypeError(f"profile Pydantic veya dict olmali, {type(profile)} aldim")

    # Eger dosya zaten varsa, eski kalibrasyonu koruyabiliriz
    # (kullanici sadece profili guncellediyse)
    path = _file_path(plant_id)
    existing_calibration = None
    if path.exists() and calibration is None:
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            existing_calibration = existing.get("calibration")
        except (json.JSONDecodeError, KeyError):
            pass

    data = {
        "plant_id": plant_id,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "profile": profile_dict,
        "calibration": calibration if calibration is not None else existing_calibration,
    }

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def load_plant(plant_id: str) -> Optional[dict]:
    """
    Santral kaydini JSON'dan oku.

    Returns:
        Dict (yukaridaki format) veya None (kayit yoksa).
    """
    path = _file_path(plant_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        # Bozuk dosya - sessizce None donme yerine error logla, None don
        print(f"[storage] Bozuk JSON: {path} - {e}")
        return None


def list_plants() -> list[dict]:
    """
    Kayitli tum santrallerin ozetini dondur.

    Returns:
        [
            {
                "plant_id": "GUNES_TARLA_1",
                "saved_at": "...",
                "has_calibration": True,
                "yillik_sapma_pct": -3.82  # varsa
            },
            ...
        ]
        Saved_at azalan siralama (en yenisi ustte).
    """
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    for f in STORAGE_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        cal = data.get("calibration")
        summary = {
            "plant_id": data.get("plant_id", f.stem),
            "saved_at": data.get("saved_at", ""),
            "has_calibration": cal is not None,
            "yillik_sapma_pct": (
                cal.get("metrics", {}).get("yillik_sapma_pct") if cal else None
            ),
            "capacity_kwp": data.get("profile", {}).get("dc_capacity_kwp"),
            "panel_tech": data.get("profile", {}).get("panel", {}).get("technology"),
        }
        summaries.append(summary)

    # En yeniyi ustte goster
    summaries.sort(key=lambda s: s["saved_at"], reverse=True)
    return summaries


def delete_plant(plant_id: str) -> bool:
    """
    Santral kaydini sil.

    Returns:
        True: silindi
        False: zaten yoktu
    """
    path = _file_path(plant_id)
    if path.exists():
        path.unlink()
        return True
    return False
