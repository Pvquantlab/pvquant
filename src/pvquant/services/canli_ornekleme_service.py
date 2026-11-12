"""08.11.2026 v2.546 (P4b-2; IH-023) — Modbus TCP / SunSpec DÜZENLİ ÖRNEKLEME ve saatlik toplama (yalnız okuma).
v2.549 (Aşama 1, D1) — SAATLİK TOPLAMA DÜZELTMESİ: saat enerjisi E = C(saat_sonu) − C(saat_başı); KAPANIŞ ÖRNEĞİ dâhil. İki sınır da yoksa saat
«measured_partial» (kısmi) olur, üretim serisine YAZILMAZ. Sınır örneği tam saatte değilse ve sınırı saran iki örnek bir periyot içindeyse sayaç
sınıra doğrusal interpolasyonla taşınır (`sinir_interpolasyon`). Güç zaman ağırlıklı ortalamadır; sayaç yoksa enerji güç eğrisinin yamuk entegrali
(«entegrasyon»), yalnız iki sınır da varsa tam sayılır. Eski davranış (00:00–00:45 farkı tam saat yazılırdı, 40 dk eşiği) Codex 07a/U19 kaydıyla kapandı.
v2.550 (Aşama 1, D4/D5) — cihaz/sınır kimliği: örnek `cihaz_id` (SunSpec seri no ya da 'santral') ve `sinir` ile saklanır; saatlik sonuçlar kaynak,
cihaz, sınır, tamlık, yöntem ve REVİZYON ile `kaynak_saatlik` (gölge) tablosuna yazılır — her saat, kısmi dâhil. scada_hourly'ye yalnız
measured_complete saatler, var olan saat üzerine yazılmadan (dosya/EPİAŞ verisi korunur). Değişen değer yeni revizyon üretir; eski silinmez.

Şartlar (hepsi birden): hedeflenen veri kaynağı `modbus_sunspec`, bağlantı ayarı (host/port/birim), yalnızca veri okuma onayı VE sahibin açıkça
işaretlediği «düzenli veri çekişini başlat» (`ornekleme_acik`). Bağlantı sınaması tek başına çekiş başlatmaz (v2.545 sözü korunur).
Adres kuralı ve FC3 sınırı canli_alim_service / io.canli ile aynıdır. Model çekirdeğine girmez.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pandas as pd

VARSAYILAN_PERIYOT_DK = 15
SAAT_MIN_ORNEK = 2
SAAT_MIN_KAPSAMA_DK = 10          # kısmi saat kaydı için asgari kapsama; tam saat için iki sınır gerekir
SINIR_TOLERANS_DK = 1.0           # sınır örneği «tam saatte» sayılır (saat sapması)
TOPLAMA_GERI_SAAT = 24            # her turda geriye bakılan tamamlanmış saat sayısı (kaçırılan saatler tamamlanır)
BATCH_ADI = "modbus_sunspec"
KAYNAK = "modbus_sunspec"
SINIR = "inverter_ac"
TAM, KISMI = "measured_complete", "measured_partial"


def _pj(plant: dict) -> dict:
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    return pj


def uygun(plant: dict) -> tuple[bool, str | None, dict | None]:
    """SAF. Düzenli örnekleme şartları; döner (uygun, neden, beyan). v2.554 (S4): IEC 104 hedefi de uygun — sahip STARTDT onayı + nokta tablosu şart."""
    vy = _pj(plant).get("veri_yolu")
    if not isinstance(vy, dict) or vy.get("tur") not in ("modbus_sunspec", "iec104"):
        return False, "hedef Modbus TCP / SunSpec ya da IEC 104 değil", None
    if not vy.get("baglanti"):
        return False, "bağlantı ayarı yok", vy
    if not vy.get("salt_okuma_onayi"):
        return False, "yalnızca veri okuma onayı yok", vy
    if vy.get("tur") == "iec104" and not (vy.get("startdt_onayi") and vy.get("nokta_tablosu")):
        return False, "IEC 104 için sahip STARTDT onayı ve nokta tablosu gerekir", vy
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


def ornek_al_iec104(vy: dict, simdi: datetime | None = None, sorgula=None) -> dict:
    """v2.554 (S4): IEC 104 genel sorgulama → nokta tablosuyla ölçüm → tek örnek. Yalnız sahip STARTDT onayıyla; komut yok."""
    from pvquant.io.canli import iec104_istemci as ic
    from pvquant.services import iec104_nokta_service as nk
    from pvquant.services.canli_alim_service import _cozumle, adres_izinli, hedef_dogrula
    b = vy.get("baglanti") or {}
    h = hedef_dogrula(b.get("host"), b.get("port") or ic.VARSAYILAN_PORT, 0)
    izin, neden = adres_izinli(_cozumle(h["host"]))
    if not izin:
        raise ValueError(neden)
    ayar = vy.get("iec104") or {}
    prm = ic.Parametreler.ayardan(ayar.get("parametreler"))
    r = (sorgula or ic.genel_sorgulama)(h["host"], h["port"], int(ayar.get("ca") or 1), prm, None)
    e = nk.esle(r["noktalar"], nk.dogrula(vy["nokta_tablosu"]))
    if e["eslesen"] == 0:
        raise ValueError(f"genel sorgulama {e['nokta_sayisi']} nokta döndürdü, tabloyla eşleşen alan yok; örnek alınmadı")
    o = e["olcum"]
    ts = (simdi or datetime.now(timezone.utc)).replace(microsecond=0)
    return {"ts_utc": ts, "cihaz_id": "scada", "sinir": ayar.get("sinir") or "plant_gross_ac", "profil": "iec104", "enerji_yolu": ("profil" if o.get("enerji_wh") is not None else "yok"),
            "guc_w": o.get("guc_w"), "enerji_wh": o.get("enerji_wh"), "dc_guc_w": o.get("dc_guc_w"), "durum_kodu": o.get("durum_kodu"), "olaylar": [], "ikame": e["ikame"], "eksik": len(e["eksik"])}


def ornek_al(baglanti: dict, simdi: datetime | None = None, istemci_fabrikasi=None) -> dict:
    """Cihazdan tek örnek (FC3/FC4). Döner {ts_utc, cihaz_id, sinir, profil, guc_w, enerji_wh, dc_guc_w, durum_kodu, olaylar}. Hata → istisna (çağıran günlükler)."""
    from pvquant.io.canli.modbus_tcp import ModbusTcpIstemci
    from pvquant.services.canli_alim_service import _cozumle, adres_izinli, cihaz_oku, hedef_dogrula, zaman_asimi
    h = hedef_dogrula(baglanti.get("host"), baglanti.get("port"), baglanti.get("birim"), baglanti.get("zaman_asimi_sn"), baglanti.get("profil"))
    izin, neden = adres_izinli(_cozumle(h["host"]))
    if not izin:
        raise ValueError(neden)
    fabrika = istemci_fabrikasi or (lambda host, port, birim, za: ModbusTcpIstemci(host, port, birim, za))
    with fabrika(h["host"], h["port"], h["birim"], zaman_asimi(h)) as c:
        cihaz = cihaz_oku(c, h.get("profil"))   # v2.552: SunSpec ya da üretici profili
    inv = cihaz.get("inverter")
    if not inv:
        raise ValueError("cihazda ölçüm modeli (701 ya da 101–103 / 111–113) ya da profil alanları yok; örnek alınmadı")
    ts = (simdi or datetime.now(timezone.utc)).replace(microsecond=0)
    seri = ((cihaz.get("ortak") or {}).get("seri_no") or "").strip()
    kisit = cihaz.get("kisit") or {}
    return {"ts_utc": ts, "cihaz_id": seri or (f"birim-{h['birim']}" if baglanti.get("cihazlar") or baglanti.get("_ek") else "santral"), "sinir": cihaz.get("sinir") or SINIR,
            "profil": cihaz.get("profil"), "enerji_yolu": cihaz.get("enerji_yolu"),
            "guc_w": inv.get("guc_w"), "enerji_wh": inv.get("enerji_wh"), "dc_guc_w": inv.get("dc_guc_w"), "durum_kodu": inv.get("durum_kodu"), "olaylar": inv.get("olaylar", []),
            "kisit_yuzde": kisit.get("kisma_yuzde"), "kisit_kaynak": kisit.get("kaynak") or []}   # v2.558 (V5): cihaz raporu; talimat değil


def ornekler_al(baglanti: dict, simdi: datetime | None = None, istemci_fabrikasi=None) -> tuple[list[dict], list[str]]:
    """v2.558 (V3): ana birim + aynı kayıt cihazındaki ek birimler (baglanti.cihazlar). Bir cihazın hatası diğerlerini durdurmaz; (örnekler, hatalar) döner."""
    out, hatalar = [], []
    hedefler = [baglanti] + [{**{k: v for k, v in baglanti.items() if k != "cihazlar"}, "birim": c["birim"], "profil": c.get("profil", baglanti.get("profil")), "_ek": True}
                             for c in (baglanti.get("cihazlar") or [])]
    for h in hedefler:
        try:
            out.append(ornek_al(h, simdi, istemci_fabrikasi))
        except Exception as e:   # noqa: BLE001
            hatalar.append(f"birim {h.get('birim')}: {type(e).__name__}: {e}")
    return out, hatalar


# ----------------------------------------------------------------------------- saatlik özet (SAF)
def _sinir_degeri(ts: pd.Series, deger: pd.Series, sinir: pd.Timestamp, pay_dk: float) -> tuple[float | None, bool]:
    """Sınırdaki değer: tam sınırda (±tolerans) örnek varsa o; yoksa sınırı saran, en çok pay_dk uzaklıktaki iki örnekten doğrusal interpolasyon.
    Döner (değer | None, interpolasyon_mu)."""
    tol = pd.Timedelta(minutes=SINIR_TOLERANS_DK)
    m = deger.notna()
    ts, deger = ts[m], deger[m]
    if ts.empty:
        return None, False
    yakin = (ts - sinir).abs() <= tol
    if yakin.any():
        return float(deger[yakin].iloc[0]), False
    once, sonra = ts < sinir, ts > sinir
    if not once.any() or not sonra.any():
        return None, False
    t0, t1 = ts[once].iloc[-1], ts[sonra].iloc[0]
    if (sinir - t0) > pd.Timedelta(minutes=pay_dk) or (t1 - sinir) > pd.Timedelta(minutes=pay_dk):
        return None, False
    v0, v1 = float(deger[once].iloc[-1]), float(deger[sonra].iloc[0])
    oran = (sinir - t0) / (t1 - t0)
    return v0 + (v1 - v0) * float(oran), True


def _yamuk(ts: pd.Series, y: pd.Series) -> tuple[float, float]:
    """Yamuk kuralı: ∫y dt (birim·saat) ve kapsanan süre (saat). En az iki nokta gerekir."""
    t = (ts - ts.iloc[0]).dt.total_seconds() / 3600.0   # saat (çözünürlükten bağımsız; pandas 3 datetime64[us])
    alan, sure = 0.0, 0.0
    for i in range(1, len(t)):
        dt = float(t.iloc[i] - t.iloc[i - 1])
        alan += 0.5 * (float(y.iloc[i]) + float(y.iloc[i - 1])) * dt
        sure += dt
    return alan, sure


def saatlik_ozet(ornekler: pd.DataFrame, saat_bas: datetime, periyot: int | None = None) -> dict | None:
    """SAF. Bir saatin örneklerinden (ts_utc, guc_w, enerji_wh) saatlik değer; sınır interpolasyonu için komşu örnekler de verilebilir.
    Döner {ts_utc, power_kw, energy_kwh, n, kapsama_dk, nitelik: sayac|entegrasyon, tamlik: measured_complete|measured_partial, sinir_interpolasyon}
    ya da yetersizse None. Tam saat = iki sınırda da değer (örnek ya da bir periyot içinden interpolasyon)."""
    if ornekler is None or ornekler.empty:
        return None
    pay = float(periyot or VARSAYILAN_PERIYOT_DK) + SINIR_TOLERANS_DK
    d = ornekler.copy()
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True)
    d = d.sort_values("ts_utc").drop_duplicates("ts_utc")
    sb = pd.Timestamp(saat_bas).tz_convert("UTC") if pd.Timestamp(saat_bas).tzinfo else pd.Timestamp(saat_bas, tz="UTC")
    se = sb + pd.Timedelta(hours=1)
    pencere = d[(d["ts_utc"] >= sb - pd.Timedelta(minutes=pay)) & (d["ts_utc"] <= se + pd.Timedelta(minutes=pay))]
    ic = pencere[(pencere["ts_utc"] >= sb) & (pencere["ts_utc"] <= se)]
    if len(pencere) < SAAT_MIN_ORNEK:
        return None
    guc = pd.to_numeric(pencere.get("guc_w"), errors="coerce") if "guc_w" in pencere else pd.Series(dtype=float, index=pencere.index)
    say = pd.to_numeric(pencere.get("enerji_wh"), errors="coerce") if "enerji_wh" in pencere else pd.Series(dtype=float, index=pencere.index)
    # --- güç: sınır değerleri + iç örnekler, zaman ağırlıklı
    g_bas, i1 = _sinir_degeri(pencere["ts_utc"], guc, sb, pay)
    g_bit, i2 = _sinir_degeri(pencere["ts_utc"], guc, se, pay)
    noktalar = [(sb, g_bas)] if g_bas is not None else []
    noktalar += [(t, float(v)) for t, v in zip(ic["ts_utc"], pd.to_numeric(ic.get("guc_w"), errors="coerce")) if pd.notna(v) and sb < t < se]
    noktalar += [(se, g_bit)] if g_bit is not None else []
    power_kw, kapsama_dk, ent_kwh = None, 0.0, None
    if len(noktalar) >= 2:
        tsn = pd.Series([n[0] for n in noktalar]); yn = pd.Series([n[1] for n in noktalar])
        alan, sure = _yamuk(tsn, yn)
        if sure > 0:
            power_kw = alan / sure / 1000.0
            kapsama_dk = round(sure * 60.0, 1)
            ent_kwh = alan / 1000.0
    elif len(noktalar) == 1:
        power_kw = noktalar[0][1] / 1000.0
    # --- enerji: sayaç farkı (monoton), iki sınır da varsa TAM
    sayac_pencere = say[(pencere["ts_utc"] >= sb - pd.Timedelta(minutes=pay)) & (pencere["ts_utc"] <= se + pd.Timedelta(minutes=pay))].dropna()
    monoton = len(sayac_pencere) >= 2 and sayac_pencere.is_monotonic_increasing
    energy_kwh, nitelik, tamlik, interp = None, None, None, False
    if monoton:
        c_bas, j1 = _sinir_degeri(pencere["ts_utc"], say, sb, pay)
        c_bit, j2 = _sinir_degeri(pencere["ts_utc"], say, se, pay)
        if c_bas is not None and c_bit is not None and c_bit >= c_bas:
            energy_kwh, nitelik, tamlik, interp, kapsama_dk = (c_bit - c_bas) / 1000.0, "sayac", TAM, (j1 or j2), 60.0
        else:
            ic_say = pd.to_numeric(ic.get("enerji_wh"), errors="coerce").dropna()
            if len(ic_say) >= 2:
                sure = (ic["ts_utc"][ic_say.index].iloc[-1] - ic["ts_utc"][ic_say.index].iloc[0]).total_seconds() / 60.0
                if sure >= SAAT_MIN_KAPSAMA_DK:
                    energy_kwh, nitelik, tamlik, kapsama_dk = (float(ic_say.iloc[-1]) - float(ic_say.iloc[0])) / 1000.0, "sayac", KISMI, round(sure, 1)
    if energy_kwh is None and ent_kwh is not None and kapsama_dk >= SAAT_MIN_KAPSAMA_DK:
        energy_kwh, nitelik, interp = ent_kwh, "entegrasyon", (i1 or i2)
        tamlik = TAM if (g_bas is not None and g_bit is not None) else KISMI
    if energy_kwh is None:
        return None
    return {"ts_utc": sb.to_pydatetime(), "power_kw": (round(power_kw, 3) if power_kw is not None else None), "energy_kwh": round(energy_kwh, 3),
            "n": int(len(ic)), "kapsama_dk": round(min(kapsama_dk, 60.0), 1), "nitelik": nitelik, "tamlik": tamlik, "sinir_interpolasyon": bool(interp)}


# ----------------------------------------------------------------------------- DB
def ornek_yaz(tenant_id, plant: dict, o: dict) -> int:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return s.execute(text(
            "INSERT INTO canli_ornek(tenant_id, plant_id, cihaz_id, sinir, profil, ts_utc, kaynak, guc_w, enerji_wh, dc_guc_w, durum_kodu, olaylar_json, kisit_yuzde, kanal) "
            "VALUES(:t, :p, :c, :si, :pr, :ts, :k, :g, :e, :dc, :d, CAST(:o AS jsonb), :ky, :kn) ON CONFLICT (plant_id, cihaz_id, ts_utc) DO NOTHING"),
            {"t": tenant_id, "p": plant["id"], "c": o.get("cihaz_id") or "santral", "si": o.get("sinir") or SINIR, "pr": o.get("profil"), "ts": o["ts_utc"],
             "k": ("iec104" if o.get("profil") == "iec104" else KAYNAK),
             "g": o.get("guc_w"), "e": o.get("enerji_wh"), "dc": o.get("dc_guc_w"), "d": o.get("durum_kodu"), "o": json.dumps(o.get("olaylar") or []),
             "ky": o.get("kisit_yuzde"), "kn": o.get("kanal") or "dogrudan"}).rowcount   # v2.558: kısıt yüzdesi (V5), kanal dogrudan|edge (E1)


def son_ornek(tenant_id, plant: dict) -> datetime | None:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        return s.execute(text("SELECT max(ts_utc) FROM canli_ornek WHERE plant_id=:p"), {"p": plant["id"]}).scalar()


def _ayni(a: dict, b) -> bool:
    """Gölge satırı değişmemiş mi (yeni revizyon gerekmez)?"""
    def e(x, y):
        return (x is None and y is None) or (x is not None and y is not None and abs(float(x) - float(y)) < 1e-6)
    return e(a.get("power_kw"), b["power_kw"]) and e(a.get("energy_kwh"), b["energy_kwh"]) and a.get("tamlik") == b["tamlik"] and a.get("yontem") == b["nitelik"]


def saatlik_topla(tenant_id, plant: dict, simdi: datetime | None = None, geri_saat: int = TOPLAMA_GERI_SAAT, periyot: int | None = None) -> dict:
    """Tamamlanmış son `geri_saat` saati cihaz bazında toplar: her saat (kısmi dâhil) kaynak_saatlik'e revizyonla; scada_hourly'ye yalnız tam saatler,
    var olan saat korunur. Döner {durum, n_yazilan (scada_hourly), n_golge, n_kismi, n_revizyon}."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    simdi = simdi or datetime.now(timezone.utc)
    per = periyot or periyot_dk((_pj(plant).get("veri_yolu") or {}))
    bit = simdi.replace(minute=0, second=0, microsecond=0)   # tamamlanmış son saatin sonu
    bas = bit - timedelta(hours=geri_saat)
    pay = timedelta(minutes=per + SINIR_TOLERANS_DK)
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text("SELECT ts_utc, kaynak, cihaz_id, sinir, guc_w, enerji_wh FROM canli_ornek WHERE plant_id=:p AND ts_utc >= :a AND ts_utc <= :b ORDER BY ts_utc"),
                         s.connection(), params={"p": plant["id"], "a": bas - pay, "b": bit + pay}, parse_dates=["ts_utc"])
        if df.empty:
            return {"durum": "ornek_yok", "n_yazilan": 0, "n_golge": 0, "n_kismi": 0, "n_revizyon": 0}
        var = {r[0] for r in s.execute(text("SELECT ts_utc FROM scada_hourly WHERE plant_id=:p AND ts_utc >= :a AND ts_utc < :b"), {"p": plant["id"], "a": bas, "b": bit}).all()}
        golge = {}
        try:
            for r in s.execute(text("SELECT DISTINCT ON (kaynak, cihaz_id, sinir, ts_utc) kaynak, cihaz_id, sinir, ts_utc, revizyon, power_kw, energy_kwh, tamlik, yontem FROM kaynak_saatlik "
                                    "WHERE plant_id=:p AND kaynak IN ('modbus_sunspec','iec104') AND ts_utc >= :a AND ts_utc < :b ORDER BY kaynak, cihaz_id, sinir, ts_utc, revizyon DESC"),
                               {"p": plant["id"], "a": bas, "b": bit}).mappings().all():
                golge[(r["kaynak"], r["cihaz_id"], r["sinir"], r["ts_utc"])] = dict(r)
            golge_var = True
        except Exception:   # noqa: BLE001 — göç uygulanmamışsa yalnız scada_hourly yolu
            s.rollback(); golge_var = False
        tam_satirlar, golge_satirlar, n_kismi, n_rev = [], [], 0, 0
        if "kaynak" not in df:
            df["kaynak"] = KAYNAK
        for (kaynak, cihaz, sinir), g in df.groupby([df["kaynak"].fillna(KAYNAK), df["cihaz_id"].fillna("santral"), df["sinir"].fillna(SINIR)]):
            saat = bas
            while saat < bit:
                oz = saatlik_ozet(g, saat, per)
                if oz:
                    onceki = golge.get((kaynak, cihaz, sinir, saat))
                    if onceki is None or not _ayni(onceki, oz):
                        rev = (int(onceki["revizyon"]) + 1) if onceki else 1
                        n_rev += 1 if onceki else 0
                        golge_satirlar.append({**oz, "kaynak": kaynak, "cihaz_id": cihaz, "sinir": sinir, "revizyon": rev})
                    if oz["tamlik"] == KISMI:
                        n_kismi += 1
                    elif saat not in var and sinir in (SINIR, "plant_gross_ac"):
                        tam_satirlar.append({**oz, "kaynak": kaynak, "cihaz_id": cihaz, "sinir": sinir})
                saat += timedelta(hours=1)
        if not tam_satirlar and not golge_satirlar:
            return {"durum": "yeni_saat_yok", "n_yazilan": 0, "n_golge": 0, "n_kismi": n_kismi, "n_revizyon": 0}
        batch_id = None
        if tam_satirlar:
            # Birden çok cihaz aynı saati verirse santral toplamı: tam saatler toplanır (aynı sınır, eksik cihaz yok varsayımı YOK — cihaz sayısı batch'e yazılır)
            toplam: dict[datetime, dict] = {}
            # v2.552: aynı saatte santral toplamı (plant_gross_ac, ör. SmartLogger) varsa inverter satırları toplanmaz — iki sınır karışmaz
            brut_saatler = {r["ts_utc"] for r in tam_satirlar if r["sinir"] == "plant_gross_ac"}
            for r in tam_satirlar:
                if r["sinir"] == SINIR and r["ts_utc"] in brut_saatler:
                    continue
                t = toplam.setdefault(r["ts_utc"], {"power_kw": 0.0, "energy_kwh": 0.0, "n_cihaz": 0, "sayac": 0, "sinir": r["sinir"], "kaynak": r["kaynak"]})
                t["power_kw"] += r["power_kw"] or 0.0; t["energy_kwh"] += r["energy_kwh"]; t["n_cihaz"] += 1; t["sayac"] += r["nitelik"] == "sayac"
            batch_id = s.execute(text(
                "INSERT INTO ingestion_batches(tenant_id,plant_id,filename,format_json,quality_json) VALUES(:t,:p,:f,CAST(:fmt AS jsonb),CAST(:q AS jsonb)) RETURNING id"),
                {"t": tenant_id, "p": plant["id"], "f": BATCH_ADI, "fmt": json.dumps({"kaynak": (sorted({t["kaynak"] for t in toplam.values()})[0] if len({t["kaynak"] for t in toplam.values()}) == 1 else BATCH_ADI),
                                                                                      "kaynaklar": sorted({t["kaynak"] for t in toplam.values()}), "bas": min(toplam).isoformat(), "bitis": max(toplam).isoformat(), "sinir": sorted({t["sinir"] for t in toplam.values()})}),
                 "q": json.dumps({"n": len(toplam), "sayac": sum(1 for t in toplam.values() if t["sayac"] == t["n_cihaz"]), "entegrasyon": sum(1 for t in toplam.values() if t["sayac"] < t["n_cihaz"]),
                                  "n_cihaz": max(t["n_cihaz"] for t in toplam.values()), "tamlik": TAM})}).scalar()
            n = 0
            for ts, t in sorted(toplam.items()):
                n += s.execute(text(
                    "INSERT INTO scada_hourly(tenant_id,plant_id,ts_utc,power_kw,energy_kwh,flag,batch_id,kapsama_dk,kaynak,alinma_zamani,aralik_dk,kaynak_damga_tipi) "
                    "VALUES(:t,:p,:ts,:pk,:e,'valid',:b,60,'canli',now(),60,'aralik_basi') "   # v2.573: yalnız tam saatler yazılır; v2.598: künye
                    "ON CONFLICT (plant_id, ts_utc) DO NOTHING"),
                    {"t": tenant_id, "p": plant["id"], "ts": ts, "pk": round(t["power_kw"], 3), "e": round(t["energy_kwh"], 3), "b": batch_id}).rowcount
        else:
            n = 0
        ng = 0
        if golge_var:
            for r in golge_satirlar:
                ng += s.execute(text(
                    "INSERT INTO kaynak_saatlik(tenant_id,plant_id,kaynak,cihaz_id,sinir,ts_utc,revizyon,power_kw,energy_kwh,tamlik,yontem,kapsama_dk,n_ornek,sinir_interpolasyon,batch_id) "
                    "VALUES(:t,:p,:k,:c,:si,:ts,:r,:pk,:e,:ta,:y,:kd,:n,:ip,:b) ON CONFLICT DO NOTHING"),
                    {"t": tenant_id, "p": plant["id"], "k": r["kaynak"], "c": r["cihaz_id"], "si": r["sinir"], "ts": r["ts_utc"], "r": r["revizyon"], "pk": r["power_kw"],
                     "e": r["energy_kwh"], "ta": r["tamlik"], "y": r["nitelik"], "kd": r["kapsama_dk"], "n": r["n"], "ip": r["sinir_interpolasyon"], "b": batch_id}).rowcount
    return {"durum": "ok", "n_yazilan": int(n), "n_saat": len(tam_satirlar), "n_golge": int(ng), "n_kismi": n_kismi, "n_revizyon": n_rev}


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
                if vy.get("tur") == "iec104":
                    o = ornek_al_iec104(vy, simdi); yaz(plant["tenant_id"], plant, o)
                    ozet.append(f"{ad}: örnek {o['guc_w']} W ({o.get('cihaz_id')})")
                else:   # v2.558 (V3): ana + ek cihazlar; kısmi başarı günlüğe düşer
                    liste, hatalar = ornekler_al(vy["baglanti"], simdi, istemci_fabrikasi)
                    for o in liste:
                        yaz(plant["tenant_id"], plant, o)
                    if not liste:
                        raise RuntimeError("; ".join(hatalar) or "örnek alınamadı")
                    ozet.append(f"{ad}: {len(liste)} cihaz örneklendi" + (f" ({', '.join(f'{o.get('cihaz_id')} {o['guc_w']} W' for o in liste[:3])})" if liste else "")
                                + (f"; hata: {'; '.join(hatalar)}" if hatalar else ""))
            else:
                ozet.append(f"{ad}: periyot dolmadı")
            t = topla(plant["tenant_id"], plant, simdi)
            if t.get("n_yazilan") or t.get("n_golge"):
                ozet.append(f"{ad}: {t.get('n_yazilan', 0)} tam saat yazıldı, gölge {t.get('n_golge', 0)}, kısmi {t.get('n_kismi', 0)}")
        except Exception as e:   # noqa: BLE001 — bir santralın cihaz hatası diğerlerini durdurmaz
            ozet.append(f"{ad}: HATA {type(e).__name__}: {e}")
    return "; ".join(ozet) if ozet else None


