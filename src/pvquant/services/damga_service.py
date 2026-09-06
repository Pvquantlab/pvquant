"""v2.265 — Dalga 5.17: değişim damgası — 'panelde bir şey değişti mi?' sorusuna tek ucuz yanıt.

Kaynak DB (süreç içi bellek değil: API çok kopyalı olabilir, worker ayrı süreçtir). Beş zaman damgası okunur;
ETag = sha256(bunlar)[:16]. İstemci 60 s (görünür) / 5 dk (arka plan) yoklar, yalnız ETag değişince veri çeker.
Telemetri şeridindeki 'tazelendi' iddiası ANCAK bu yoklama gerçekten çalışırken yazılır (dürüstlük ilkesi).
"""
from __future__ import annotations

import hashlib
import json


def etag_uret(damga: dict) -> str:
    return 'W/"' + hashlib.sha256(json.dumps(damga, sort_keys=True, default=str).encode()).hexdigest()[:16] + '"'


def hesapla(tenant_id, plant_id) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text(
            "SELECT (SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p) AS son_scada,"
            " (SELECT max(run_at) FROM forecast_runs r WHERE plant_id=:p AND EXISTS (SELECT 1 FROM forecast_values v WHERE v.run_id=r.id)) AS son_kosu,"
            " (SELECT max(created_at) FROM alerts WHERE plant_id=:p) AS son_alarm,"
            " (SELECT count(*) FROM alerts WHERE plant_id=:p AND acked_by IS NULL AND created_at >= now() - interval '7 days') AS acik_alarm,"
            " (SELECT max(date) FROM skill_daily WHERE plant_id=:p) AS son_skill,"
            " (SELECT max(created_at) FROM calibrations WHERE plant_id=:p) AS son_kalibrasyon"),
            {"p": plant_id}).mappings().first()
    d = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(r).items()}
    d["acik_alarm"] = int(d.get("acik_alarm") or 0)
    return d
