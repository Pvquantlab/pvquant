"""Alarm v0 — El Kitabı P4 §3 birebir (Zeyilname v2.11 · P4-A paketi).
İKİ kural, fazlası YASAK:
  (1) veri_gelmedi : son SCADA 48 saatten eski
  (2) skill_dustu  : 0-24s MAPE 7 gün üst üste 30g ortalamasının 1.5 katı
Spam kilidi: aynı kural aynı santral için günde en çok 1 alarm.
SMTP yoksa (PVQ_SMTP_HOST tanımsız) mail atlanır, alerts satırı yazılır.

v2.265 (Dalga 5.17): EK KURALLAR yalnız santral bazında AÇIKÇA seçilirse (plants.params_json.alarm_kurallari)
çalışır — varsayılan hâlâ iki kural. Kütüphane: pvquant.ext.platform.alarm.KUTUPHANE (pr_dustu,
clipping_orani_yuksek, iletisim_kesintisi). Eşikler params_json.alarm_esik'ten. Okundu/atama: acked_by/acked_at/assigned_to.

v2.519 (P7a, yol haritası): kural bazlı sıklık (iletişim kesintisi saatlik, teminat 10:15 / avans 14:45 TSİ iş günü, PTF 14:40, takvim
günlük), santral bazlı alıcılar (params_json.alarm_alicilar + PVQ_ALARM_TO) ve webhook olayı «alarm.yeni»; yeni kurallar takvim_son_tarih
(olay başına tek alarm, mesaj birebir eşleşmesiyle), ptf_dusuk_saat (yarının gün öncesi PTF'si eşik/V altında), ariza_sayaci_yaklasti
(elle girilen aylık arıza sayısı), teminat_hatirlatma / avans_hatirlatma; kgup_teslim_gecikti artık «bildirildi» beyanına da bakar."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from pvquant.db import tenant_baglami
from pvquant.ext.platform.alarm import KUTUPHANE

# v2.265: seçilebilir ek kurallar (ürün kararı: yalnız bu üçü; ping/KGÜP/dengesizlik kuralları veri kaynağı olmadan açılmaz)
EK_KURALLAR = ("pr_dustu", "clipping_orani_yuksek", "iletisim_kesintisi", "kullanilabilirlik_dustu",
               "kgup_teslim_gecikti", "dengesizlik_asimi", "kgup_revizyon_onerisi",   # v2.288: kütüphanenin tamamı seçilebilir; v2.507: F-10 revizyon
               "takvim_son_tarih", "ptf_dusuk_saat", "ariza_sayaci_yaklasti", "teminat_hatirlatma", "avans_hatirlatma")   # v2.519 (P7a)
ESIK_VARSAYILAN = {"pr_esik": 0.70, "clipping_esik": 0.15, "iletisim_esik_saat": 6, "kullanilabilirlik_esik": 0.97,
                   "dengesizlik_esik": 0.03, "revizyon_esik": 0.10,
                   "takvim_gun_once": 3, "ptf_esik_tl_mwh": 0.0, "ariza_esik": 25}   # v2.519: gün, TL/MWh (0 → PTF ≤ 0; YEKDEM'de V), adet
IST = ZoneInfo("Europe/Istanbul")
AYLAR = ("Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")
GUNLER = ("Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz")
KURAL_ETIKET = {"veri_gelmedi": "Veri gelmedi", "skill_dustu": "Tahmin doğruluğu düştü", "pr_dustu": "Performans oranı düştü",   # 29.10: «isabet» iç terim (panel dili)
                "clipping_orani_yuksek": "Kırpma oranı yüksek", "iletisim_kesintisi": "İletişim kesintisi",
                "kullanilabilirlik_dustu": "Kullanılabilirlik düştü",
                "kgup_teslim_gecikti": "Program bildirimi hazırlanamadı", "dengesizlik_asimi": "Dengesizlik maliyeti yüksek",
                "kgup_revizyon_onerisi": "Program revizyonu önerisi",   # v2.507 (F-10): bugünün programı güncel beklentiden eşik kadar sapıyor
                "takvim_son_tarih": "Yaklaşan son tarih", "ptf_dusuk_saat": "Yarın düşük fiyat saati",
                "ariza_sayaci_yaklasti": "Arıza sayacı eşiğe yaklaştı", "teminat_hatirlatma": "Teminat saati hatırlatması",
                "avans_hatirlatma": "Avans ödeme hatırlatması"}   # v2.519 (P7a)


def _pj(plant: dict) -> dict:
    import json as _j
    pj = plant.get("params_json") or {}
    return _j.loads(pj) if isinstance(pj, str) else pj


def secili_kurallar(plant: dict) -> list[str]:
    """params_json.alarm_kurallari ∩ EK_KURALLAR (sıra sabit)."""
    k = _pj(plant).get("alarm_kurallari") or []
    return [x for x in EK_KURALLAR if x in k]


def esikler(plant: dict) -> dict:
    e = dict(ESIK_VARSAYILAN); e.update({k: v for k, v in (_pj(plant).get("alarm_esik") or {}).items() if k in e and v is not None})
    return e


def alicilar(plant: dict) -> list[str]:
    """v2.519: santral bazlı alarm alıcıları (e-posta); PVQ_ALARM_TO ortam adresi her zaman eklenir (boşsa atlanır)."""
    pj = _pj(plant)
    out = [x.strip() for x in (pj.get("alarm_alicilar") or []) if isinstance(x, str) and x.strip()]
    ortam = (os.environ.get("PVQ_ALARM_TO") or "").strip()
    if ortam:
        out.append(ortam)
    return list(dict.fromkeys(out))


def ek_alarmlar(plant: dict, baglam: dict) -> list[tuple[str, str, str]]:
    """SAF: seçili ek kurallar için (kural, şiddet, mesaj) — kütüphanenin koşul/mesajı, santralin eşikleri."""
    b = {**esikler(plant), **baglam}
    out = []
    for ad in secili_kurallar(plant):
        if ad == "kgup_revizyon_onerisi":   # v2.507 (F-10): kütüphane dışı kural — koşul ve mesaj revizyon_service bağlamından
            saatler = b.get("revizyon_oneri_saatleri") or []
            if saatler:
                son = str(b.get("revizyon_ilk_son") or "")[11:16]
                out.append((ad, "warning", f"{plant.get('name', '')}: bugünün programı güncel beklentiden eşik üstü sapıyor — saat {', '.join(f'{h:02d}:00' for h in saatler)}"
                            f" (toplam {float(b.get('revizyon_toplam_fark_mwh') or 0):+.1f} MWh); ilk saat için revizyon son anı {son} (GİP kapısı + 30 dk)"))
            continue
        if ad == "kgup_teslim_gecikti":   # v2.519 (P7a, A7): tahmin yoksa kritik; tahmin var ama bildirilen dosya beyanı yoksa uyarı
            if b.get("kgup_gecikti"):
                out.append((ad, "kritik", f"{plant.get('name', '')}: yarın için teslim penceresi (14:00–15:30) kapandı ve pencere öncesinde verilmiş tahmin yok — program dosyası üretilemedi"))
            elif b.get("kgup_bildirildi") is False:
                out.append((ad, "uyari", f"{plant.get('name', '')}: yarının program önerisi hazır ama TPYS'ye bildirdiğiniz dosya PVQuant'a yüklenmedi — bildirdiyseniz dosyayı Tahminler sayfasından yükleyin; yüklenen dosya beyanınız sayılır"))
            continue
        if ad == "ptf_dusuk_saat":   # v2.519 (P7a, IH-011)
            saatler = b.get("ptf_dusuk_saatler") or []
            if saatler:
                esik = float(b.get("ptf_esik_kullanilan") if b.get("ptf_esik_kullanilan") is not None else b["ptf_esik_tl_mwh"])
                out.append((ad, "uyari", f"{plant.get('name', '')}: yarın ({_tarih_tr(b.get('ptf_yarin'))}) {len(saatler)} saatte gün öncesi fiyat eşiğin altında "
                            f"({'PTF ≤ 0' if esik <= 0 else 'PTF < ' + f'{esik:.0f} TL/MWh'}): saat {', '.join(f'{h:02d}:00' for h in saatler)}"))
            continue
        if ad == "ariza_sayaci_yaklasti":   # v2.519 (P7a, IH-009): elle girilen aylık arıza kaydı sayısı
            n = b.get("ariza_sayisi_ay")
            if n is not None and int(n) >= int(b["ariza_esik"]):
                out.append((ad, "uyari", f"{plant.get('name', '')}: bu ay bildirilen arıza kaydı {int(n)} (uyarı eşiği {int(b['ariza_esik'])}); arıza eşiğinde KÜPST fiyat katsayısı yükselir (kural tablosu)"))
            continue
        if ad in ("teminat_hatirlatma", "avans_hatirlatma"):   # v2.519 (P7a, IH-031/IH-032): iş günü hatırlatması, zamanlayıcı tetikler
            if b.get("hatirlatma") == ad:
                msg = ("iş günü hatırlatması — teminat mektubu 10:30'a kadar EPİAŞ'a sunulur, 11:00'de GÖP ve GİP teminat kontrolü; eksik kalırsa işlem yasağı riski "
                       "(Teminat Usul ve Esasları; tutarlar EPYS ve Takasbank'ta)" if ad == "teminat_hatirlatma" else
                       "iş günü hatırlatması — günlük avans bildirimi 14:30'da yayımlandı; borç 15:00'a kadar ödenir (sonrası temerrüt: 6183 m.51 oranının %50'si, "
                       "17:00 sonrası tam oran), alacak 17:00'a kadar EPİAŞ'tan gelir (DUY m.132/Ç, m.132/D)")
                out.append((ad, "bilgi", f"{plant.get('name', '')}: {msg}"))
            continue
        if ad == "takvim_son_tarih":   # ayrı yazıcı: takvim_alarmlari (olay başına tek alarm)
            continue
        k = KUTUPHANE[ad]
        # iletisim_kesintisi kütüphanede 'ping dakikası' ister; üründe canlı ping yok → SCADA tazeliği saat cinsinden
        kosul = ((b.get("son_scada_saat_once") or 0) > b["iletisim_esik_saat"]) if ad == "iletisim_kesintisi" else k.kosul(b)
        if kosul:
            if ad == "iletisim_kesintisi":
                msg = f"son ölçüm {float(b.get('son_scada_saat_once') or 0):.0f} saat önce (eşik {float(b['iletisim_esik_saat']):.0f} s) — canlı bağlantı kesilmiş olabilir"
            elif ad == "dengesizlik_asimi":
                msg = f"son 30 günün dengesizlik maliyeti gelirin %{100 * float(b.get('dengesizlik_gelir_orani_ay') or 0):.1f}'i (eşik %{100 * float(b['dengesizlik_esik']):.0f})"
            else:
                msg = k.mesaj(b)
            out.append((ad, k.siddet, f"{plant.get('name', '')}: {msg}"))
    return out


def _baglam(tenant_id, plant: dict, secili: list[str]) -> dict:
    """Yalnız seçili kuralların ihtiyaç duyduğu veriyi hesaplar (gereksiz sorgu yok)."""
    b: dict = {}
    pid = plant["id"]
    if "pr_dustu" in secili:
        from pvquant.services import pr_service
        pr = pr_service.pr_karti(tenant_id, pid, 30)
        b["pr_30g"] = pr.get("PR") if pr.get("durum") == "ok" else None
    if "clipping_orani_yuksek" in secili:
        from pvquant.services import hijyen_service
        h = hijyen_service.ozet(tenant_id, pid, 7)
        b["clipping_orani_7g"] = (h["kirpma_saat"] / h["saat"]) if h.get("saat") else 0.0
    if "kullanilabilirlik_dustu" in secili:
        from pvquant.services import kullanilabilirlik_service
        k = kullanilabilirlik_service.hesapla(tenant_id, plant, 30)
        b["kullanilabilirlik_30g"] = k.get("A_t")
    if "kgup_teslim_gecikti" in secili:
        b["kgup_gecikti"] = False
        try:
            import pandas as _pd
            from pvquant.services import kgup_service, dengesizlik_service
            simdi = _pd.Timestamp.now(tz="Europe/Istanbul")
            seg = dengesizlik_service.segment_bilgisi(plant.get("params_json"))
            if seg.get("kgup_yukumlu") and simdi.hour * 60 + simdi.minute >= 15 * 60 + 30:
                yarin = (simdi + _pd.Timedelta(days=1)).date()
                _, kosu = kgup_service.kaynak_kosu_df(tenant_id, plant["id"], yarin)
                b["kgup_gecikti"] = kosu is None
                if kosu is not None:   # v2.519 (A7): bildirilen dosya beyanı (kgup_surum kaynak='musteri') var mı
                    from pvquant.services import kgup_arsiv_service
                    b["kgup_bildirildi"] = any(r.get("kaynak") == "musteri" for r in kgup_arsiv_service.listele(tenant_id, plant["id"], yarin))
        except Exception:   # noqa: BLE001
            b["kgup_gecikti"] = False
    if "dengesizlik_asimi" in secili:
        try:
            from pvquant.services import dengesizlik_service
            sim = dengesizlik_service.simulasyon(tenant_id, {"id": pid, "params_json": plant.get("params_json")}, gun=30)
            oran = (sim.get("toplam") or {}).get("gelir_oran_pct")
            b["dengesizlik_gelir_orani_ay"] = (float(oran) / 100.0) if oran is not None else None
        except Exception:   # noqa: BLE001
            b["dengesizlik_gelir_orani_ay"] = None
    if "iletisim_kesintisi" in secili:
        with tenant_baglami(tenant_id) as s:
            saat = s.execute(text("SELECT EXTRACT(EPOCH FROM (now() - max(ts_utc)))/3600 FROM scada_hourly WHERE plant_id=:p"), {"p": pid}).scalar()
        b["son_scada_saat_once"] = round(float(saat), 1) if saat is not None else None
    if "ptf_dusuk_saat" in secili:   # v2.519 (P7a)
        try:
            b.update(ptf_baglam(plant))
        except Exception as e:   # noqa: BLE001 — fiyat okunamazsa alarm düşmez
            print("[alarm][ptf]", plant.get("name"), type(e).__name__, e); b["ptf_dusuk_saatler"] = []
    if "ariza_sayaci_yaklasti" in secili:   # v2.519 (P7a): params_json.ariza_sayisi_ay (elle girilen)
        b["ariza_sayisi_ay"] = _pj(plant).get("ariza_sayisi_ay")
    if "kgup_revizyon_onerisi" in secili:   # v2.507 (F-10)
        try:
            from pvquant.services import revizyon_service
            r = revizyon_service.oner(tenant_id, {**plant, "id": pid})
            b["revizyon_oneri_saatleri"] = r.get("oneri_saatleri") or []
            b["revizyon_toplam_fark_mwh"] = r.get("toplam_fark_mwh"); b["revizyon_ilk_son"] = r.get("ilk_revizyon_son")
        except Exception:   # noqa: BLE001 — öneri hesaplanamazsa alarm düşmez
            b["revizyon_oneri_saatleri"] = []
    return b


def ptf_baglam(plant: dict, bugun: date | None = None, fiyatlar=None) -> dict:
    """v2.519 (P7a, IH-011): yarının (İstanbul) 24 saatinde EPİAŞ gün öncesi PTF'si (kaynak epias / epias_gop) eşik altındaki saatler.
    Eşik: alarm_esik.ptf_esik_tl_mwh (0 → PTF ≤ 0); lisanslı YEKDEM'de ve tarife yekdem ise eşik 0 bırakıldığında V = ABD senti/kWh × 10 × kur
    (TL/MWh) kullanılır ve PTF < V aranır. Senaryo fiyatı sayılmaz (gün öncesi PTF gelmemişse alarm yok)."""
    import pandas as pd
    from pvquant.services import dengesizlik_service
    pj = _pj(plant); e = esikler(plant)
    yarin = (bugun or datetime.now(IST).date()) + timedelta(days=1)
    idx = pd.date_range(pd.Timestamp(yarin).tz_localize(IST), periods=24, freq="h").tz_convert("UTC")
    if fiyatlar is None:
        from pvquant.services import piyasa_service
        fiyatlar = piyasa_service.fiyatlar
    f = fiyatlar(idx)
    esik = float(e["ptf_esik_tl_mwh"]); v_ile = False
    t = pj.get("tarife") or {}
    if esik <= 0 and dengesizlik_service.segment_bilgisi(pj).get("segment") == "lisansli_yekdem" and t.get("tip") == "yekdem" \
            and t.get("usd_cent_kwh") and t.get("kur_tl_usd"):
        esik = float(t["usd_cent_kwh"]) * 10.0 * float(t["kur_tl_usd"]); v_ile = True
    ger = f[f["kaynak"].isin(["epias", "epias_gop"])] if "kaynak" in f else f.iloc[0:0]
    ptf = ger["ptf"].astype(float)
    kosul = (ptf <= esik) if esik <= 0 else (ptf < esik)
    saatler = sorted(int(h) for h in ger.index.tz_convert(IST).hour[kosul.values]) if len(ger) else []
    return {"ptf_dusuk_saatler": saatler, "ptf_esik_kullanilan": esik, "ptf_v_ile": v_ile, "ptf_yarin": yarin.isoformat(), "ptf_veri_saat": int(len(ger))}


def _tarih_tr(iso) -> str:
    """ISO gün → «2 Kas 2026 Pzt» (alarm metni müşteri biçiminde)."""
    try:
        t = date.fromisoformat(str(iso)[:10])
    except (TypeError, ValueError):
        return str(iso or "")
    return f"{t.day} {AYLAR[t.month - 1]} {t.year} {GUNLER[t.weekday()]}"


def takvim_alarmlari(plant: dict, bugun: date | None = None) -> list[tuple[str, str, str]]:
    """v2.519 (P7a): takvim_son_tarih — santralın segmentine göre yaklaşan olaylardan kalan gün ≤ takvim_gun_once olanlar; olay başına
    deterministik mesaj (tarih + ad + dönem + dayanak), yazıcı aynı mesajı 60 gün içinde ikinci kez yazmaz. Şiddet: ≤1 gün uyarı, yoksa bilgi."""
    from pvquant.services import takvim_service
    n = int(esikler(plant)["takvim_gun_once"])
    o = takvim_service.ozet(plant, gun=max(7, n), bugun=bugun)
    if not o["segment"]:   # segment seçilmemişse takvim tüm segmentlerin tarihlerini verir — alarm üretilmez (Takvim sayfası bunu yazar)
        return []
    out = []
    for ev in o["yaklasan"]:
        if ev["kalan_gun"] > n:
            continue
        tarih = _tarih_tr(ev["tarih"]) + (f" {ev['saat']}" if ev.get("saat") else "")
        donem = f" ({AYLAR[int(ev['donem'][5:7]) - 1]} {ev['donem'][:4]} dönemi)" if ev.get("donem") else ""
        out.append(("takvim_son_tarih", "uyari" if ev["kalan_gun"] <= 1 else "bilgi",
                    f"{plant.get('name', '')}: {tarih} — {ev['ad']}{donem}; dayanak: {ev['kaynak']}"))
    return out


def _bildir(plant: dict | None, rule: str, msg: str, severity: str) -> None:
    """v2.519: alerts satırı yazıldıktan sonra e-posta (santral alıcıları + PVQ_ALARM_TO) ve webhook «alarm.yeni»; hiçbir hata yükselmez."""
    from pvquant.services import posta_service
    konu = f"[PVQuant] {KURAL_ETIKET.get(rule, rule)}"
    kime = alicilar(plant or {})
    sonuc = [posta_service.gonder(a, konu, msg) for a in kime]   # any() kısa devre yapmasın: her alıcıya dene
    if not any(sonuc):
        print("[alarm][mail yok]", konu)
    if plant and plant.get("tenant_id") and plant.get("id"):
        try:
            from pvquant.services import webhook_service
            webhook_service.gonder(plant["tenant_id"], "alarm.yeni",
                                   {"olay": "alarm.yeni", "santral_id": str(plant["id"]), "santral": plant.get("name"), "kural": rule,
                                    "kural_adi": KURAL_ETIKET.get(rule, rule), "siddet": severity, "mesaj": msg,
                                    "zaman": datetime.now(IST).isoformat(timespec="seconds")}, plant_id=str(plant["id"]))
        except Exception as e:   # noqa: BLE001
            print("[alarm][webhook atlandı]", rule, type(e).__name__, e)


def _kaydet_ve_gonder(s, tid, pid, rule: str, msg: str, severity: str = "warning", plant: dict | None = None) -> None:
    # spam kilidi: günde 1 — pencere 23 saat (01.11 incelemesi): günlük iş bir gün 04:00:30'da, ertesi gün 04:00:20'de koşarsa
    # 24 saatlik pencere bir önceki alarmı hâlâ «dün» sayıp o günü sessizce atlıyordu; saatlik iş için de en çok 1/23 saat yeterli.
    var = s.execute(text(
        "SELECT 1 FROM alerts WHERE plant_id=:p AND rule=:r "
        "AND created_at > now()-interval '23 hours'"),
        {"p": pid, "r": rule}).first()
    if var:
        return
    s.execute(text(
        "INSERT INTO alerts(tenant_id,plant_id,rule,message,severity) "
        "VALUES(:t,:p,:r,:m,:s)"), {"t": tid, "p": pid, "r": rule, "m": msg, "s": severity})
    _bildir(plant or {"tenant_id": tid, "id": pid}, rule, msg, severity)


def _kaydet_tekil(s, tid, pid, rule: str, msg: str, severity: str, plant: dict | None = None) -> bool:
    """v2.519: olay başına tek alarm — aynı mesaj son 60 günde yazılmışsa atlanır (takvim olayları için)."""
    var = s.execute(text("SELECT 1 FROM alerts WHERE plant_id=:p AND rule=:r AND message=:m AND created_at > now()-interval '60 days'"),
                    {"p": pid, "r": rule, "m": msg}).first()
    if var:
        return False
    s.execute(text("INSERT INTO alerts(tenant_id,plant_id,rule,message,severity) VALUES(:t,:p,:r,:m,:s)"),
              {"t": tid, "p": pid, "r": rule, "m": msg, "s": severity})
    _bildir(plant or {"tenant_id": tid, "id": pid}, rule, msg, severity)
    return True


SIDDET = {"bilgi": "info", "uyari": "warning", "kritik": "critical"}


def tara(plant: dict) -> None:
    """Worker 4. işin gövdesi — santral başına tek tarama."""
    tid, pid = plant["tenant_id"], plant["id"]
    with tenant_baglami(tid) as s:
        son = s.execute(text(
            "SELECT max(ts_utc) FROM scada_hourly WHERE plant_id=:p"),
            {"p": pid}).scalar()
        if son is not None:
            esik = s.execute(text("SELECT now()-interval '48 hours'")).scalar()
            if son < esik:
                _kaydet_ve_gonder(s, tid, pid, "veri_gelmedi",
                    f"{plant['name']}: son SCADA verisi {son:%d.%m %H:%M} — "
                    "48 saati aştı, yükleme aksadı.", plant=plant)
        rows = s.execute(text(
            "SELECT date, mape FROM skill_daily WHERE plant_id=:p "
            "AND horizon_bucket='0-24' ORDER BY date DESC LIMIT 30"),
            {"p": pid}).fetchall()
        if len(rows) >= 10:
            ort = sum(r.mape for r in rows) / len(rows)
            son7 = [r.mape for r in rows[:7]]
            if all(m > 1.5 * ort for m in son7):
                _kaydet_ve_gonder(s, tid, pid, "skill_dustu",
                    f"{plant['name']}: 0-24s MAPE 7 gündür 30 günlük "
                    f"ortalamanın (%{ort:.0f}) 1.5 katının üzerinde — "
                    "kalibrasyon/sensör kontrolü önerilir.", plant=plant)
    # v2.265: ek kurallar — yalnız santral bazında açılmışsa; varsayılan iki kural değişmez
    # v2.519: gün içi kuralları (kgup_teslim_gecikti, kgup_revizyon_onerisi, ptf, hatırlatmalar) kendi zamanlayıcı işlerinde; gece taraması atlar
    secili = [k for k in secili_kurallar(plant) if k not in ("kgup_teslim_gecikti", "kgup_revizyon_onerisi", "ptf_dusuk_saat",
                                                              "teminat_hatirlatma", "avans_hatirlatma")]
    if secili:
        baglam = _baglam(tid, plant, secili)
        with tenant_baglami(tid) as s:
            for rule, siddet, msg in ek_alarmlar(plant, baglam):
                _kaydet_ve_gonder(s, tid, pid, rule, msg, SIDDET[siddet], plant=plant)
            if "takvim_son_tarih" in secili:   # v2.519 (P7a): olay başına tek alarm
                for rule, siddet, msg in takvim_alarmlari(plant):
                    _kaydet_tekil(s, tid, pid, rule, msg, SIDDET[siddet], plant=plant)


def kgup_kontrol(plant: dict) -> None:
    """29.10.2026 (F-11 N2 / 08 #7): «kgup_teslim_gecikti» kuralı yalnız 15:30 TSİ SONRASINDA anlamlıdır; gece alarm taraması
    (04:00 UTC) bu koşulu hiç göremiyordu → kural seçili olsa da tetiklenemiyordu. Worker bu işi 12:35 UTC'de (15:35 TSİ) koşar."""
    if "kgup_teslim_gecikti" not in secili_kurallar(plant):
        return
    tid, pid = plant["tenant_id"], plant["id"]
    baglam = _baglam(tid, plant, ["kgup_teslim_gecikti"])
    with tenant_baglami(tid) as s:
        for rule, siddet, msg in ek_alarmlar(plant, baglam):
            if rule == "kgup_teslim_gecikti":
                _kaydet_ve_gonder(s, tid, pid, rule, msg, SIDDET[siddet], plant=plant)


def kgup_revizyon_kontrol(plant: dict) -> None:
    """v2.507 (F-10): gün içi saatlik kontrol — «kgup_revizyon_onerisi» seçiliyse bugünün programı ile güncel beklenti kıyaslanır;
    eşik üstü ve revize edilebilir saat varsa alarm (günde 1 spam kilidi _kaydet_ve_gonder'de)."""
    if "kgup_revizyon_onerisi" not in secili_kurallar(plant):
        return
    tid, pid = plant["tenant_id"], plant["id"]
    baglam = _baglam(tid, plant, ["kgup_revizyon_onerisi"])
    with tenant_baglami(tid) as s:
        for rule, siddet, msg in ek_alarmlar(plant, baglam):
            if rule == "kgup_revizyon_onerisi":
                _kaydet_ve_gonder(s, tid, pid, rule, msg, siddet, plant=plant)


def _tek_kural(plant: dict, kural: str, baglam_ek: dict | None = None) -> None:
    """v2.519: tek kuralın zamanlayıcı tetiklemesi — kural seçili değilse hiç dokunmaz; spam kilidi günde 1."""
    if kural not in secili_kurallar(plant):
        return
    tid, pid = plant["tenant_id"], plant["id"]
    baglam = {**_baglam(tid, plant, [kural]), **(baglam_ek or {})}
    with tenant_baglami(tid) as s:
        for rule, siddet, msg in ek_alarmlar(plant, baglam):
            if rule == kural:
                _kaydet_ve_gonder(s, tid, pid, rule, msg, SIDDET[siddet], plant=plant)


def iletisim_kontrol(plant: dict) -> None:
    """v2.519 (P7a, ENV-F03): «iletişim kesintisi» kritikken günde bir taranıyordu; worker bunu her saat koşar."""
    _tek_kural(plant, "iletisim_kesintisi")


def ptf_kontrol(plant: dict) -> None:
    """v2.519 (P7a, IH-011): gün öncesi PTF işi (14:35 TSİ) bittikten sonra 14:40'ta — yarının düşük fiyat saatleri."""
    _tek_kural(plant, "ptf_dusuk_saat")


def hatirlatma(plant: dict, tur: str, bugun: date | None = None) -> None:
    """v2.519 (P7a, IH-031/IH-032): iş günü hatırlatması — teminat 10:15 TSİ, avans 14:45 TSİ; yalnız lisanslı segment."""
    from pvquant.ext.turkiye import takvim as tk
    from pvquant.services import dengesizlik_service
    kural = f"{tur}_hatirlatma"
    if kural not in secili_kurallar(plant):
        return
    g = bugun or datetime.now(IST).date()
    if not tk.is_gunu(g):
        return
    if dengesizlik_service.segment_bilgisi(plant.get("params_json")).get("segment") not in tk.LISANSLI:
        return
    _tek_kural(plant, kural, {"hatirlatma": kural})


def hatirlatma_teminat(plant: dict) -> None:
    hatirlatma(plant, "teminat")


def hatirlatma_avans(plant: dict) -> None:
    hatirlatma(plant, "avans")


def listele(tenant_id, plant_id, n: int = 20):
    """Alarm listesi — SUNUM için ham okuma (yeni→eski); hesap yok,
    üretici worker'daki tara()'dır. RLS tenant_baglami'nda."""
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT a.id, a.rule, a.severity, a.message, a.created_at, a.acked_by, a.acked_at, a.assigned_to, "
            " u1.email AS okuyan, u2.email AS atanan "
            "FROM alerts a LEFT JOIN users u1 ON u1.id = a.acked_by LEFT JOIN users u2 ON u2.id = a.assigned_to "
            "WHERE a.plant_id=:p ORDER BY a.created_at DESC LIMIT :n"),
            {"p": plant_id, "n": n}).fetchall()
        return [{"id": str(r.id), "kural": r.rule, "siddet": r.severity,
                 "mesaj": r.message, "zaman": r.created_at.isoformat(),
                 # v2.265: okundu/atama
                 "okundu": r.acked_by is not None, "okuyan": r.okuyan,
                 "okunma": r.acked_at.isoformat() if r.acked_at else None,
                 "atanan_id": str(r.assigned_to) if r.assigned_to else None, "atanan": r.atanan} for r in rows]


