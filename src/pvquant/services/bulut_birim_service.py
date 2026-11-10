"""10.11.2026 v2.565 (Aşama 3, D2 doğrulama protokolü adım 3) — BULUT BİRİM KIYASI: çekilen ham saatler × portal dışa aktarımı.

Bulut bağlayıcıları alanların anlamını ÜRETİCİ BELGESİNDEN alır (ör. FusionSolar `inverter_power` = saatlik kWh) ve bu yorum gerçek hesapla görülmemiştir
(B kapısı G07/U04: «inverter_power alanını kW veya kWh diye yayınlama»). Sahip, portalın kendi saatlik üretim dışa aktarımını (CSV: zaman, kwh) yükler; bu
servis aynı saatlerdeki ham alanları birkaç yorum (hipotez) altında kıyaslar: kWh doğrudan · Wh/1000 · MWh×1000 · kümülatif fark (kWh) · kümülatif fark (Wh).
Her alan için en iyi hipotez ve tolerans oranı (%2 ya da 0,5 kWh/saat; ≥24 ortak saat) raporlanır. «Belgeye göre» alan (`enerji_kwh_belge`, hipotez kWh) uyumluysa
`belge_uyumlu` → sahip «birim doğrulandı» işaretini ancak o zaman koyabilir (bulut_kimlik_service.ayarla kapısı). Başka bir alan/hipotez uyumlu ama belge
yorumu değilse `belgeyle_celisiyor`: işaret konamaz, bağlayıcının belge yorumu düzeltilmeden gölge görünüme yazılmaz (sahte doğrulama yok).
10.11 inceleme: tolerans oranı YALNIZ ÜRETİM OLAN saatlerde ölçülür (referans > 2×0,5 kWh). Gece/üretimsiz saatlerde 0 ≈ 0 her yorumla «toleransta»
göründüğü için sayılmaz; en az 8 üretimli ortak saat yoksa karar verilmez (yalnız gece saatlerinden sahte «uyumlu» çıkmaz).
Ham referans saklanmaz; yalnız özet `bulut_kimlik.birim_kanit` (jsonb) sütununa düşer. Referans okuyucu pilot kitiyle ortak (`pilot_service.referans_csv_oku`).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pvquant.services.pilot_service import MIN_ORTAK_SAAT, TOL_KWH, TOL_PCT, _tr   # 10.11 inceleme: Türkçe ondalık tek yerde

HIPOTEZLER = {"kwh": ("saatlik kWh (doğrudan)", lambda seri, t: seri.get(t)),
              "wh": ("saatlik Wh (÷1000)", lambda seri, t: None if seri.get(t) is None else seri[t] / 1000.0),
              "mwh": ("saatlik MWh (×1000)", lambda seri, t: None if seri.get(t) is None else seri[t] * 1000.0),
              "kumulatif_kwh": ("kümülatif kWh (saat sonu − saat başı)", lambda seri, t: None if seri.get(t) is None or seri.get(t + timedelta(hours=1)) is None else seri[t + timedelta(hours=1)] - seri[t]),
              "kumulatif_wh": ("kümülatif Wh (fark ÷1000)", lambda seri, t: None if seri.get(t) is None or seri.get(t + timedelta(hours=1)) is None else (seri[t + timedelta(hours=1)] - seri[t]) / 1000.0)}
BELGE_ALANI = "enerji_kwh_belge"
BELGE_HIPOTEZI = "kwh"
MIN_URETIMLI_SAAT = 8   # 10.11 inceleme: karar için üretim olan en az bu kadar ortak saat (kış gününde bir gün yeter)


def _ts(v) -> datetime:
    t = datetime.fromisoformat(v) if isinstance(v, str) else v
    return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def _seriler(ham: list[dict]) -> dict[str, dict[datetime, float]]:
    out: dict[str, dict[datetime, float]] = {}
    for r in ham:
        t = _ts(r["ts_utc"])
        for a, v in (r.get("alanlar") or {}).items():
            if isinstance(v, bool) or v is None or v == "":
                continue
            try:
                f = float(v)
            except (TypeError, ValueError):
                continue
            out.setdefault(a, {})[t] = f
    return out


def _hipotez_kiyas(seri: dict[datetime, float], referans: list[dict], hip: str, tol_pct: float, tol_kwh: float) -> dict:
    _, f = HIPOTEZLER[hip]
    n = n_ur = n_tol = 0; ape = []; top_ref = top_h = 0.0
    for r in referans:
        t = _ts(r["ts_utc"]); ref = float(r["kwh"])
        e = f(seri, t)
        if e is None:
            continue
        n += 1; top_ref += ref; top_h += e
        if ref > 0:
            ape.append(abs(e - ref) / ref)
        if ref > 2 * tol_kwh:   # üretim olan saat: 0 ≈ 0 eşleşmesi kanıt sayılmaz
            n_ur += 1
            n_tol += int(abs(e - ref) <= max(tol_kwh, tol_pct / 100.0 * abs(ref)))
    return {"hipotez": hip, "n_ortak": n, "n_uretimli": n_ur, "n_tolerans_ici": n_tol, "oran": (round(n_tol / n_ur, 4) if n_ur else None), "mape_pct": (round(sum(ape) / len(ape) * 100, 2) if ape else None),
            "toplam_fark_pct": (round((top_h - top_ref) / top_ref * 100, 2) if top_ref > 0 else None)}


def kiyas(ham: list[dict], referans: list[dict], alan_etiketleri: dict | None = None, tol_pct: float = TOL_PCT, tol_kwh: float = TOL_KWH) -> dict:
    """SAF. ham: [{ts_utc, alanlar{alan: sayı}}] (bulut_saatlik_ham satırları); referans: [{ts_utc, kwh}] (portal dışa aktarımı). Dönen özet gizli içermez."""
    seriler = _seriler(ham)
    alan_etiketleri = alan_etiketleri or {}
    alanlar = []
    saatler = [_ts(r["ts_utc"]) for r in referans]
    belge_seri = seriler.get(BELGE_ALANI)
    for a, seri in seriler.items():
        if a != BELGE_ALANI and belge_seri is not None and any(t in belge_seri for t in saatler) and all(seri.get(t) == belge_seri.get(t) for t in saatler):
            continue   # belge alanının birebir kaynağı (ör. inverter_power): aynı sayılar iki satır gösterilmez
        adaylar = [_hipotez_kiyas(seri, referans, h, tol_pct, tol_kwh) for h in HIPOTEZLER]
        adaylar = [x for x in adaylar if x["n_ortak"]]
        if not adaylar:
            continue
        en = max(adaylar, key=lambda x: ((x["oran"] or 0), -list(HIPOTEZLER).index(x["hipotez"])))
        sonuc = "yetersiz" if en["n_ortak"] < MIN_ORTAK_SAAT or en["n_uretimli"] < MIN_URETIMLI_SAAT else "uyumlu" if (en["oran"] or 0) >= 0.95 else "uyumsuz"
        alanlar.append({"alan": a, "etiket": (alan_etiketleri.get(a) or {}).get("etiket") if isinstance(alan_etiketleri.get(a), dict) else alan_etiketleri.get(a), **en,
                        "hipotez_etiketi": HIPOTEZLER[en["hipotez"]][0], "sonuc": sonuc})
    alanlar.sort(key=lambda x: (x["sonuc"] != "uyumlu", -(x["oran"] or 0)))
    belge = next((x for x in alanlar if x["alan"] == BELGE_ALANI), None)
    belge_uyumlu = bool(belge and belge["sonuc"] == "uyumlu" and belge["hipotez"] == BELGE_HIPOTEZI)
    baska = [x for x in alanlar if x["sonuc"] == "uyumlu" and not (x["alan"] == BELGE_ALANI and x["hipotez"] == BELGE_HIPOTEZI)]
    n_ortak = max((x["n_ortak"] for x in alanlar), default=0)
    n_uretimli = max((x["n_uretimli"] for x in alanlar), default=0)
    if not alanlar or n_ortak < MIN_ORTAK_SAAT:
        sonuc, metin = "yetersiz", f"Yalnız {n_ortak} ortak saat (en az {MIN_ORTAK_SAAT} gerekir); karar verilmez. Çekiş en az bir tam gün sürmeli ve dışa aktarım aynı günleri kapsamalı."
    elif n_uretimli < MIN_URETIMLI_SAAT:
        sonuc, metin = "yetersiz", (f"{n_ortak} ortak saatin yalnız {n_uretimli} tanesinde üretim var (en az {MIN_URETIMLI_SAAT} gerekir); karar verilmez. "
                                     "Üretimsiz saatler her yorumla uyuştuğu için kanıt sayılmaz; dışa aktarım üretim olan en az bir günü kapsamalı.")
    elif belge_uyumlu:
        sonuc, metin = "belge_uyumlu", (f"Belgeye göre saatlik kWh yorumu portal dışa aktarımıyla uyumlu: üretim olan {belge['n_uretimli']} ortak saatin {belge['n_tolerans_ici']} tanesi toleransta "
                                         f"(%{_tr((belge['oran'] or 0) * 100, '.1f')}). Bu kanıt «birim doğrulandı» işareti için yeterlidir.")
    elif baska:
        b = baska[0]
        sonuc, metin = "belgeyle_celisiyor", (f"Belge yorumu uyumsuz; «{b['etiket'] or b['alan']}» alanı «{b['hipotez_etiketi']}» yorumuyla uyumlu (%{_tr((b['oran'] or 0) * 100, '.1f')}). Bağlayıcının belge yorumu "
                                               "düzeltilmeden «birim doğrulandı» işaretlenemez; bu bulgu geliştiriciye iletilir.")
    else:
        sonuc, metin = "uyumsuz", "Hiçbir alan hiçbir yorumla toleransta değil; ölçüm sınırı (inverter/sayaç), saat dilimi ya da santral eşlemesi incelenmeli. «Birim doğrulandı» işaretlenemez."
    gosterilen = alanlar[:8]
    if belge is not None and belge not in gosterilen:   # çok alanlı sağlayıcıda belge satırı listeden düşmesin
        gosterilen = alanlar[:7] + [belge]
    return {"sonuc": sonuc, "metin": metin, "belge_uyumlu": belge_uyumlu and sonuc == "belge_uyumlu", "n_referans": len(referans), "n_ortak": n_ortak, "n_uretimli": n_uretimli, "alanlar": gosterilen,
            "tolerans": {"pct": tol_pct, "kwh": tol_kwh, "min_ortak_saat": MIN_ORTAK_SAAT, "min_uretimli_saat": MIN_URETIMLI_SAAT},
            "not": "Kıyas, portalın kendi saatlik dışa aktarımını referans alır; iki kaynak da aynı sağlayıcıdan geldiği için bu bir BİRİM/ANLAM doğrulamasıdır, ölçüm doğruluğu kanıtı değildir."}


def ham_aralik(tenant_id, plant_id, saglayici: str, bas: datetime, bit: datetime) -> list[dict]:
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text("SELECT ts_utc, alanlar FROM bulut_saatlik_ham WHERE plant_id=CAST(:p AS uuid) AND saglayici=:sg AND ts_utc >= :b AND ts_utc < :e ORDER BY ts_utc"),
                         {"p": str(plant_id), "sg": saglayici, "b": bas, "e": bit}).mappings().all()
    return [{"ts_utc": r["ts_utc"], "alanlar": r["alanlar"]} for r in rows]


def degerlendir(tenant_id, plant_id, saglayici: str, referans: list[dict], aktor_id=None, dosya: str | None = None, simdi: datetime | None = None, ham=None, yaz=None) -> dict:
    """DB: referans aralığındaki ham saatler → kıyas → özet bulut_kimlik.birim_kanit'e (ham referans saklanmaz)."""
    from pvquant.io.bulut import AKTIF_SAGLAYICILAR
    from pvquant.services import bulut_kimlik_service as bk
    simdi = simdi or datetime.now(timezone.utc)
    bas = min(_ts(r["ts_utc"]) for r in referans); bit = max(_ts(r["ts_utc"]) for r in referans) + timedelta(hours=2)   # kümülatif fark için bir saat pay
    satirlar = (ham or ham_aralik)(tenant_id, plant_id, saglayici, bas, bit)
    etiketler = (AKTIF_SAGLAYICILAR.get(saglayici) or {}).get("alanlar") or {}
    k = kiyas(satirlar, referans, etiketler)
    k.update({"zaman": simdi.isoformat(timespec="seconds"), "aktor_id": str(aktor_id) if aktor_id else None, "dosya": dosya, "n_ham_saat": len(satirlar),
              "uyari": referans[0].get("_uyari") if referans else None})
    n = (yaz or bk.birim_kanit_yaz)(tenant_id, plant_id, saglayici, k)
    k["kaydedildi"] = bool(n)
    return k
