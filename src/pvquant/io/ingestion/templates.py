"""Vendor/kullanıcı şablonları.

Bir ingestion başarıyla onaylandığında kararları (format + eşleme +
dönüşüm) JSON şablon olarak saklanır. Sonraki yüklemelerde:

  1. Kayıtlı şablonlar sırayla denenir; kolonları birebir karşılayan
     ilk şablon otomatik uygulanır (kullanıcıya 'X şablonu kullanıldı'
     bilgisi gösterilir).
  2. Hiçbiri uymazsa otomatik algılama/eşleme devreye girer.

Depo, calibration_cache ile aynı desendedir: dosya sistemi + JSON.
İleride DB'ye taşımak isterseniz yalnızca bu modül değişir.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .contracts import ColumnMapping, FileFormat, TransformSpec


class TemplateStore:
    """JSON tabanlı ingestion şablon deposu."""

    def __init__(self, directory: str | Path = "ingestion_templates") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, template: dict) -> Path:
        """Şablonu kaydeder. `template` = IngestionResult.to_template()."""
        payload = dict(template)
        payload["_meta"] = {
            "name": name,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
        }
        path = self.directory / f"{_slug(name)}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                        encoding="utf-8")
        return path

    def load(self, name: str) -> dict | None:
        path = self.directory / f"{_slug(name)}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_templates(self) -> list[str]:
        return sorted(p.stem for p in self.directory.glob("*.json"))

    def find_matching(self, columns: list[str]) -> tuple[str, dict] | None:
        """Kolon setini birebir karşılayan ilk şablonu döner.

        'Karşılamak': şablonun eşlediği her kaynak kolon, dosyada
        mevcut olmalı. (Dosyada fazladan kolon olması sorun değil.)
        """
        colset = set(map(str, columns))
        for name in self.list_templates():
            tpl = self.load(name)
            if tpl is None:
                continue
            mapped = [v for k, v in tpl.get("mapping", {}).items()
                      if isinstance(v, str) and k != "confidence"]
            if mapped and set(mapped) <= colset:
                return name, tpl
        return None

    @staticmethod
    def parse(template: dict) -> tuple[FileFormat, ColumnMapping, TransformSpec]:
        """JSON şablonu dataclass'lara açar."""
        ff = FileFormat(**{k: v for k, v in template["file_format"].items()})
        mp_raw = dict(template["mapping"])
        mp_raw.setdefault("confidence", {})
        mp = ColumnMapping(**mp_raw)
        ts = TransformSpec(**template["transform"])
        return ff, mp, ts


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:80]