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
                    file_format=None, mapping=None,
                    hazir_sonuc=None) -> dict:
    """hazir_sonuc verilirse ingest_file ATLANIR; Faz 1'de uretilip
    kullanicinin onayladigi sonuc aynen kalicilastirilir. None ise
    eski atomik davranis (yukle+kaydet) aynen gecerli."""
    res = hazir_sonuc if hazir_sonuc is not None else ingest_file(
        str(dosya_yolu), capacity_kwp=capacity_kwp,
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


def aylik_ozet(df: pd.DataFrame, tz: str | None = None) -> pd.DataFrame:
    """Issue #1 (v2.68): valid saatlik SCADA'dan aylik uretim ozeti.
    Saf fonksiyon — DB'siz test edilir. Girdi: scada_oku ciktisi (UTC index).
    tz verilirse ay siniri o saat diliminin takvimiyle cizilir (durust ay:
    31 Mart 21:00 UTC, Istanbul'da 1 Nisan'dir). tz=None -> UTC takvimi.
    Cikti kolonlari: ay (YYYY-MM), uretim_mwh, saat, kapsam_pct.
    kWh kaynagi: energy_kwh; bos satirda power_kw (saatlik seri: kW x 1h = kWh).
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["ay", "uretim_mwh", "saat", "kapsam_pct"])
    kwh = df["energy_kwh"].fillna(df["power_kw"])
    idx = df.index.tz_convert(tz) if tz else df.index
    g = kwh.groupby(idx.tz_localize(None).to_period("M"))
    out = pd.DataFrame({
        "uretim_mwh": (g.sum() / 1000.0).round(2),
        "saat": g.count().astype(int),
    })
    ay_saat = out.index.to_timestamp().days_in_month * 24
    out["kapsam_pct"] = (out["saat"] / ay_saat * 100).round(1)
    out.insert(0, "ay", out.index.astype(str))
    return out.reset_index(drop=True)


def aylik_uretim(tenant_id, plant_id) -> pd.DataFrame:
    """Ince DB sarmalayici: scada_oku -> aylik_ozet, santralin tz'siyle (v2.68)."""
    with tenant_baglami(tenant_id) as s:
        tz = s.execute(text("SELECT tz FROM plants WHERE id=:p"),
                       {"p": plant_id}).scalar()
    return aylik_ozet(scada_oku(tenant_id, plant_id), tz=tz)


def veri_ozeti(tenant_id, plant_id) -> dict:
    """Hafif varlık kontrolü: tüm satırları ÇEKMEDEN sayım + son damga.
    (scada_oku 15 bin satırı yükler; boş-durum kontrolü için israftır.)"""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text(
            "SELECT count(*) FILTER (WHERE flag='valid') AS valid_saat,"
            " max(ts_utc) AS son_ts FROM scada_hourly WHERE plant_id=:p"),
            {"p": plant_id}).first()
    return {"valid_saat": int(r.valid_saat or 0), "son_ts": r.son_ts}