def okundu(tenant_id, plant_id, alarm_id, user_id) -> bool:
    """v2.265: okundu işareti (kim, ne zaman). İkinci kez işaretleme sessizce True."""
    with tenant_baglami(tenant_id) as s:
        n = s.execute(text("UPDATE alerts SET acked_by=:u, acked_at=COALESCE(acked_at, now()) WHERE id=:i AND plant_id=:p"),
                      {"u": user_id, "i": alarm_id, "p": plant_id}).rowcount
    return n > 0


def ata(tenant_id, plant_id, alarm_id, kime) -> bool:
    """v2.265: atama (None → atamayı kaldır). Atanan kullanıcı aynı kiracıda olmalı."""
    with tenant_baglami(tenant_id) as s:
        if kime is not None:
            var = s.execute(text("SELECT 1 FROM users WHERE id=:u AND tenant_id=:t"), {"u": kime, "t": tenant_id}).first()
            if not var:
                raise ValueError("kullanıcı bu hesapta değil")
        n = s.execute(text("UPDATE alerts SET assigned_to=:u WHERE id=:i AND plant_id=:p"), {"u": kime, "i": alarm_id, "p": plant_id}).rowcount
    return n > 0


def kullanicilar(tenant_id) -> list[dict]:
    """v2.265: atama listesi — kiracının kullanıcıları (users tablosu RLS dışı; tenant süzgeci açıkça)."""
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text("SELECT id, email, role FROM users WHERE tenant_id=:t ORDER BY email"), {"t": tenant_id}).fetchall()
    return [{"id": str(r.id), "email": r.email, "rol": r.role} for r in rows]


