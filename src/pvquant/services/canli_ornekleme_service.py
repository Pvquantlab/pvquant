"""08.11.2026 v2.546 (P4b-2; IH-023) — Modbus TCP / SunSpec DÜZENLİ ÖRNEKLEME ve saatlik toplama (yalnız okuma).

Şartlar (hepsi birden): hedeflenen veri kaynağı `modbus_sunspec`, bağlantı ayarı (host/port/birim), yalnızca veri okuma onayı VE sahibin açıkça
işaretlediği «düzenli veri çekişini başlat» (`ornekleme_acik`). Bağlantı sınaması tek başına çekiş başlatmaz (v2.545 sözü korunur).
Örnek: inverter modelinden anlık güç (W), sayaç (Wh), DC güç, durum kodu, olay bitleri → `canli_ornek` (ham, silinmez).
Saatlik toplama: tamamlanmış her saat için örneklerden enerji — önce SAYAÇ FARKI (Wh, monoton ve her iki uç varsa), yoksa ortalama güç × kapsanan süre;
güç = ortalama W/1000. En az 2 örnek ve ≥ 40 dk kapsama şart; aksi hâlde saat yazılmaz (uydurma yok). scada_hourly'ye ayrı batch ile
(ingestion_batches.format_json.kaynak = 'modbus_sunspec'); var olan saat üzerine YAZILMAZ (dosya/EPİAŞ verisi korunur). Model çekirdeğine girmez.
Adres kuralı ve FC3 sınırı canli_alim_service / io.canli ile aynıdır.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pandas as pd

VARSAYILAN_PERIYOT_DK = 15
SAAT_MIN_ORNEK = 2
SAAT_MIN_KAPSAMA_DK = 40
TOPLAMA_GERI_SAAT = 24       # her turda geriye bakılan tamamlanmış saat sayısı (kaçırılan saatler tamamlanır)
BATCH_ADI = "modbus_sunspec"


def _pj(plant: dict) -> dict:
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    return pj


def uygun(plant: dict) -> tuple[bool, str | None, dict | None]:
    """SAF. Düzenli örnekleme şartları; döner (uygun, neden, beyan)."""
    vy = _pj(plant).get("veri_yolu")
    if not isinstance(vy, dict) or vy.get("tur") != "modbus_sunspec":
        return False, "hedef Modbus TCP / SunSpec değil", None
    if not vy.get("baglanti"):
        return False, "bağlantı ayarı yok", vy
    if not vy.get("salt_okuma_onayi"):
        return False, "yalnızca veri okuma onayı yok", vy
    if not vy.get("ornekleme_acik"):
        return False, "düzenli veri çekişi başlatılmadı", vy
    return True, None, vy


def periyot_dk(vy: dict | None) -> int:
    p = (vy or {}).get("periyot_dk")
    try:
        p = int(p) if p else VARSAYILAN_PERIYOT_DK
    except (TypeError, ValueError):
        p = VARSAYILAN_PERIYOT_DK
    return max(1, min(p, 1440))


def ornek_al(baglanti: dict, simdi: datetime | None = None, istemci_fabrikasi=None) -> dict:
    """Cihazdan tek örnek (FC3). Döner {ts_utc, guc_w, enerji_wh, dc_guc_w, durum_kodu, olaylar}. Hata → istisna (çağıran günlükler)."""
    from pvquant.io.canli import sunspec
    from pvquant.io.canli.modbus_tcp import ModbusTcpIstemci
    from pvquant.services.canli_alim_service import ZAMAN_ASIMI_SN, _cozumle, adres_izinli, hedef_dogrula
    h = hedef_dogrula(baglanti.get("host"), baglanti.get("port"), baglanti.get("birim"))
    izin, neden = adres_izinli(_cozumle(h["host"]))
    if not izin:
        raise ValueError(neden)
    fabrika = istemci_fabrikasi or (lambda host, port, birim, za: ModbusTcpIstemci(host, port, birim, za))
    with fabrika(h["host"], h["port"], h["birim"], ZAMAN_ASIMI_SN) as c:
        cihaz = sunspec.oku_cihaz(c.oku)
    inv = cihaz.get("inverter") or {}
    ts = (simdi or datetime.now(timezone.utc)).replace(microsecond=0)
    return {"ts_utc": ts, "guc_w": inv.get("guc_w"), "enerji_wh": inv.get("enerji_wh"), "dc_guc_w": inv.get("dc_guc_w"),
            "durum_kodu": inv.get("durum_kodu"), "olaylar": inv.get("olaylar", [])}


def saatlik_ozet(ornekler: pd.DataFrame, saat_bas: datetime) -> dict | None:
    """SAF. Bir saatin örneklerinden (ts_utc, guc_w, enerji_wh) saatlik değer. Yetersizse None.
    enerji: sayaç farkı (Wh → kWh) monoton ve iki uç doluysa; yoksa ortalama güç × kapsanan süre. nitelik: sayac | ortalama."""
    if ornekler is None or ornekler.empty or len(ornekler) < SAAT_MIN_ORNEK:
        return None
    d = ornekler.copy()
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True)
    d = d.sort_values("ts_utc")
    saat_bas = pd.Timestamp(saat_bas).tz_convert("UTC") if pd.Timestamp(saat_bas).tzinfo else pd.Timestamp(saat_bas, tz="UTC")
    saat_bit = saat_bas + pd.Timedelta(hours=1)
    d = d[(d["ts_utc"] >= saat_bas) & (d["ts_utc"] < saat_bit)]
    if len(d) < SAAT_MIN_ORNEK:
        return None
    kapsama_dk = (d["ts_utc"].iloc[-1] - d["ts_utc"].iloc[0]).total_seconds() / 60.0
    if kapsama_dk < SAAT_MIN_KAPSAMA_DK:
        return None
    guc = pd.to_numeric(d["guc_w"], errors="coerce")
    guc_kw = float(guc.mean()) / 1000.0 if guc.notna().any() else None
    say = pd.to_numeric(d.get("enerji_wh"), errors="coerce") if "enerji_wh" in d else pd.Series(dtype=float)
    enerji_kwh, nitelik = None, None
    if say.notna().sum() >= 2:
        ilk, son = float(say.dropna().iloc[0]), float(say.dropna().iloc[-1])
        if son >= ilk and say.dropna().is_monotonic_increasing:
            enerji_kwh, nitelik = (son - ilk) / 1000.0, "sayac"
    if enerji_kwh is None and guc_kw is not None:
        enerji_kwh, nitelik = guc_kw * min(kapsama_dk / 60.0, 1.0), "ortalama"
    if enerji_kwh is None:
        return None
    return {"ts_utc": saat_bas.to_pydatetime(), "power_kw": (round(guc_kw, 3) if guc_kw is not None else None), "energy_kwh": round(enerji_kwh, 3),
            "n": int(len(d)), "kapsama_dk": round(kapsama_dk, 1), "nitelik": nitelik}


# ----------------------------------------------------------------------------- DB
def ornek_yaz(tenant_id, plant: dict, o: dict) -> int:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return s.execute(text(
            "INSERT INTO canli_ornek(tenant_id, plant_id, ts_utc, kaynak, guc_w, enerji_wh, dc_guc_w, durum_kodu, olaylar_json) "
            "VALUES(:t, :p, :ts, 'modbus_sunspec', :g, :e, :dc, :d, CAST(:o AS jsonb)) ON CONFLICT (plant_id, ts_utc) DO NOTHING"),
            {"t": tenant_id, "p": plant["id"], "ts": o["ts_utc"], "g": o.get("guc_w"), "e": o.get("enerji_wh"), "dc": o.get("dc_guc_w"),
             "d": o.get("durum_kodu"), "o": json.dumps(o.get("olaylar") or [])}).rowcount


def son_ornek(tenant_id, plant: dict) -> datetime | None:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return s.execute(text("SELECT max(ts_utc) FROM canli_ornek WHERE plant_id=:p"), {"p": plant["id"]}).scalar()


def saatlik_topla(tenant_id, plant: dict, simdi: datetime | None = None, geri_saat: int = TOPLAMA_GERI_SAAT) -> dict:
    """Tamamlanmış son `geri_saat` saati örneklerden toplar; scada_hourly'de olmayan saatleri tek batch ile yazar (var olan saat korunur)."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    simdi = simdi or datetime.now(timezone.utc)
    bit = simdi.replace(minute=0, second=0, microsecond=0)   # tamamlanmış son saatin sonu
    bas = bit - timedelta(hours=geri_saat)
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text("SELECT ts_utc, guc_w, enerji_wh FROM canli_ornek WHERE plant_id=:p AND ts_utc >= :a AND ts_utc < :b ORDER BY ts_utc"),
                         s.connection(), params={"p": plant["id"], "a": bas, "b": bit}, parse_dates=["ts_utc"])
        if df.empty:
            return {"durum": "ornek_yok", "n_yazilan": 0}
        var = {r[0] for r in s.execute(text("SELECT ts_utc FROM scada_hourly WHERE plant_id=:p AND ts_utc >= :a AND ts_utc < :b"), {"p": plant["id"], "a": bas, "b": bit}).all()}
        satirlar = []
        saat = bas
        while saat < bit:
            if saat not in var:
                oz = saatlik_ozet(df, saat)
                if oz:
                    satirlar.append(oz)
            saat += timedelta(hours=1)
        if not satirlar:
            return {"durum": "yeni_saat_yok", "n_yazilan": 0}
        batch_id = s.execute(text(
            "INSERT INTO ingestion_batches(tenant_id,plant_id,filename,format_json,quality_json) VALUES(:t,:p,:f,CAST(:fmt AS jsonb),CAST(:q AS jsonb)) RETURNING id"),
            {"t": tenant_id, "p": plant["id"], "f": BATCH_ADI, "fmt": json.dumps({"kaynak": BATCH_ADI, "bas": satirlar[0]["ts_utc"].isoformat(), "bitis": satirlar[-1]["ts_utc"].isoformat()}),
             "q": json.dumps({"n": len(satirlar), "sayac": sum(1 for r in satirlar if r["nitelik"] == "sayac"), "ortalama": sum(1 for r in satirlar if r["nitelik"] == "ortalama")})}).scalar()
        n = 0
        for r in satirlar:
            n += s.execute(text(
                "INSERT INTO scada_hourly(tenant_id,plant_id,ts_utc,power_kw,energy_kwh,flag,batch_id) VALUES(:t,:p,:ts,:pk,:e,'valid',:b) "
                "ON CONFLICT (plant_id, ts_utc) DO NOTHING"),
                {"t": tenant_id, "p": plant["id"], "ts": r["ts_utc"], "pk": r["power_kw"], "e": r["energy_kwh"], "b": batch_id}).rowcount
    return {"durum": "ok", "n_yazilan": int(n), "n_saat": len(satirlar)}


