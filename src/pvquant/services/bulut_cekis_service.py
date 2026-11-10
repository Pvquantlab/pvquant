"""09.11.2026 v2.557 (Aşama 3, K2) — FUSIONSOLAR DÜZENLİ ÇEKİŞ (yalnız okuma; ham tabloya; birim doğrulanınca gölge görünüme).

Kota (NBI belgesi): getKpiStationHour hesap başına günde Roundup(n/100)+24 çağrı (≤100 santral → 25); bir çağrı ≤100 santral kodu alır → aynı hesaba
bağlı santrallar TEK çağrıda. Plan: hesap başına saatte 1 çağrı (bugün) + yerel 01:xx'te 1 çağrı (dün tamamlama) = 25; sayaç GUNLUK_TAVAN'da (24) durur,
biri yedek. Giriş 10 dakikada 5 → tur başına hesap başına tek giriş. Kota sayacı kayıtta (kota_gun/kota_sayac) tutulur, hesaptaki tüm kayıtlara yazılır.
Birim: belgeye göre `inverter_power` saatlik inverter üretimi kWh. GERÇEK YANITLA DOĞRULANANA KADAR yalnız ham jsonb saklanır
(bulut_saatlik_ham); sahibin/ekibin «birim doğrulandı» işaretiyle kaynak_saatlik'e (kaynak fusionsolar, cihaz bulut, sınır inverter_ac, yöntem saglayici,
tamlık measured_complete yalnız TAMAMLANMIŞ saatlerde; değişen değer yeni revizyon). scada_hourly'ye YAZILMAZ (D5: kabul sonrası ayrı iş).
Kimlik yalnız bu işte çözülür; hata metinleri kimlik içermez.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

IS_ADI = "bulut_cekis"
GUNLUK_TAVAN = 24
KAYNAK = "fusionsolar"
CIHAZ = "bulut"
SINIR = "inverter_ac"
YONTEM = "saglayici"
ALANLAR = {
    "inverter_power": {"birim": "kWh", "etiket": "inverter üretimi (saatlik)", "hedef": "energy_kwh"},
    "ongrid_power": {"birim": "kWh", "etiket": "şebekeye verilen (saatlik)"},
    "theory_power": {"birim": "kWh", "etiket": "teorik üretim (sağlayıcı modeli)"},
    "radiation_intensity": {"birim": "kWh/m²", "etiket": "ışınım (sağlayıcı sensörü)"},
    "power_profit": {"birim": "para birimi", "etiket": "gelir (sağlayıcı hesabı)"},
}
BIRIM_NOTU = "Alan anlamları ve birimleri Huawei NBI belgesine göredir (inverter_power = saatlik kWh); gerçek hesap yanıtıyla doğrulanmadan kaynak kıyasına yazılmaz."


def satirlar(data: list[dict]) -> list[dict]:
    """SAF. getKpiStationHour data[] → [{kimlik, ts_utc, alanlar}]. collectTime ms (saat başı)."""
    out = []
    for d in data or []:
        try:
            ts = datetime.fromtimestamp(int(d["collectTime"]) / 1000.0, tz=timezone.utc)
        except (KeyError, TypeError, ValueError):
            continue
        out.append({"kimlik": str(d.get("stationCode") or ""), "ts_utc": ts, "alanlar": dict(d.get("dataItemMap") or {})})
    return out


def gunler(simdi: datetime, tz_adi: str | None) -> list[datetime]:
    """SAF. Çekilecek günler (yerel gece yarısı, saat dilimli): bugün; yerel saat 01:xx ise dün de (geç gelen saatlerin tamamlanması)."""
    tz = ZoneInfo(tz_adi or "Europe/Istanbul")
    yerel = simdi.astimezone(tz)
    bugun = yerel.replace(hour=0, minute=0, second=0, microsecond=0)
    return [bugun, bugun - timedelta(days=1)] if yerel.hour == 1 else [bugun]


def kota_sayaci(grup: list[dict], bugun: date) -> int:
    """SAF. Aynı hesaptaki kayıtların bugünkü en yüksek sayacı (hepsine aynı değer yazılır)."""
    return max((int(k.get("kota_sayac") or 0) for k in grup if _gun(k.get("kota_gun")) == bugun), default=0)


def _gun(v) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def siniflandir(msg: str) -> str:
    m = msg or ""
    if "(305)" in m or "(401)" in m or "kimlik" in m:
        return "kimlik_hatasi"
    if "(407)" in m or "20618" in m or "istek sınırı" in m:
        return "kota"
    return "hata"


def kayitlar_cekis_acik() -> list[dict]:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    with sistem_baglami() as s:
        return [dict(r) for r in s.execute(text(
            "SELECT k.*, p.tz AS tz, p.name AS santral_adi FROM bulut_kimlik k JOIN plants p ON p.id = k.plant_id JOIN tenants t ON t.id = k.tenant_id "
            "WHERE k.cekis_acik AND t.status='active' AND NOT p.archived ORDER BY k.saglayici, k.bolge")).mappings().all()]


def tur(simdi: datetime | None = None, kayitlar: list[dict] | None = None, coz=None, istemci_fabrikasi=None, ham_yaz=None, golge_yaz=None, guncelle=None, kimlik_guncelle=None) -> str | None:
    """Bir tur: hesap başına tek giriş; gün başına toplu (TOPLU sağlayıcı) ya da santral başına çağrı; ham yazım; «birim doğrulandı» ise gölge yazım; kota sayacı
    sağlayıcının günlük tavanına göre (v2.562: sicildeki her etkin bağlayıcı; token yenilemesi zarf şifreli saklanır). Kayıt yoksa None."""
    from pvquant.io.bulut import AKTIF_SAGLAYICILAR
    from pvquant.services import bulut_kimlik_service as bk
    simdi = simdi or datetime.now(timezone.utc)
    kayitlar = kayitlar_cekis_acik() if kayitlar is None else kayitlar
    if not kayitlar:
        return None
    coz = coz or bk.coz_kimlik; ham_yaz = ham_yaz or _ham_yaz; golge_yaz = golge_yaz or _golge_yaz; guncelle = guncelle or _guncelle; kimlik_guncelle = kimlik_guncelle or bk.kimlik_guncelle
    ozet: list[str] = []
    gruplar: dict[tuple, list[dict]] = {}
    for k in kayitlar:
        sg = k.get("saglayici"); sicil = AKTIF_SAGLAYICILAR.get(sg or "")
        if not sicil or not sicil.get("sinif"):
            guncelle(k, "saglayici_desteklenmiyor", "bu sağlayıcı için düzenli çekiş bağlayıcısı yok", simdi, None, None); continue
        if not k.get("dis_kimlik"):   # v2.564: sahip onayı sonrası santral seçimi ertelenmiş — seçilmeden sağlayıcıya çağrı yapılmaz
            guncelle(k, "santral_secilmedi", "sağlayıcı santralı seçilmedi; Santralim ekranından seçin", simdi, None, None); ozet.append(f"{k.get('santral_adi') or k.get('plant_id')}: santral seçilmedi"); continue
        try:
            kim = coz(k)
        except Exception as e:   # noqa: BLE001 — KEK yok/uyuşmuyor: kimlik metni asla dönmez
            guncelle(k, "kasa_hatasi", f"kimlik çözülemedi: {e}", simdi, None, None); ozet.append(f"{k.get('santral_adi') or k.get('plant_id')}: kimlik çözülemedi"); continue
        gruplar.setdefault((sg, k.get("bolge") or sicil.get("varsayilan_bolge"), tuple(sorted((a, str(v)) for a, v in kim.items()))), []).append(k)
    for (sg, bolge, kim_t), grup in gruplar.items():
        sicil = AKTIF_SAGLAYICILAR[sg]; tavan = int(sicil.get("gunluk_tavan") or GUNLUK_TAVAN); sinif = istemci_fabrikasi or sicil["sinif"]; kim = dict(kim_t)
        tz_adi = grup[0].get("tz") or "Europe/Istanbul"
        bugun = simdi.astimezone(ZoneInfo(tz_adi)).date()
        sayac = kota_sayaci(grup, bugun)
        gl = gunler(simdi, tz_adi)
        kodlar = sorted({str(k["dis_kimlik"]) for k in grup if k.get("dis_kimlik")})
        tahmin = len(gl) * (sinif.cagri_tahmini(len(kodlar)) if hasattr(sinif, "cagri_tahmini") else 1)
        if sayac + tahmin > tavan:
            for k in grup:
                guncelle(k, "kota_doldu", f"günlük çağrı tavanı ({tavan}) doldu; çekiş yarın sürer", simdi, bugun, sayac)
            ozet.append(f"{len(grup)} santral: kota doldu ({sayac}/{tavan})"); continue
        c = None
        try:
            c = sinif(bolge)
            c.kimlik_yenile = lambda yeni, grup=grup, sg=sg: [kimlik_guncelle(k["tenant_id"], k["plant_id"], sg, yeni) for k in grup]   # Sungrow token yenilemesi → zarf şifreli
            c.giris(kim)
            n_ham = n_golge = 0
            for gun in gl:
                st = c.saatlik_ham(kodlar, gun)
                for k in grup:
                    kendi = [r for r in st if r["kimlik"] == str(k.get("dis_kimlik"))]
                    if not kendi:
                        continue
                    n_ham += ham_yaz(k, kendi)
                    if k.get("birim_dogrulandi"):
                        n_golge += golge_yaz(k, kendi, simdi)
            sayac += int(getattr(c, "cagri", 0) or len(gl))
            for k in grup:
                guncelle(k, "ok", None, simdi, bugun, sayac)
            ozet.append(f"{len(grup)} santral · {len(gl)} gün · {n_ham} ham saat · gölge {n_golge} · çağrı {sayac}/{tavan}")
        except Exception as e:   # noqa: BLE001 — bir hesabın hatası diğerlerini durdurmaz; metinde kimlik yok
            msg = f"{type(e).__name__}: {e}"; d = siniflandir(msg)
            for k in grup:
                guncelle(k, d, msg, simdi, bugun, sayac)
            ozet.append(f"{len(grup)} santral: HATA {d} — {msg}")
        finally:
            if c is not None:
                try:
                    c.kapat()
                except Exception:   # noqa: BLE001
                    pass
    return "; ".join(ozet) if ozet else None


def _ham_yaz(k: dict, satirlar_: list[dict]) -> int:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    n = 0
    with tenant_baglami(k["tenant_id"]) as s:
        for r in satirlar_:
            s.execute(text("INSERT INTO bulut_saatlik_ham(tenant_id, plant_id, saglayici, ts_utc, dis_kimlik, alanlar) VALUES (:t, :p, :sg, :ts, :d, CAST(:a AS jsonb)) "
                           "ON CONFLICT (plant_id, saglayici, ts_utc) DO UPDATE SET alanlar=EXCLUDED.alanlar, dis_kimlik=EXCLUDED.dis_kimlik, alinma=now()"),
                      {"t": k["tenant_id"], "p": k["plant_id"], "sg": k["saglayici"], "ts": r["ts_utc"], "d": r["kimlik"], "a": json.dumps(r["alanlar"], ensure_ascii=False)})
            n += 1
    return n


def _golge_yaz(k: dict, satirlar_: list[dict], simdi: datetime) -> int:
    """Yalnız birim_dogrulandi: tamamlanmış saatlerin inverter_power'ı kaynak_saatlik'e; değer değişmişse yeni revizyon."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    n = 0
    with tenant_baglami(k["tenant_id"]) as s:
        for r in satirlar_:
            if r["ts_utc"] + timedelta(hours=1) > simdi:
                continue   # saat tamamlanmadı
            e = r["alanlar"].get("enerji_kwh_belge")   # v2.562: sağlayıcıdan bağımsız — bağlayıcı belgeye göre saatlik kWh verirse
            if e is None:
                continue
            try:
                e = float(e)
            except (TypeError, ValueError):
                continue
            son = s.execute(text("SELECT energy_kwh, revizyon FROM kaynak_saatlik WHERE plant_id=:p AND kaynak=:k AND cihaz_id=:c AND sinir=:si AND ts_utc=:ts "
                                 "ORDER BY revizyon DESC LIMIT 1"), {"p": k["plant_id"], "k": k.get("saglayici") or KAYNAK, "c": CIHAZ, "si": SINIR, "ts": r["ts_utc"]}).mappings().first()
            if son is not None and son["energy_kwh"] is not None and abs(float(son["energy_kwh"]) - e) < 0.05:
                continue
            s.execute(text("INSERT INTO kaynak_saatlik(tenant_id, plant_id, kaynak, cihaz_id, sinir, ts_utc, revizyon, power_kw, energy_kwh, tamlik, yontem, kapsama_dk) "
                           "VALUES (:t, :p, :k, :c, :si, :ts, :r, :pw, :e, 'measured_complete', :y, 60)"),
                      {"t": k["tenant_id"], "p": k["plant_id"], "k": k.get("saglayici") or KAYNAK, "c": CIHAZ, "si": SINIR, "ts": r["ts_utc"], "r": (int(son["revizyon"]) + 1 if son else 1),
                       "pw": e, "e": e, "y": YONTEM})
            n += 1
    return n


