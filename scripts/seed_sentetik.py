#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sentetik tohum (E.3-b hamle 2, v2.104).

AMAÇ: veri zaten sentetik — takvim beklemek anlamsız. Son N günü gerçekçi
SCADA + tahminle doldurur; türev tabloları (skill_daily, report_stats)
GERÇEK worker fonksiyonlarıyla hesaplatır. pdf16 böylece sahte ara
tablodan değil, uygulamanın kendi boru hattından doğar.

DAMGA / GERİ ALMA — her şey deterministik kimlikle işaretli:
  scada    : batch_id = uuid5(NS_DNS, "pvq-seed-scada-<plant_id>")
  koşular  : meteo_source = 'sentetik_tohum'
Tekrar koşmak güvenli (önce kendi izini siler). Tamamen geri almak için:
  python scripts/seed_sentetik.py --temizle
"""
import argparse
import datetime as dt
import pathlib
import sys
import uuid

_KOK = pathlib.Path(__file__).resolve().parents[1]
if str(_KOK) not in sys.path:
    sys.path.insert(0, str(_KOK))

import numpy as np
import pandas as pd
from sqlalchemy import text

from pvquant.db import tenant_baglami  # yalnız türev hesaplar (worker fonksiyonları) kullanır
from apps.worker.main import _tum_santraller, gece_skill, rapor_alanlari

# Ham tablo yaz/sil işleri SAHİP rolüyle: bakım scripti uygulama rolü değildir;
# pvq_app'e DELETE bilerek verilmedi (çalışma zamanı silmez) ve bu doğru kalmalı.
import os as _os
from sqlalchemy import create_engine as _ce
from sqlalchemy.orm import Session as _Session
_SAHIP = _ce(_os.environ.get(
    "PVQ_DB_URL",
    "postgresql+psycopg://pvquant:pvquant_dev@localhost:5432/pvquant"))


def _sahip_oturum():
    return _Session(_SAHIP)


def _batch_id(pid):
    return uuid.uuid5(uuid.NAMESPACE_DNS, "pvq-seed-scada-%s" % pid)


def _run_id(pid, gun):
    return uuid.uuid5(uuid.NAMESPACE_DNS, "pvq-seed-run-%s-%s" % (pid, gun))


def _temizle(plant, gun_sayisi):
    """Kendi izini sil: koşular (meteo_source damgası), scada (batch damgası),
    tohum penceresindeki skill_daily (o pencerede TÜM scada sentetikti) ve
    report_stats fotoğrafları (aşağıda gerçek veriyle yeniden hesaplanır)."""
    tid, pid = plant["tenant_id"], plant["id"]
    esik = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=gun_sayisi + 2)
    with _sahip_oturum() as s, s.begin():
        n1 = s.execute(text(
            "DELETE FROM forecast_values WHERE run_id IN "
            "(SELECT id FROM forecast_runs WHERE plant_id=:p "
            " AND meteo_source='sentetik_tohum')"), {"p": pid}).rowcount
        n2 = s.execute(text(
            "DELETE FROM forecast_runs WHERE plant_id=:p "
            "AND meteo_source='sentetik_tohum'"), {"p": pid}).rowcount
        n3 = s.execute(text(
            "DELETE FROM scada_hourly WHERE plant_id=:p AND batch_id=:b"),
            {"p": pid, "b": _batch_id(pid)}).rowcount
        s.execute(text("DELETE FROM ingestion_batches WHERE id=:b"),
                  {"b": _batch_id(pid)})
        n4 = s.execute(text(
            "DELETE FROM skill_daily WHERE plant_id=:p AND date >= :e"),
            {"p": pid, "e": esik.date()}).rowcount
        s.execute(text("DELETE FROM report_stats WHERE plant_id=:p"),
                  {"p": pid})
    print("  temizlik: %d tahmin, %d koşu, %d scada, %d skill satırı" %
          (n1, n2, n3, n4))


def _sentetik_seri(plant, saatler, rng):
    """Berrak-gök biçimli, gün-hava-faktörlü 'gerçekleşen' güç (kW)."""
    import pvlib
    loc = pvlib.location.Location(float(plant["lat"]), float(plant["lon"]),
                                  tz="UTC")
    cs = loc.get_clearsky(saatler, model="haurwitz").ghi  # W/m2
    gunler = sorted(set(saatler.date))
    f, faktor = 0.85, {}
    for g in gunler:                      # AR(1) hava faktörü — ardışık günler benzer
        f = 0.72 * f + 0.28 * rng.uniform(0.50, 1.02)
        faktor[g] = f
    fdizi = np.array([faktor[t.date()] for t in saatler])
    kwp = float(plant["capacity_kwp"])
    guc = kwp * (cs.values / 1000.0) * 0.88 * fdizi
    guc = guc * rng.normal(1.0, 0.02, len(guc))          # ölçüm gürültüsü
    return np.clip(guc, 0.0, kwp)


def ek(plant, gun_sayisi):
    tid, pid = plant["tenant_id"], plant["id"]
    rng = np.random.default_rng(int(uuid.UUID(str(pid))) % (2**32))
    simdi = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0,
                                                     microsecond=0)
    bas = simdi - dt.timedelta(days=gun_sayisi)
    # gerçekleşen: bas → simdi-1h; tahmin ufku simdi+72h'ye taşar
    tum_saatler = pd.date_range(bas, simdi + dt.timedelta(hours=72),
                                freq="h", tz="UTC")
    gercek = pd.Series(_sentetik_seri(plant, tum_saatler, rng),
                       index=tum_saatler)

    # --- SCADA (yalnız geçmiş; gece 0 kW satırı yazılmaz → bayrak temiz) ---
    scada = []
    b = _batch_id(pid)
    for ts, kw in gercek[gercek.index < simdi].items():
        if kw <= 0.0:
            continue
        scada.append({"t": tid, "p": pid, "ts": ts, "kw": float(kw),
                      "e": float(kw), "b": b})
    with _sahip_oturum() as s, s.begin():
        s.execute(text(
            "INSERT INTO ingestion_batches(id,tenant_id,plant_id,filename,"
            " format_json,mapping_json,transform_json,quality_json)"
            " VALUES(:b,:t,:p,'SENTETIK_TOHUM (seed_sentetik.py)',"
            " '{}'::jsonb,'{}'::jsonb,'{}'::jsonb,"
            " jsonb_build_object('sentetik', true, 'gun', :g))"),
            {"b": b, "t": tid, "p": pid, "g": gun_sayisi})
        s.execute(text(
            "INSERT INTO scada_hourly(tenant_id,plant_id,ts_utc,power_kw,"
            " energy_kwh,flag,batch_id) VALUES(:t,:p,:ts,:kw,:e,'valid',:b)"),
            scada)
    print("  scada: %d saat (%s → %s)" %
          (len(scada), bas.date(), (simdi - dt.timedelta(hours=1)).date()))

    # --- Koşular: her gün 03:00'te, 72 saatlik ufuk ---
    n_deger = 0
    with _sahip_oturum() as s, s.begin():
        for i in range(gun_sayisi):
            g = (bas + dt.timedelta(days=i)).date()
            run_at = dt.datetime(g.year, g.month, g.day, 3,
                                 tzinfo=dt.timezone.utc)
            rid = _run_id(pid, g)
            s.execute(text(
                "INSERT INTO forecast_runs(id,tenant_id,plant_id,run_at,mode,"
                " model,meteo_source,meteo_ozet_json) VALUES(:i,:t,:p,:r,'C',"
                " 'hybrid_residual','sentetik_tohum','{}'::jsonb)"),
                {"i": rid, "t": tid, "p": pid, "r": run_at})
            ufuk = pd.date_range(run_at + dt.timedelta(hours=1),
                                 run_at + dt.timedelta(hours=72),
                                 freq="h", tz="UTC")
            degerler = []
            for ts in ufuk:
                a = float(gercek.get(ts, 0.0))
                if a <= 0.0:
                    continue                     # gece: tahmin de 0, satır yok
                h = (ts - run_at).total_seconds() / 3600
                sap = 0.05 if h < 24 else 0.11   # ufukla büyüyen hata
                bant = 0.10 if h < 24 else 0.18
                p50 = max(0.0, a * (1 + rng.normal(0, sap)))
                degerler.append({
                    "t": tid, "r": rid, "p": pid, "ts": ts, "p50": p50,
                    "p10": p50 * (1 - bant), "p90": p50 * (1 + bant),
                    "f": p50 * float(rng.normal(1, 0.03)),
                    "m": p50 * float(rng.normal(1, 0.02))})
            if degerler:
                s.execute(text(
                    "INSERT INTO forecast_values(tenant_id,run_id,plant_id,"
                    " ts_utc,p50_kw,p10_kw,p90_kw,physics_kw,ml_kw)"
                    " VALUES(:t,:r,:p,:ts,:p50,:p10,:p90,:f,:m)"), degerler)
                n_deger += len(degerler)
    print("  tahmin: %d koşu, %d değer" % (gun_sayisi, n_deger))

    # --- Türevler GERÇEK boru hattından ---
    gece_skill(plant, pencere_gun=gun_sayisi + 5)
    rapor_alanlari(plant, pencere_gun=120)
    with _sahip_oturum() as s:
        kg = s.execute(text(
            "SELECT count(DISTINCT date) FROM skill_daily "
            "WHERE plant_id=:p AND horizon_bucket LIKE '0%'"),
            {"p": pid}).scalar()
        anahtarlar = [r[0] for r in s.execute(text(
            "SELECT key FROM report_stats WHERE plant_id=:p ORDER BY key"),
            {"p": pid})]
    print("  türev: skill_daily %d gün (0-24) · report_stats: %s" %
          (kg, ", ".join(anahtarlar) or "BOŞ"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gun", type=int, default=45)
    ap.add_argument("--temizle", action="store_true",
                    help="yalnız tohum izini sil, ekme yapma")
    ap.add_argument("--santral", default=None,
                    help="tek santral adı (varsayılan: tüm aktifler)")
    arg = ap.parse_args()
    for plant in _tum_santraller():
        if arg.santral and plant["name"] != arg.santral:
            continue
        print("=== %s ===" % plant["name"])
        _temizle(plant, arg.gun)
        if not arg.temizle:
            ek(plant, arg.gun)
    print("bitti.")