def kural_durumu(plant: dict) -> dict:
    pj = _pj(plant)
    return {"secili": secili_kurallar(plant), "secilebilir": list(EK_KURALLAR), "esik": esikler(plant),
            "etiket": KURAL_ETIKET, "varsayilan": ["veri_gelmedi", "skill_dustu"],
            "alicilar": [x for x in (pj.get("alarm_alicilar") or []) if isinstance(x, str)],   # v2.519: santral alıcıları (ortam adresi hariç)
            "ortam_alicisi": bool((os.environ.get("PVQ_ALARM_TO") or "").strip())}


_EPOSTA = __import__("re").compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def kural_ayarla(tenant_id, plant_id, kurallar: list[str], esik: dict | None = None, alicilar: list[str] | None = None) -> dict:
    from pvquant.services import plant_service
    k = [x for x in EK_KURALLAR if x in (kurallar or [])]
    e = {kk: float(v) for kk, v in (esik or {}).items() if kk in ESIK_VARSAYILAN and v is not None}
    if "takvim_gun_once" in e and not (1 <= e["takvim_gun_once"] <= 30):
        raise ValueError("takvim_gun_once 1–30")
    if "ptf_esik_tl_mwh" in e and not (0 <= e["ptf_esik_tl_mwh"] <= 10000):
        raise ValueError("ptf_esik_tl_mwh 0–10000")
    if "ariza_esik" in e and not (1 <= e["ariza_esik"] <= 30):
        raise ValueError("ariza_esik 1–30")
    for kk in ("takvim_gun_once", "ariza_esik"):
        if kk in e:
            e[kk] = int(e[kk])
    ek = {}
    if alicilar is not None:
        a = list(dict.fromkeys(x.strip().lower() for x in alicilar if isinstance(x, str) and x.strip()))
        if len(a) > 10:
            raise ValueError("en çok 10 alıcı")
        for x in a:
            if not _EPOSTA.match(x):
                raise ValueError(f"alıcı e-posta geçersiz: {x}")
        ek["alarm_alicilar"] = a
    if "pr_esik" in e and not (0.3 <= e["pr_esik"] <= 1.0):
        raise ValueError("pr_esik 0,30–1,00")
    if "clipping_esik" in e and not (0.0 < e["clipping_esik"] <= 1.0):
        raise ValueError("clipping_esik 0–1")
    if "iletisim_esik_saat" in e and not (1 <= e["iletisim_esik_saat"] <= 48):
        raise ValueError("iletisim_esik_saat 1–48")
    if "kullanilabilirlik_esik" in e and not (0.5 <= e["kullanilabilirlik_esik"] <= 1.0):
        raise ValueError("kullanilabilirlik_esik 0,5–1,0")
    if "dengesizlik_esik" in e and not (0.0 < e["dengesizlik_esik"] <= 0.5):
        raise ValueError("dengesizlik_esik 0–0,5")
    pj = plant_service.params_birlestir(tenant_id, plant_id, alarm_kurallari=k, alarm_esik=e, **ek)
    return kural_durumu({"params_json": pj})
