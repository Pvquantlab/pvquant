"""SCADA yukleme servisi: mevcut ingestion ciktisi -> kalici tablolar."""
from __future__ import annotations
import json
import pandas as pd
from sqlalchemy import text
from pvquant.db import tenant_baglami
from pvquant.io.ingestion.pipeline import ingest_file

_KOLONLAR = {"power_kw":"power_kw","energy_kwh":"energy_kwh",
             "poa_global":"poa_wm2","t_air":"t_air",
             "t_module":"t_module","wind_speed":"wind_ms"}


def yukle_ve_kaydet(tenant_id, plant_id, dosya_yolu, *, capacity_kwp,
                    latitude, longitude, source_timezone,
                    file_format=None, mapping=None) -> dict:
    res = ingest_file(str(dosya_yolu), capacity_kwp=capacity_kwp,
                      latitude=latitude, longitude=longitude,
                      source_timezone=source_timezone,
                      file_format=file_format, mapping=mapping)
    clean = res.data if hasattr(res, "data") else res.to_clean_frame()
    df = clean.set_index("timestamp") if "timestamp" in clean.columns else clean
    with tenant_baglami(tenant_id) as s:
        batch_id = s.execute(text(
            "INSERT INTO ingestion_batches(tenant_id,plant_id,filename,"
            " format_json,mapping_json,transform_json,quality_json) "
            "VALUES (:t,:p,:f,:fmt,:map,:tr,:q) RETURNING id"),
            {"t": tenant_id, "p": plant_id, "f": str(dosya_yolu),
             "fmt": _j(res, "file_format"), "map": _j(res, "mapping"),
             "tr": _j(res, "transform"), "q": _j(res, "report")}).scalar()
        satirlar = []
        for ts, row in df.iterrows():
            kayit = {"t": tenant_id, "p": plant_id, "ts": ts,
                     "flag": row.get("flag", "valid"), "b": batch_id}
            for src, hedef in _KOLONLAR.items():
                v = row.get(src)
                kayit[hedef] = None if pd.isna(v) else float(v)
            satirlar.append(kayit)
        s.execute(text(
            "INSERT INTO scada_hourly(tenant_id,plant_id,ts_utc,power_kw,"
            " energy_kwh,poa_wm2,t_air,t_module,wind_ms,flag,batch_id) "
            "VALUES (:t,:p,:ts,:power_kw,:energy_kwh,:poa_wm2,:t_air,"
            " :t_module,:wind_ms,:flag,:b) "
            "ON CONFLICT (plant_id, ts_utc) DO UPDATE SET "
            " power_kw=EXCLUDED.power_kw, energy_kwh=EXCLUDED.energy_kwh,"
            " poa_wm2=EXCLUDED.poa_wm2, t_air=EXCLUDED.t_air,"
            " t_module=EXCLUDED.t_module, wind_ms=EXCLUDED.wind_ms,"
            " flag=EXCLUDED.flag, batch_id=EXCLUDED.batch_id"), satirlar)
    return {"batch_id": str(batch_id), "n_satir": len(satirlar)}


def _j(res, alan):
    o = getattr(res, alan, None)
    if o is None: return None
    d = o.to_dict() if hasattr(o, "to_dict") else (
        o.model_dump() if hasattr(o, "model_dump") else None)
    return json.dumps(d, default=str, ensure_ascii=False) if d else None


def scada_oku(tenant_id, plant_id) -> pd.DataFrame:
    """Kalibrasyonun kullanacagi temiz okuma: valid satirlar, UTC index."""
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text(
            "SELECT ts_utc, power_kw, energy_kwh, poa_wm2, t_air,"
            " t_module, wind_ms FROM scada_hourly "
            "WHERE plant_id=:p AND flag='valid' ORDER BY ts_utc"),
            s.connection(), params={"p": plant_id},
            index_col="ts_utc", parse_dates=["ts_utc"])
    return df