def tur(plants: list[dict], simdi: datetime | None = None, istemci_fabrikasi=None, yaz=ornek_yaz, son=son_ornek, topla=saatlik_topla) -> str | None:
    """Bir tur: uygun santrallarda periyodu dolmuşsa örnek al + yaz, sonra saatlik toplama. Uygun santral yoksa None (günlük satırı düşmez)."""
    simdi = simdi or datetime.now(timezone.utc)
    ozet = []
    for plant in plants:
        ok, _neden, vy = uygun(plant)
        if not ok:
            continue
        ad = plant.get("name") or plant.get("id")
        try:
            so = son(plant["tenant_id"], plant)
            if so is None or (simdi - (so if so.tzinfo else so.replace(tzinfo=timezone.utc))) >= timedelta(minutes=periyot_dk(vy)):
                o = ornek_al(vy["baglanti"], simdi, istemci_fabrikasi)
                yaz(plant["tenant_id"], plant, o)
                ozet.append(f"{ad}: örnek {o['guc_w']} W")
            else:
                ozet.append(f"{ad}: periyot dolmadı")
            t = topla(plant["tenant_id"], plant, simdi)
            if t.get("n_yazilan"):
                ozet.append(f"{ad}: {t['n_yazilan']} saat yazıldı")
        except Exception as e:   # noqa: BLE001 — bir santralın cihaz hatası diğerlerini durdurmaz
            ozet.append(f"{ad}: HATA {type(e).__name__}: {e}")
    return "; ".join(ozet) if ozet else None


def durum(tenant_id, plant: dict) -> dict | None:
    """Veri kaynakları kartı için: son örnek, son 24 saatte örnek sayısı, bu kaynaktan yazılan son saat. Tablo yoksa None."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    try:
        with tenant_baglami(tenant_id) as s:
            r = s.execute(text("SELECT max(ts_utc) AS son, count(*) FILTER (WHERE ts_utc >= now() - INTERVAL '24 hour') AS n24 FROM canli_ornek WHERE plant_id=:p"),
                          {"p": plant["id"]}).mappings().first()
            ss = s.execute(text("SELECT max(sh.ts_utc) FROM scada_hourly sh JOIN ingestion_batches b ON b.id = sh.batch_id "
                                "WHERE sh.plant_id=:p AND b.format_json->>'kaynak' = 'modbus_sunspec'"), {"p": plant["id"]}).scalar()
    except Exception:   # noqa: BLE001 — göç uygulanmamışsa
        return None
    if not r or r["son"] is None:
        return {"son_ornek": None, "n24": 0, "son_saat": None}
    return {"son_ornek": r["son"], "n24": int(r["n24"] or 0), "son_saat": ss}
