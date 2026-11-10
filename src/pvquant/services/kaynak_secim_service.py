"""09.11.2026 v2.550 (Aşama 1, D5) — KAYNAK SEÇİMİ ve GÖLGE SAATLİK GÖRÜNÜM (yalnız okuma; çekirdeğe ve scada_hourly'ye dokunmaz).

Kural (Codex 07 «Kaynak önceliği ve revizyon»): evrensel «sayaç > SCADA > inverter» sırası yoktur. Önce aynı ÖLÇÜM SINIRI, aynı dönem; sonra tamlık
(measured_complete > measured_partial > estimated); sonra santralın kaynak önceliği (params_json.kaynak_onceligi ya da varsayılan); eşitlikte kaynak adı
ve cihaz kimliği. Her kaynağın yalnız EN SON revizyonu aday olur; düşük öncelikli silinmez, «alternatif» olarak döner. Seçimin nedeni yazılır.
Gölge görünüm: kaynak_saatlik'ten seçilen saat ile scada_hourly'deki (dosya / EPİAŞ / canlı) saat yan yana; fark kWh ve nitelik. Tahmin, doğruluk ve
kalibrasyon bu görünümü OKUMAZ; kabul sonrası ayrı bir işle bağlanır (yol haritası DEV10).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

TAMLIK_SIRA = {"measured_complete": 2, "measured_partial": 1, "estimated": 0}
TAMLIK_ETIKET = {"measured_complete": "tam saat ölçümü", "measured_partial": "kısmi saat ölçümü", "estimated": "tahmini"}
VARSAYILAN_ONCELIK = {"scada_dosya": 3, "sayac_dosya": 3, "iec104": 2, "modbus_sunspec": 2, "fusionsolar": 1, "solaredge": 1, "solis": 1, "sungrow": 1, "growatt": 1, "epias_seffaflik": 1}   # v2.557: bulut (sağlayıcı) doğrudan okumaların altında
SINIR_ETIKET = {"inverter_ac": "inverter AC çıkışı", "plant_gross_ac": "tesis brüt AC", "pcc_net": "bağlantı noktası net", "settlement": "uzlaştırma sayacı"}
BATCH_KAYNAK = {"modbus_sunspec": "modbus_sunspec", "iec104": "iec104", "epias_realtime": "epias_seffaflik"}


def oncelik(plant: dict | None) -> dict:
    pj = (plant or {}).get("params_json") or {}
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    o = pj.get("kaynak_onceligi") if isinstance(pj.get("kaynak_onceligi"), dict) else {}
    return {**VARSAYILAN_ONCELIK, **{k: int(v) for k, v in o.items() if isinstance(v, (int, float))}}


def _son_revizyonlar(adaylar: list[dict]) -> list[dict]:
    son: dict[tuple, dict] = {}
    for a in adaylar:
        k = (a.get("kaynak"), a.get("cihaz_id", "santral"), a.get("sinir", "inverter_ac"))
        if k not in son or int(a.get("revizyon") or 1) > int(son[k].get("revizyon") or 1):
            son[k] = a
    return list(son.values())


def sec(adaylar: list[dict], sinir: str = "inverter_ac", onc: dict | None = None) -> dict | None:
    """SAF. Aynı saat için adaylar (kaynak, cihaz_id, sinir, revizyon, power_kw, energy_kwh, tamlik). Döner {secilen, alternatifler, neden} ya da None."""
    onc = onc or VARSAYILAN_ONCELIK
    ayni = [a for a in _son_revizyonlar(adaylar) if a.get("sinir", "inverter_ac") == sinir]
    if not ayni:
        return None
    ayni.sort(key=lambda a: (-TAMLIK_SIRA.get(a.get("tamlik"), 0), -onc.get(a.get("kaynak"), 0), str(a.get("kaynak")), str(a.get("cihaz_id"))))
    s = ayni[0]
    neden = TAMLIK_ETIKET.get(s.get("tamlik"), s.get("tamlik"))
    if len(ayni) > 1:
        r = ayni[1]
        if TAMLIK_SIRA.get(s.get("tamlik"), 0) > TAMLIK_SIRA.get(r.get("tamlik"), 0):
            neden += f"; {r.get('kaynak')} {TAMLIK_ETIKET.get(r.get('tamlik'), '')} olduğu için geride"
        elif onc.get(s.get("kaynak"), 0) != onc.get(r.get("kaynak"), 0):
            neden += f"; kaynak önceliği {s.get('kaynak')} > {r.get('kaynak')}"
        else:
            neden += "; eşitlikte ad sırası"
    return {"secilen": s, "alternatifler": ayni[1:], "neden": neden}


def karsilastir(golge: list[dict], mevcut: list[dict], plant: dict | None = None, sinir: str = "inverter_ac") -> dict:
    """SAF. golge: kaynak_saatlik satırları; mevcut: scada_hourly satırları (ts_utc, power_kw, energy_kwh, flag, kaynak). Saat bazında yan yana."""
    onc = oncelik(plant)
    saatler: dict[datetime, list[dict]] = {}
    for g in golge:
        saatler.setdefault(g["ts_utc"], []).append(g)
    mev = {m["ts_utc"]: m for m in mevcut}
    out, n_tam, n_kismi, n_fark = [], 0, 0, 0
    for ts in sorted(set(saatler) | set(mev)):
        secim = sec(saatler.get(ts, []), sinir, onc)
        m = mev.get(ts)
        s = (secim or {}).get("secilen")
        fark = (round(float(s["energy_kwh"]) - float(m["energy_kwh"]), 3) if s and m and s.get("energy_kwh") is not None and m.get("energy_kwh") is not None else None)
        if s:
            n_tam += s.get("tamlik") == "measured_complete"; n_kismi += s.get("tamlik") == "measured_partial"
        if fark is not None and abs(fark) > 0.5:
            n_fark += 1
        out.append({"ts_utc": ts.isoformat() if hasattr(ts, "isoformat") else ts,
                    "secilen": ({"kaynak": s["kaynak"], "cihaz_id": s.get("cihaz_id"), "power_kw": s.get("power_kw"), "energy_kwh": s.get("energy_kwh"),
                                 "tamlik": s.get("tamlik"), "tamlik_etiketi": TAMLIK_ETIKET.get(s.get("tamlik")), "yontem": s.get("yontem"), "revizyon": s.get("revizyon"),
                                 "kapsama_dk": s.get("kapsama_dk")} if s else None),
                    "neden": (secim or {}).get("neden"), "alternatif_sayisi": len((secim or {}).get("alternatifler", [])),
                    "mevcut": ({"power_kw": m.get("power_kw"), "energy_kwh": m.get("energy_kwh"), "flag": m.get("flag"), "kaynak": m.get("kaynak")} if m else None),
                    "fark_kwh": fark})
    return {"saatler": out, "ozet": {"n_saat": len(out), "n_tam": n_tam, "n_kismi": n_kismi, "n_mevcut": len(mev), "n_fark_05kwh": n_fark},
            "sinir": sinir, "sinir_etiketi": SINIR_ETIKET.get(sinir, sinir), "oncelik": onc,
            "not": "Gölge görünüm: kaynak bazlı saatlik değerler ile üretim serisindeki saat yan yana. Tahmin ve doğruluk bu görünümü kullanmaz; kaynak seçimi kabul edilince ayrı bir işle bağlanır. Kısmi ve tahmini saatler üretim serisine yazılmaz."}


def golge_gorunum(tenant_id, plant: dict, bas: datetime, bit: datetime, sinir: str = "inverter_ac") -> dict:
    """DB: kaynak_saatlik + scada_hourly (batch kaynağıyla) → karsilastir. Tablo yoksa boş görünüm."""
    import pandas as pd
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    try:
        with tenant_baglami(tenant_id) as s:
            g = s.execute(text("SELECT ts_utc, kaynak, cihaz_id, sinir, revizyon, power_kw, energy_kwh, tamlik, yontem, kapsama_dk FROM kaynak_saatlik "
                               "WHERE plant_id=:p AND ts_utc >= :a AND ts_utc < :b ORDER BY ts_utc, revizyon"), {"p": plant["id"], "a": bas, "b": bit}).mappings().all()
            m = s.execute(text("SELECT h.ts_utc, h.power_kw, h.energy_kwh, h.flag, b.format_json->>'kaynak' AS kaynak FROM scada_hourly h "
                               "LEFT JOIN ingestion_batches b ON b.id = h.batch_id WHERE h.plant_id=:p AND h.ts_utc >= :a AND h.ts_utc < :b ORDER BY h.ts_utc"),
                          {"p": plant["id"], "a": bas, "b": bit}).mappings().all()
    except Exception:   # noqa: BLE001 — göç uygulanmamışsa
        return {**karsilastir([], [], plant, sinir), "uyari": "gölge tablo henüz yok (göç uygulanmadı)"}
    golge = [dict(r) for r in g]
    mevcut = [{**dict(r), "kaynak": BATCH_KAYNAK.get(r["kaynak"] or "", r["kaynak"] or "scada_dosya")} for r in m]
    return karsilastir(golge, mevcut, plant, sinir)


def varsayilan_pencere(simdi: datetime | None = None, gun: int = 7) -> tuple[datetime, datetime]:
    simdi = simdi or datetime.now(timezone.utc)
    bit = simdi.replace(minute=0, second=0, microsecond=0)
    return bit - timedelta(days=gun), bit


KAYNAK_ETIKET = {"scada_dosya": "SCADA dosyası", "sayac_dosya": "sayaç dosyası", "epias_seffaflik": "EPİAŞ Şeffaflık", "modbus_sunspec": "Modbus / SunSpec", "iec104": "IEC 104",
                 "fusionsolar": "FusionSolar bulutu", "solaredge": "SolarEdge bulutu", "solis": "SolisCloud", "sungrow": "iSolarCloud (Sungrow)", "growatt": "Growatt bulutu"}   # v2.559 (V4); v2.562: rapor ve dış API etiketleri (kod müşteri yüzüne çıkmaz)


def nitelik_ozeti(tenant_id, plant: dict, bas: datetime, bit: datetime) -> dict | None:
    """v2.559 (V4). Dönemde üretim serisi saatlerinin kaynak dağılımı (scada_hourly geçerli saatler, parti kaynağıyla) ve gölge tablonun son revizyon
    özeti (kaynak × tamlık; birden çok revizyonu olan saat sayısı). Tahmin ve doğruluk gölge görünümü kullanmaz. Tablo yoksa gölge None; hiç veri yoksa None."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    try:
        with tenant_baglami(tenant_id) as s:
            m = s.execute(text("SELECT COALESCE(b.format_json->>'kaynak', 'scada_dosya') AS k, count(*) AS n FROM scada_hourly h LEFT JOIN ingestion_batches b ON b.id = h.batch_id "
                               "WHERE h.plant_id=:p AND h.ts_utc >= :a AND h.ts_utc < :b AND h.flag='valid' GROUP BY 1 ORDER BY 2 DESC"), {"p": plant["id"], "a": bas, "b": bit}).mappings().all()
            try:
                g = s.execute(text("SELECT kaynak, tamlik, count(*) AS n FROM (SELECT DISTINCT ON (kaynak, cihaz_id, sinir, ts_utc) kaynak, tamlik FROM kaynak_saatlik "
                                   "WHERE plant_id=:p AND ts_utc >= :a AND ts_utc < :b ORDER BY kaynak, cihaz_id, sinir, ts_utc, revizyon DESC) x GROUP BY 1, 2 ORDER BY 1, 2"),
                              {"p": plant["id"], "a": bas, "b": bit}).mappings().all()
                rev = s.execute(text("SELECT count(*) FROM (SELECT 1 FROM kaynak_saatlik WHERE plant_id=:p AND ts_utc >= :a AND ts_utc < :b GROUP BY kaynak, cihaz_id, sinir, ts_utc "
                                     "HAVING max(revizyon) > 1) y"), {"p": plant["id"], "a": bas, "b": bit}).scalar()
                golge = {"kaynaklar": [{"kaynak": BATCH_KAYNAK.get(r["kaynak"], r["kaynak"]), "etiket": KAYNAK_ETIKET.get(BATCH_KAYNAK.get(r["kaynak"], r["kaynak"]), r["kaynak"]),
                                        "tamlik": r["tamlik"], "tamlik_etiketi": TAMLIK_ETIKET.get(r["tamlik"], r["tamlik"]), "saat": int(r["n"])} for r in g],
                         "revizyonlu_saat": int(rev or 0)}
            except Exception:   # noqa: BLE001 — gölge tablo yoksa
                s.rollback(); golge = None
    except Exception:   # noqa: BLE001
        return None
    seri = [{"kaynak": BATCH_KAYNAK.get(r["k"], r["k"]), "etiket": KAYNAK_ETIKET.get(BATCH_KAYNAK.get(r["k"], r["k"]), r["k"]), "saat": int(r["n"])} for r in m]
    if not seri and not (golge and golge["kaynaklar"]):
        return None
    metin = "Üretim serisi: " + (", ".join(f"{x['etiket']} {x['saat']} saat" for x in seri) if seri else "geçerli saat yok")
    if golge and golge["kaynaklar"]:
        metin += "; kaynak kıyası (üretim serisine yazılmayan sınıflar dâhil): " + ", ".join(f"{x['etiket']} {x['tamlik_etiketi']} {x['saat']}" for x in golge["kaynaklar"])
        if golge["revizyonlu_saat"]:
            metin += f"; {golge['revizyonlu_saat']} saatte birden çok revizyon"
    return {"uretim_serisi": seri, "golge": golge, "metin": metin,
            "not": "Her saatin kaynağı, ölçüm sınırı, niteliği ve revizyonu izlenebilir; kısmi ve tahmini saatler üretim serisine yazılmaz, tahmin ve doğruluk kaynak kıyasını kullanmaz."}
