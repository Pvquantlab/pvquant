"""v2.278 — Tablo 3.1 satır 7: EPİAŞ Şeffaflık gerçekleşen üretim → SCADA yüklenmeyen santrallerde gerçekleşen kaynağı.

Lisanslı santralın saatlik gerçek zamanlı üretimi Şeffaflık Platformu'ndan (TGT kimliği: PVQUANT_EPIAS_KULLANICI/SIFRE) çekilir
ve scada_hourly'ye 'epias' kaynaklı bir yükleme partisi olarak yazılır — yalnız SCADA'nın OLMADIĞI saatlere (ON CONFLICT DO
NOTHING: kullanıcı yüklemesi her zaman önceliklidir). Santral eşlemesi params_json.epias_santral_id (Şeffaflık powerPlantId;
santral listesi ucundan bulunur). Saatlik MWh → ortalama kW. Kimlik ya da eşleme yoksa dürüstçe atlanır; durum panelde söylenir.
Karne/skill/alarm bu satırları SCADA gibi kullanır — kaynak parti kaydında (ingestion_batches.filename='epias_realtime') görünür.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd

from pvquant.config import get_settings

PARTI_ADI = "epias_realtime"


def _pj(plant: dict) -> dict:
    pj = plant.get("params_json") or {}
    return json.loads(pj) if isinstance(pj, str) else pj


def uygun_mu(plant: dict) -> tuple[bool, str]:
    s = get_settings()
    if not (s.epias_kullanici and s.epias_sifre):
        return False, "EPİAŞ kimliği yok (PVQUANT_EPIAS_KULLANICI / PVQUANT_EPIAS_SIFRE)"
    if not _pj(plant).get("epias_santral_id"):
        return False, "Şeffaflık santral kimliği (epias_santral_id) tanımlı değil"
    return True, "hazır"


def satirlar_uret(uretim_mwh: pd.Series, capacity_kwp: float) -> list[dict]:
    """SAF. UTC saatlik MWh → scada satırları (power_kw = MWh×1000; tavan aşımı/negatif 'anomali' bayrağıyla, silinmez)."""
    from pvquant.ext.turkiye.epias import gerceklesen_adaptoru
    df = gerceklesen_adaptoru(uretim_mwh.dropna(), capacity_kwp / 1000.0)
    out = []
    for ts, r in df.iterrows():
        out.append({"ts": ts.to_pydatetime(), "power_kw": float(r["uretim_mwh"]) * 1000.0, "energy_kwh": float(r["uretim_mwh"]) * 1000.0,
                    "flag": "valid" if not r["bayrak"] else "anomali"})
    return out


def cek(plant: dict, bas: date, bitis: date, istemci=None) -> pd.Series:
    from pvquant.services.piyasa_service import _istemci
    c = istemci or _istemci()
    return c.gercek_zamanli_uretim(bas.isoformat(), bitis.isoformat(), powerPlantId=int(_pj(plant)["epias_santral_id"]))


def yukle(tenant_id, plant: dict, gun: int = 7, istemci=None) -> dict:
    """Son `gun` günün üretimini çek, SCADA olmayan saatlere yaz. Döner {durum, n_yazilan, n_cekilen, bas, bitis}."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    ok, neden = uygun_mu(plant)
    if not ok and istemci is None:
        return {"durum": "atlandi", "neden": neden, "n_yazilan": 0}
    bitis = date.today() - timedelta(days=1); bas = bitis - timedelta(days=gun)
    seri = cek(plant, bas, bitis, istemci)
    if seri.empty:
        return {"durum": "veri_yok", "n_yazilan": 0, "n_cekilen": 0, "bas": bas.isoformat(), "bitis": bitis.isoformat()}
    satirlar = satirlar_uret(seri, float(plant["capacity_kwp"]))
    with tenant_baglami(tenant_id) as s:
        batch_id = s.execute(text(
            "INSERT INTO ingestion_batches(tenant_id,plant_id,filename,format_json,quality_json) VALUES(:t,:p,:f,CAST(:fmt AS jsonb),CAST(:q AS jsonb)) RETURNING id"),
            {"t": tenant_id, "p": plant["id"], "f": PARTI_ADI, "fmt": json.dumps({"kaynak": "epias_realtime", "bas": bas.isoformat(), "bitis": bitis.isoformat()}),
             "q": json.dumps({"n": len(satirlar), "anomali": sum(1 for r in satirlar if r["flag"] != "valid")})}).scalar()
        n = 0
        for r in satirlar:
            n += s.execute(text(
                "INSERT INTO scada_hourly(tenant_id,plant_id,ts_utc,power_kw,energy_kwh,flag,batch_id) "
                "VALUES(:t,:p,:ts,:pk,:e,:f,:b) ON CONFLICT (plant_id, ts_utc) DO NOTHING"),
                {"t": tenant_id, "p": plant["id"], "ts": r["ts"], "pk": r["power_kw"], "e": r["energy_kwh"], "f": r["flag"], "b": batch_id}).rowcount
    return {"durum": "ok", "n_yazilan": int(n), "n_cekilen": len(satirlar), "bas": bas.isoformat(), "bitis": bitis.isoformat()}


def durum(tenant_id, plant: dict) -> dict:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    ok, neden = uygun_mu(plant)
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text(
            "SELECT count(*) AS n, max(s.ts_utc) AS son FROM scada_hourly s JOIN ingestion_batches b ON b.id = s.batch_id "
            "WHERE s.plant_id=:p AND b.filename=:f"), {"p": plant["id"], "f": PARTI_ADI}).mappings().first()
    return {"uygun": ok, "neden": neden, "epias_santral_id": _pj(plant).get("epias_santral_id"),
            "n_saat": int(r["n"] or 0), "son": r["son"].isoformat() if r["son"] else None}