def _guncelle(k: dict, durum: str, hata: str | None, simdi: datetime, bugun: date | None, sayac: int | None) -> None:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(k["tenant_id"]) as s:
        s.execute(text("UPDATE bulut_kimlik SET son_cekis=:z, son_durum=:d, son_hata=:h, kota_gun=COALESCE(:g, kota_gun), kota_sayac=COALESCE(:s, kota_sayac), guncelleme=now() WHERE id=:i"),
                  {"z": simdi, "d": durum, "h": (hata[:500] if hata else None), "g": bugun, "s": sayac, "i": k["id"]})


def ham_son(tenant_id, plant_id, saglayici: str | None = None, n: int = 24) -> list[dict]:
    """UI: son n ham saat (alanlar olduğu gibi). Tablo yoksa boş."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    try:
        with tenant_baglami(tenant_id) as s:
            rows = s.execute(text("SELECT saglayici, ts_utc, dis_kimlik, alanlar, alinma FROM bulut_saatlik_ham WHERE plant_id=CAST(:p AS uuid) "
                                  + ("AND saglayici=:sg " if saglayici else "") + "ORDER BY ts_utc DESC LIMIT :n"),
                             {"p": str(plant_id), "sg": saglayici, "n": int(n)}).mappings().all()
    except Exception:   # noqa: BLE001
        return []
    return [{"saglayici": r["saglayici"], "ts_utc": r["ts_utc"].isoformat(), "dis_kimlik": r["dis_kimlik"], "alanlar": r["alanlar"], "alinma": r["alinma"].isoformat()} for r in rows]


def saglayici_alanlari() -> dict:
    """v2.562: UI için sağlayıcı → {alanlar, birim_notu, gunluk_tavan} (sicilden)."""
    from pvquant.io.bulut import AKTIF_SAGLAYICILAR
    return {k: {"alanlar": v["alanlar"], "birim_notu": v["birim_notu"], "gunluk_tavan": v["gunluk_tavan"], "toplu": v["toplu"]} for k, v in AKTIF_SAGLAYICILAR.items()}
