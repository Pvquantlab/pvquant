"""09.11.2026 v2.555 (Aşama 5, V2) — CİHAZ DURUMUNDAN OLAY ADAYI (SAF + okuma). Otomatik olay KAYDETMEZ: sahibe aday listesi gösterir, kayıt Olay kaydı
sayfasından elle yapılır (olay kaydı değiştirilemez/silinemez ilkesi; cihaz alarmı = sahadaki arızanın kanıtı değil, işareti).

Girdi: canli_ornek (Modbus/SunSpec, üretici profili, IEC 104) — durum_kodu (103.St eşlemesi: 7 arıza, 1 kapalı, 8 beklemede …) ve olay bitleri
(SunSpec Evt1 / 701 Alrm). Aday: aynı cihazda ardışık «arıza ya da alarm bitli» örnek koşusu (en az 2 örnek ya da ≥ 10 dk); bitiş = koşunun son örneği,
sonraki örnek normale dönmüşse «bitti», dönmemişse «sürüyor». Ayrıca örnekleme açıkken 3 periyottan uzun boşluk = «iletişim kopukluğu» (olay türü değil,
bilgi; üretim 0 sayılmaz — Codex DQ01/DQ21). Mevcut olay kaydıyla çakışan aday «kayıtlı» işaretlenir, gizlenmez.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

ARIZA_KODLARI = {7}
MIN_ORNEK = 2
MIN_SURE_DK = 10.0
BOSLUK_KATSAYI = 3


def adaylar(ornekler: list[dict], mevcut_olaylar: list[dict] | None = None, periyot_dk: int = 15, simdi: datetime | None = None) -> list[dict]:
    """SAF. ornekler: [{ts_utc, cihaz_id, durum_kodu, olaylar (liste|None), guc_w}] (sıra önemsiz). Döner aday listesi (yeni → eski)."""
    simdi = simdi or datetime.now(timezone.utc)
    mevcut = mevcut_olaylar or []
    by_cihaz: dict[str, list[dict]] = {}
    for o in ornekler:
        by_cihaz.setdefault(str(o.get("cihaz_id") or "santral"), []).append(o)
    out: list[dict] = []
    bosluk = timedelta(minutes=BOSLUK_KATSAYI * max(1, int(periyot_dk)))

    def _ts(o):
        t = o["ts_utc"]
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)

    def _kayitli(bas: datetime, bit: datetime | None) -> bool:
        b1 = bit or simdi
        for m in mevcut:
            mb, me = m.get("baslangic"), m.get("bitis")
            if mb is None:
                continue
            mb = mb if mb.tzinfo else mb.replace(tzinfo=timezone.utc)
            me = (me if me.tzinfo else me.replace(tzinfo=timezone.utc)) if me else None
            if mb < b1 and (me is None or me > bas):
                return True
        return False

    for cihaz, lst in by_cihaz.items():
        lst = sorted(lst, key=_ts)
        kosu: list[dict] = []
        onceki_ts = None
        for o in lst + [None]:
            if o is not None:
                t = _ts(o)
                if onceki_ts is not None and t - onceki_ts > bosluk:
                    out.append({"tur": "iletisim_kopuklugu", "tur_etiketi": "iletişim kopukluğu (örnek gelmedi)", "cihaz_id": cihaz, "bas": onceki_ts.isoformat(), "bit": t.isoformat(),
                                "sure_dk": round((t - onceki_ts).total_seconds() / 60.0, 1), "ornek_sayisi": 0, "kodlar": [], "durum": "bitti",
                                "kayitli": _kayitli(onceki_ts, t), "not": "Örnekleme açıkken 3 periyottan uzun boşluk; üretim sıfır sayılmaz, olay değildir."})
                onceki_ts = t
            alarm = o is not None and ((o.get("durum_kodu") in ARIZA_KODLARI) or bool(o.get("olaylar")))
            if alarm:
                kosu.append(o); continue
            if kosu:
                bas, son = _ts(kosu[0]), _ts(kosu[-1])
                bit = _ts(o) if o is not None else None
                kosu_sure = ((son if bit is not None else simdi) - bas).total_seconds() / 60.0   # eşik: örneklerin yayıldığı süre; sürüyorsa şimdiye kadar
                if len(kosu) >= MIN_ORNEK or kosu_sure >= MIN_SURE_DK:   # tek örnekle bitmiş koşu (gürültü) aday değil
                    kodlar = sorted({k for x in kosu for k in (x.get("olaylar") or [])})
                    out.append({"tur": "ariza", "tur_etiketi": "arıza / alarm", "cihaz_id": cihaz, "bas": bas.isoformat(), "bit": bit.isoformat() if bit else None,
                                "sure_dk": round(((bit or simdi) - bas).total_seconds() / 60.0, 1), "ornek_sayisi": len(kosu), "kodlar": kodlar,
                                "durum": "bitti" if bit else "suruyor", "kayitli": _kayitli(bas, bit),
                                "not": "Cihaz durumu arıza ya da alarm biti; olay kaydına almak sahibin kararıdır (EAK gerekçesi ve arıza sayacı buna bağlı)."})
                kosu = []
        # v2.558 (V5): cihazın raporladığı güç kısması koşusu (kisit_yuzde > 0) — aynı eşik; türü «kısıt (cihaz raporu)»; talimat mı PPC mi sahibin kararı
        kk: list[dict] = []
        for o in lst + [None]:
            if o is not None and (o.get("kisit_yuzde") or 0) > 0:
                kk.append(o); continue
            if kk:
                bas, son = _ts(kk[0]), _ts(kk[-1])
                bit = _ts(o) if o is not None else None
                kosu_sure = ((son if bit is not None else simdi) - bas).total_seconds() / 60.0
                if len(kk) >= MIN_ORNEK or kosu_sure >= MIN_SURE_DK:
                    y = [float(x["kisit_yuzde"]) for x in kk]
                    kaynak = sorted({k for x in kk for k in (x.get("kisit_kaynak") or [])})
                    out.append({"tur": "kisit", "tur_etiketi": "güç kısması (cihaz raporu)", "cihaz_id": cihaz, "bas": bas.isoformat(), "bit": bit.isoformat() if bit else None,
                                "sure_dk": round(((bit or simdi) - bas).total_seconds() / 60.0, 1), "ornek_sayisi": len(kk), "kodlar": kaynak,
                                "kisma_yuzde_ort": round(sum(y) / len(y), 1), "kisma_yuzde_maks": round(max(y), 1),
                                "durum": "bitti" if bit else "suruyor", "kayitli": _kayitli(bas, bit),
                                "not": "Cihaz güç kısması raporladı; EDAŞ/TEİAŞ talimatı (YAT/YAL) mı, PPC ayarı mı, cihaz koruması mı buradan bilinmez. Talimatsa Olay kaydına talimat türüyle işlenir; sapma açıklamasında ayrışır."})
                kk = []
    out.sort(key=lambda a: a["bas"], reverse=True)
    return out


def listele(tenant_id, plant: dict, saat: int = 72, simdi: datetime | None = None) -> dict:
    """DB: son `saat` saatin örnekleri + mevcut olaylar → adaylar. Tablo yoksa boş."""
    import json
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import olay_service
    from pvquant.services.canli_ornekleme_service import _pj, periyot_dk
    simdi = simdi or datetime.now(timezone.utc)
    bas = simdi - timedelta(hours=saat)
    try:
        with tenant_baglami(tenant_id) as s:
            rows = s.execute(text("SELECT ts_utc, cihaz_id, durum_kodu, olaylar_json, guc_w, kisit_yuzde FROM canli_ornek WHERE plant_id=:p AND ts_utc >= :a ORDER BY ts_utc"),
                             {"p": plant["id"], "a": bas}).mappings().all()
    except Exception:   # noqa: BLE001 — göç uygulanmamışsa
        return {"adaylar": [], "pencere_saat": saat, "n_ornek": 0, "not": "canlı örnek tablosu yok"}
    ornekler = [{"ts_utc": r["ts_utc"], "cihaz_id": r["cihaz_id"], "durum_kodu": r["durum_kodu"], "guc_w": r["guc_w"], "kisit_yuzde": r["kisit_yuzde"],
                 "olaylar": (r["olaylar_json"] if isinstance(r["olaylar_json"], list) else (json.loads(r["olaylar_json"]) if r["olaylar_json"] else []))} for r in rows]
    mevcut = olay_service.aralik(tenant_id, plant["id"], bas, simdi) if ornekler else []
    per = periyot_dk((_pj(plant).get("veri_yolu") or {}))
    return {"adaylar": adaylar(ornekler, mevcut, per, simdi), "pencere_saat": saat, "n_ornek": len(ornekler), "periyot_dk": per,
            "not": "Adaylar cihaz durumundan türetilir; olay kaydına alınması sahibin kararıdır. «Kayıtlı» olanlar mevcut bir olayla çakışıyor."}
