"""v2.265 — Dalga 5.17: değişim damgası — 'panelde bir şey değişti mi?' sorusuna tek ucuz yanıt.

Kaynak DB (süreç içi bellek değil: API çok kopyalı olabilir, worker ayrı süreçtir). Beş + dört zaman damgası okunur (26.10: piyasa, iş kaydı, meteo, santral özü);
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
    d.update(_ortak_damga(tenant_id, plant_id))
    return d


def _ortak_damga(tenant_id, plant_id) -> dict:
    """26.10 eşzamanlama — damga artık şunları da kapsar (müşteri paneli bunlar değişince de tazelenir):
    son_piyasa: PTF/SMF güncellemesi (piyasa_fiyat.guncelleme; gece_piyasa işi), son_is: kiracının ya da küresel son iş kaydı
    (jobs_log.started; gece işlemleri kartı), son_meteo: santral noktasına en yakın meteo arşivi koşusu (gece_meteo işi),
    santral_ozu: santral parametreleri satırının özeti (kapasite, konum, params_json; Santral ayarları kaydedilince değişir).
    Küresel tablolar sistem bağlamından okunur (RLS dışı, kiracı süzgeci sorguda)."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        r = s.execute(text(
            "SELECT (SELECT max(guncelleme) FROM piyasa_fiyat) AS son_piyasa,"
            " (SELECT max(started) FROM jobs_log WHERE tenant_id = CAST(:t AS uuid) OR tenant_id IS NULL) AS son_is,"
            " (SELECT max(m.kosu_zamani) FROM meteo_arsiv m, plants p WHERE p.id = CAST(:p AS uuid)"
            "    AND abs(m.lat - p.lat) < 0.05 AND abs(m.lon - p.lon) < 0.05) AS son_meteo,"
            " (SELECT md5(CAST(row_to_json(p) AS text)) FROM plants p WHERE p.id = CAST(:p AS uuid) AND p.tenant_id = CAST(:t AS uuid)) AS santral_ozu"),
            {"t": str(tenant_id), "p": str(plant_id)}).mappings().first()
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(r).items()}
