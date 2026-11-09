"""09.11.2026 v2.554 (Aşama 2, S4) — IEC 104 NOKTA TABLOSU: IOA → PVQuant alanı eşlemesi ve genel sorgulama sonucunun ölçüm sözlüğüne çevrilmesi (SAF).

Nokta tablosu santral başına beyanda saklanır (`params_json.veri_yolu.nokta_tablosu`): [{ioa, alan, carpan, ad, tip}]. Alanlar: guc_w, enerji_wh, dc_guc_w,
durum_kodu, isinim_wm2, sicaklik_c, frekans_hz. Carpan kaynak biriminden SI'ya (ör. kW → W: 1000). CSV içe aktarma: başlık satırı ioa,alan,carpan[,ad][,tip];
üretici dışa aktarımları (Sungrow «Generate Point Table», Huawei yapılandırma) farklı başlıklar taşıyorsa önce bu beş kolona indirgenir — biçim görülmedi.
Kalite: IV/NT → değer eksik; SB → ikame (değer alınır, bayrak taşınır); OV → taşma (eksik). Zaman cihaz saatidir; toplayıcı istemci UTC'sini kullanır.
"""
from __future__ import annotations

import csv
import io

ALANLAR = {"guc_w": "AC güç (W)", "enerji_wh": "kümülatif enerji (Wh)", "dc_guc_w": "DC güç (W)", "durum_kodu": "durum kodu", "isinim_wm2": "ışınım (W/m²)",
           "sicaklik_c": "sıcaklık (°C)", "frekans_hz": "frekans (Hz)"}
AZAMI_NOKTA = 500


def dogrula(tablo) -> list[dict]:
    """SAF. [{ioa, alan, carpan, ad, tip}] → doğrulanmış liste; tekrar IOA ve bilinmeyen alan reddedilir."""
    if not isinstance(tablo, list) or not tablo:
        raise ValueError("nokta tablosu boş")
    if len(tablo) > AZAMI_NOKTA:
        raise ValueError(f"nokta tablosu en çok {AZAMI_NOKTA} satır")
    out, gorulen = [], set()
    for i, r in enumerate(tablo, 1):
        if not isinstance(r, dict):
            raise ValueError(f"{i}. satır sözlük değil")
        try:
            ioa = int(r.get("ioa"))
        except (TypeError, ValueError) as e:
            raise ValueError(f"{i}. satır: IOA tam sayı olmalı") from e
        if not (0 <= ioa <= 16777215):
            raise ValueError(f"{i}. satır: IOA 0–16777215 arasında olmalı")
        if ioa in gorulen:
            raise ValueError(f"{i}. satır: IOA {ioa} tekrar ediyor")
        alan = str(r.get("alan") or "").strip()
        if alan not in ALANLAR:
            raise ValueError(f"{i}. satır: alan {', '.join(ALANLAR)} arasından olmalı")
        try:
            carpan = float(r.get("carpan") if r.get("carpan") not in (None, "") else 1.0)
        except (TypeError, ValueError) as e:
            raise ValueError(f"{i}. satır: çarpan sayı olmalı") from e
        if carpan == 0:
            raise ValueError(f"{i}. satır: çarpan 0 olamaz")
        gorulen.add(ioa)
        out.append({"ioa": ioa, "alan": alan, "carpan": carpan, "ad": (str(r.get("ad") or "").strip()[:80] or None), "tip": (int(r["tip"]) if r.get("tip") not in (None, "") else None)})
    return out


def csv_den(metin: str) -> list[dict]:
    """SAF. Başlıklı CSV (ioa, alan, carpan, ad, tip; ayraç , ya da ;) → doğrulanmış tablo."""
    metin = metin.lstrip("﻿")
    ayrac = ";" if metin.splitlines()[0].count(";") > metin.splitlines()[0].count(",") else ","
    okuyucu = csv.DictReader(io.StringIO(metin), delimiter=ayrac)
    basliklar = {(h or "").strip().lower(): h for h in (okuyucu.fieldnames or [])}
    for z in ("ioa", "alan"):
        if z not in basliklar:
            raise ValueError("CSV başlığında 'ioa' ve 'alan' kolonları gerekir (isteğe bağlı: carpan, ad, tip)")
    satirlar = []
    for r in okuyucu:
        if not any((v or "").strip() for v in r.values() if isinstance(v, str)):
            continue
        g = lambda k: (r.get(basliklar[k]) if k in basliklar else None)
        carpan = (g("carpan") or "").replace(",", ".") if isinstance(g("carpan"), str) else g("carpan")
        satirlar.append({"ioa": g("ioa"), "alan": g("alan"), "carpan": carpan, "ad": g("ad"), "tip": g("tip")})
    return dogrula(satirlar)


def esle(noktalar: list[dict], tablo: list[dict]) -> dict:
    """SAF. Genel sorgulama noktaları + tablo → ölçüm sözlüğü (SunSpec inverter sözlüğüyle uyumlu) + eşleşme raporu."""
    ioa_tablo = {t["ioa"]: t for t in tablo}
    olcum: dict = {a: None for a in ALANLAR}
    eslesen, ikame, eksik, kalite_notlari = 0, 0, [], []
    gorulen_ioa = set()
    for n in noktalar:
        t = ioa_tablo.get(n["ioa"])
        if not t:
            continue
        gorulen_ioa.add(n["ioa"])
        k = n.get("kalite") or {}
        if n.get("deger") is None or k.get("iv") or k.get("nt") or k.get("ov"):
            eksik.append({"ioa": n["ioa"], "alan": t["alan"], "neden": "geçersiz" if k.get("iv") else "güncel değil" if k.get("nt") else "taşma" if k.get("ov") else "değer yok"})
            continue
        deger = float(n["deger"]) * float(t["carpan"])
        if t["alan"] == "durum_kodu":
            deger = int(round(deger))
        olcum[t["alan"]] = deger; eslesen += 1
        if k.get("sb"):
            ikame += 1; kalite_notlari.append({"ioa": n["ioa"], "alan": t["alan"], "neden": "ikame değer"})
    gelmeyen = [t["ioa"] for t in tablo if t["ioa"] not in gorulen_ioa]
    return {"olcum": olcum, "eslesen": eslesen, "ikame": ikame, "eksik": eksik, "gelmeyen_ioa": gelmeyen, "nokta_sayisi": len(noktalar), "tablo_sayisi": len(tablo),
            "kalite_notlari": kalite_notlari}