def durum(tenant_id, plant: dict) -> dict | None:
    """Veri kaynakları kartı için: son örnek, son 24 saatte örnek sayısı, bu kaynaktan yazılan son saat, cihaz sayısı, son 24 saatte kısmi saat. Tablo yoksa None."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    try:
        with tenant_baglami(tenant_id) as s:
            r = s.execute(text("SELECT max(ts_utc) AS son, count(*) FILTER (WHERE ts_utc >= now() - INTERVAL '24 hour') AS n24, "
                               "count(DISTINCT cihaz_id) FILTER (WHERE ts_utc >= now() - INTERVAL '24 hour') AS n_cihaz FROM canli_ornek WHERE plant_id=:p"),
                          {"p": plant["id"]}).mappings().first()
            ss = s.execute(text("SELECT max(sh.ts_utc) FROM scada_hourly sh JOIN ingestion_batches b ON b.id = sh.batch_id "
                                "WHERE sh.plant_id=:p AND b.format_json->>'kaynak' IN ('modbus_sunspec','iec104')"), {"p": plant["id"]}).scalar()
            try:
                kismi = s.execute(text("SELECT count(*) FROM kaynak_saatlik WHERE plant_id=:p AND kaynak IN ('modbus_sunspec','iec104') AND tamlik='measured_partial' "
                                       "AND ts_utc >= now() - INTERVAL '24 hour'"), {"p": plant["id"]}).scalar()
            except Exception:   # noqa: BLE001
                s.rollback(); kismi = None
    except Exception:   # noqa: BLE001 — göç uygulanmamışsa
        return None
    if not r or r["son"] is None:
        return {"son_ornek": None, "n24": 0, "son_saat": None, "n_cihaz": 0, "n_kismi_24": kismi}
    return {"son_ornek": r["son"], "n24": int(r["n24"] or 0), "son_saat": ss, "n_cihaz": int(r["n_cihaz"] or 0), "n_kismi_24": (int(kismi) if kismi is not None else None)}
