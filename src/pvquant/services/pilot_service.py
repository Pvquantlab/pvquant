"""09.11.2026 v2.560 (Aşama 4) — PİLOT KAPILARI ve REFERANS KIYASI.

Kapılar (Codex Faz 3 G01–G10; 09_Gercek_Pilot_Teknik_Gereksinimleri, 15_Faz3_Yonetici_Karar_Raporu §7): G01–G06 ve G10 ortak P0; G07/G08/G09 markaya
özgü. «kod» kaynaklı kapılar (G05, G06) PVQuant testleriyle kapanır; «saha» kaynaklılar sahibin/işletmecinin beyanıyla, tarih ve notla kapatılır
(params_json.pilot.kapilar). Sahaya bağlantı, bütün P0 kapıları kapanmadan başlatılmaz; ekran bunu söyler.
Referans kıyası (P1xx/P7xx çıkış kanıtı): aynı cihazın, aynı ölçüm sınırında, referans saatlik dışa aktarımı (CSV: zaman, kWh) ile gölge görünümdeki
TAM saatler karşılaştırılır; kısmi/tahmini saatler kıyas dışı (referans değildir). Tolerans saat başına en çok(%2, 0,5 kWh); en az 24 ortak saat yoksa
«yetersiz». Sonuç özeti params_json.pilot.referans_sonuc'a yazılır (ham referans saklanmaz).
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, timezone

KAPILAR = [
    {"kod": "G01", "ad": "Gerçek cihaz ve tam profil", "kaynak": "saha", "p0": True,
     "aciklama": "Pilot cihazının tam model etiketi, donanım/yazılım sürümü ve kayıt haritası (SunSpec modelleri ya da üretici tablosu) elde; PVQuant profili bununla eşleşiyor."},
    {"kod": "G02", "ad": "Yetki", "kaynak": "saha", "p0": True,
     "aciklama": "Tesis/veri sahibi, O&M ve OT sorumlusunun yazılı izni: cihaz, port, birim kimliği, fonksiyon kodu, adres aralığı, süre, test ve geri dönüş."},
    {"kod": "G03", "ad": "Yalnızca okuma ve oturum", "kaynak": "saha", "p0": True,
     "aciklama": "Yalnız okuma fonksiyonları (FC03/FC04), yazma kapalı; cihazın eşzamanlı istemci sınırı ve mevcut SCADA oturumu etkilenmiyor; OT filtreli yol (VPN), 502 internete açık değil."},
    {"kod": "G04", "ad": "Referans dışa aktarım", "kaynak": "saha", "p0": True,
     "aciklama": "Aynı cihazın, aynı ölçüm sınırında, pilot dönemini tam kapsayan referans saatlik dışa aktarımı elde; tolerans yöntemi önceden yazılı."},
    {"kod": "G05", "ad": "Tipli çözümleme ve tam aralık", "kaynak": "kod", "p0": True,
     "aciklama": "Tipli sentinel ve sonlu değer denetimi, kapanış örneğiyle tam saat, kısmi saatin ayrı sınıfı — PVQuant testleri (v2.549–v2.551)."},
    {"kod": "G06", "ad": "MBAP ve cihaz/akış kimliği", "kaynak": "kod", "p0": True,
     "aciklama": "MBAP başlık doğrulaması, bağlantı başına zaman aşımı; cihaz, kaynak, ölçüm sınırı kimliği ve revizyon — PVQuant testleri (v2.549–v2.550, v2.558)."},
    {"kod": "G07", "ad": "Huawei bağlantısı", "kaynak": "saha", "p0": False,
     "aciklama": "FusionSolar Northbound hesabı (kurulumcu yöneticisi açar) ve birim semantiği gerçek yanıtla doğrulanmış; SmartLogger haritası gerçek cihazla."},
    {"kod": "G08", "ad": "GoodWe bağlantısı", "kaynak": "saha", "p0": False,
     "aciklama": "SEMS OpenAPI lisansı/beyaz liste; EzLogger nokta tablosu yönü. Bağlayıcı yazılmadı; talep gelince."},
    {"kod": "G09", "ad": "Sungrow bağlantısı", "kaynak": "saha", "p0": False,
     "aciklama": "iSolarCloud OAuth onayı ve Türkiye bölgesi; Logger1000 FC04 haritası gerçek cihazla."},
    {"kod": "G10", "ad": "Kesinti ve geri dönüş planı", "kaynak": "saha", "p0": True,
     "aciklama": "Kesintide yeniden bağlanma ve çift sayım olmaması gösterildi; pilotu durdurma/geri alma adımları yazılı; O&M'ye etkisi yok."},
]
TOL_PCT = 2.0
TOL_KWH = 0.5
MIN_ORTAK_SAAT = 24


def _pj(plant: dict) -> dict:
    pj = (plant or {}).get("params_json") or {}
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    return pj


def durum(plant: dict) -> dict:
    """SAF. Kapı listesi + beyan durumu; P0 açık kapılar; sahaya çıkış hazır mı (tüm P0 kapalı)."""
    pil = _pj(plant).get("pilot") if isinstance(_pj(plant).get("pilot"), dict) else {}
    kap = pil.get("kapilar") if isinstance(pil.get("kapilar"), dict) else {}
    out = []
    for k in KAPILAR:
        b = kap.get(k["kod"]) or {}
        tamam = bool(b.get("tamam")) if k["kaynak"] == "saha" else True
        out.append({**k, "tamam": tamam, "not": b.get("not"), "zaman": b.get("zaman"), "aktor_id": b.get("aktor_id"),
                    "durum_etiketi": ("kod testleriyle kapalı; gerçek cihazda doğrulanmadı" if k["kaynak"] == "kod" else ("sahibin beyanıyla kapalı" if tamam else "açık"))})
    acik_p0 = [k["kod"] for k in out if k["p0"] and not k["tamam"]]
    return {"kapilar": out, "p0_acik": acik_p0, "sahaya_hazir": not acik_p0, "referans_sonuc": pil.get("referans_sonuc"),
            "not": "Sahaya bağlantı tüm P0 kapıları kapanmadan başlatılmaz. Kod kapıları PVQuant testleriyle, saha kapıları sahibin/işletmecinin tarihli beyanıyla kapanır; "
                   "beyan, sahadaki gerçeği kanıtlamaz, sorumluluğu adlandırır."}


def kapi_ayarla(tenant_id, plant_id, kod: str, tamam: bool, not_: str | None, aktor_id) -> dict:
    from pvquant.services import plant_service
    kod = (kod or "").strip().upper()
    k = next((x for x in KAPILAR if x["kod"] == kod), None)
    if k is None:
        raise ValueError("bilinmeyen kapı kodu")
    if k["kaynak"] == "kod":
        raise ValueError("bu kapı kod testleriyle kapanır; elle işaretlenmez")
    row = plant_service.getir(tenant_id, plant_id)
    if row is None:
        raise LookupError("santral yok")
    pil = _pj(row).get("pilot") if isinstance(_pj(row).get("pilot"), dict) else {}
    kap = dict(pil.get("kapilar") or {})
    kap[kod] = {"tamam": bool(tamam), "not": (str(not_).strip()[:300] or None) if not_ else None, "zaman": datetime.now(timezone.utc).isoformat(timespec="minutes"), "aktor_id": str(aktor_id) if aktor_id else None}
    plant_service.params_birlestir(tenant_id, plant_id, pilot={**pil, "kapilar": kap})
    row["params_json"] = {**_pj(row), "pilot": {**pil, "kapilar": kap}}
    return durum(row)


def referans_csv_oku(metin: str) -> list[dict]:
    """CSV: zaman/ts, kwh/enerji_kwh (ayraç , ya da ;). Saat dilimi yoksa UTC varsayılır ve işaretlenir. Döner [{ts_utc, kwh}] (saat başına yuvarlanmış)."""
    metin = metin.lstrip("\ufeff")
    ayrac = ";" if metin.count(";") > metin.count(",") else ","
    r = csv.DictReader(io.StringIO(metin), delimiter=ayrac)
    if not r.fieldnames:
        raise ValueError("CSV başlığı yok")
    alan = {a.strip().lower(): a for a in r.fieldnames}
    ts_k = next((alan[a] for a in ("ts_utc", "ts", "zaman", "saat", "time", "timestamp") if a in alan), None)
    kwh_k = next((alan[a] for a in ("kwh", "enerji_kwh", "energy_kwh", "uretim_kwh") if a in alan), None)
    if not ts_k or not kwh_k:
        raise ValueError("CSV'de zaman (ts/zaman) ve kWh (kwh/enerji_kwh) sütunları gerekli")
    out, tzsiz = [], 0
    for sat in r:
        t = (sat.get(ts_k) or "").strip(); v = (sat.get(kwh_k) or "").strip().replace(",", ".")
        if not t or not v:
            continue
        try:
            ts = datetime.fromisoformat(t.replace("Z", "+00:00"))
            kwh = float(v)
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc); tzsiz += 1
        out.append({"ts_utc": ts.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0), "kwh": kwh})
    if not out:
        raise ValueError("okunabilir satır yok")
    if tzsiz:
        out[0]["_uyari"] = f"{tzsiz} satırda saat dilimi yok; UTC varsayıldı"
    return out


def _tr(x: float, bicim: str = "g") -> str:
    """SAF. Türkçe ondalık (virgül) — müşteri metinlerinde nokta ondalık kalmasın (10.11 inceleme)."""
    return format(x, bicim).replace(".", ",")


def referans_kiyas(golge_saatler: list[dict], referans: list[dict], tol_pct: float = TOL_PCT, tol_kwh: float = TOL_KWH) -> dict:
    """SAF. golge_saatler: karsilastir() çıktısındaki saatler [{ts_utc, secilen{tamlik, energy_kwh, kaynak}}]; referans [{ts_utc, kwh}].
    Yalnız TAM gölge saatleri kıyaslanır; kısmi/tahmini ve gölgesi olmayan saatler ayrı sayılır (referans dışı)."""
    g = {}
    for h in golge_saatler:
        t = h["ts_utc"]
        t = datetime.fromisoformat(t) if isinstance(t, str) else t
        g[t.astimezone(timezone.utc)] = h.get("secilen")
    n_ortak = n_tol = n_yok = n_kismi = 0; farklar = []; ape = []; top_ref = top_g = 0.0; maks = 0.0; saatler = []
    for r in referans:
        sec = g.get(r["ts_utc"].astimezone(timezone.utc))
        if sec is None:
            n_yok += 1; continue
        if sec.get("tamlik") != "measured_complete" or sec.get("energy_kwh") is None:
            n_kismi += 1; continue
        e = float(sec["energy_kwh"]); ref = float(r["kwh"]); f = e - ref
        n_ortak += 1; top_ref += ref; top_g += e; farklar.append(f); maks = max(maks, abs(f))
        if ref > 0:
            ape.append(abs(f) / ref)
        ici = abs(f) <= max(tol_kwh, tol_pct / 100.0 * abs(ref))
        n_tol += int(ici)
        if not ici and len(saatler) < 48:
            saatler.append({"ts_utc": r["ts_utc"].isoformat(), "referans_kwh": round(ref, 3), "golge_kwh": round(e, 3), "fark_kwh": round(f, 3), "kaynak": sec.get("kaynak")})
    oran = (n_tol / n_ortak) if n_ortak else None
    if n_ortak < MIN_ORTAK_SAAT:
        sonuc, metin = "yetersiz", f"Yalnız {n_ortak} ortak tam saat (en az {MIN_ORTAK_SAAT} gerekir); karar verilmez."
    elif oran >= 0.95:
        sonuc, metin = "uyumlu", f"{n_ortak} ortak tam saatin {n_tol} tanesi toleransta (%{_tr(oran * 100, '.1f')}; saat başına en çok %{_tr(tol_pct)} ya da {_tr(tol_kwh)} kWh)."
    else:
        sonuc, metin = "uyumsuz", f"{n_ortak} ortak tam saatin yalnız {n_tol} tanesi toleransta (%{_tr(oran * 100, '.1f')}); fark kaynağı (ölçüm sınırı, saat dilimi, kayıp, çift sayım) incelenmeli."
    return {"sonuc": sonuc, "metin": metin, "n_referans": len(referans), "n_ortak": n_ortak, "n_tolerans_ici": n_tol, "tolerans_orani": (round(oran, 4) if oran is not None else None),
            "n_golge_yok": n_yok, "n_golge_kismi_disi": n_kismi, "mape_pct": (round(sum(ape) / len(ape) * 100, 2) if ape else None),
            "ortalama_fark_kwh": (round(sum(farklar) / len(farklar), 3) if farklar else None), "maks_mutlak_fark_kwh": round(maks, 3),
            "toplam_referans_kwh": round(top_ref, 1), "toplam_golge_kwh": round(top_g, 1),
            "toplam_fark_pct": (round((top_g - top_ref) / top_ref * 100, 2) if top_ref > 0 else None), "tolerans": {"pct": tol_pct, "kwh": tol_kwh},
            "tolerans_disi_saatler": saatler,
            "not": "Kıyas yalnız tam gölge saatlerinde; kısmi/tahmini saatler ve gölgesi olmayan saatler referans dışıdır. Uyum, aynı ölçüm sınırı ve aynı cihaz varsayımıyla okunur."}


def referans_degerlendir(tenant_id, plant: dict, referans: list[dict], sinir: str = "inverter_ac", aktor_id=None, dosya: str | None = None) -> dict:
    """DB: referans aralığı için gölge görünüm → kıyas; özet params_json.pilot.referans_sonuc'a yazılır (ham referans saklanmaz)."""
    from pvquant.services import kaynak_secim_service as ks, plant_service
    bas = min(r["ts_utc"] for r in referans); bit = max(r["ts_utc"] for r in referans) + timedelta(hours=1)
    gg = ks.golge_gorunum(tenant_id, plant, bas, bit, sinir)
    k = referans_kiyas(gg.get("saatler") or [], referans)
    uy = referans[0].get("_uyari")
    k["uyarilar"] = ([uy] if uy else []) + ([gg["uyari"]] if gg.get("uyari") else [])
    ozet = {**{a: k[a] for a in ("sonuc", "metin", "n_referans", "n_ortak", "n_tolerans_ici", "tolerans_orani", "n_golge_yok", "n_golge_kismi_disi", "mape_pct", "maks_mutlak_fark_kwh", "toplam_fark_pct")},
            "sinir": sinir, "bas": bas.isoformat(), "bit": bit.isoformat(), "dosya": dosya, "zaman": datetime.now(timezone.utc).isoformat(timespec="minutes"), "aktor_id": str(aktor_id) if aktor_id else None}
    pil = _pj(plant).get("pilot") if isinstance(_pj(plant).get("pilot"), dict) else {}
    plant_service.params_birlestir(tenant_id, plant["id"], pilot={**pil, "referans_sonuc": ozet})
    return k
