"""v2.572 (Faz 1 F1-A) — çalışan yazılımın sürüm damgası.

İmaj kurulurken compose `PVQ_SURUM` kurma argümanını (`git describe --always`) ortama yazar; koşu künyesine
(`forecast_runs.yazilim_surumu`) ve doğrulama metasına bu değer girer. Tanımlı değilse None: sayı/sürüm uydurulmaz.
"""
from __future__ import annotations

import os


def yazilim_surumu() -> str | None:
    v = (os.environ.get("PVQ_SURUM") or "").strip()
    return v[:64] or None
