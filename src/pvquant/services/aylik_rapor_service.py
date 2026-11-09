"""v2.525 (P8/P10 — raporlama) — Dönem raporu ve zamanlanmış gönderim.

Dönem seçici: «YYYY-MM» (ay), «YYYY-QN» (çeyrek), «YYYY» (yıl); geçmiş herhangi bir dönem yeniden üretilebilir (IH-096, IH-105, IH-107; B14/B17).
İçerik (mevcut servislerden, yeni formül yok): günlük/aylık üretim (SCADA, geçerli saatler), gün başında verilmiş beklenti (forecast_daily P50/P10/P90),
sapma; olay kaydı (tür, süre, devre dışı güç) ve olay kaydına göre kapasite ağırlıklı kullanılabilirlik; ölçülen düzlem ışınımı varsa IEC 61724-1
temel PR (sıcaklık düzeltmesiz; yoksa yazılır); ay dönemi için PVQuant uzlaştırma kalemleri (mutabakat_service.pvquant_kalemleri — Doğruluk ile aynı
hesap) ve yüklü EPİAŞ bildirimi; sayaç kapsamı. Yıl/çeyrek döneminde aylık tablo (uzlaştırma yeniden hesabı yalnız ay döneminde).

Zamanlanmış gönderim (params_json.rapor_gonderim): aktif, ayın günü (1–28), alıcılar (boşsa alarm alıcıları); worker her gün 05:10 UTC bakar,
o ayın gününde önceki ayın raporunu HTML e-posta gövdesi olarak gönderir (posta_service; SMTP yoksa gönderilmez ve «yapılandırılmadı» yazılır);
son gönderim ve durumu params_json'a yazılır, denetim izine düşer. Dürüstlük: EPİAŞ uzlaştırması değildir; tutarlar yeniden hesaptır; kazanç/kayıp iddiası yok.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import text

from pvquant.db import tenant_baglami
from pvquant.ext.platform import rapor_sablon as rs

IST = ZoneInfo("Europe/Istanbul")
AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
_AY_RE = re.compile(r"^(20\d{2})-(0[1-9]|1[0-2])$"); _CEYREK_RE = re.compile(r"^(20\d{2})-Q([1-4])$"); _YIL_RE = re.compile(r"^(20\d{2})$")
GONDERIM_VARSAYILAN = {"aktif": False, "gun": 3, "alicilar": []}
GONDERIM_DENEME = 3   # başarısız gönderim için en çok yeniden deneme (günde bir)


# ---------------- dönem ----------------
def donem_cozumle(s: str | None, bugun: date | None = None) -> dict:
    """'YYYY-MM' | 'YYYY-QN' | 'YYYY' → {tur, bas, bit (hariç), etiket, kod}; verilmezse son tam ay. Gelecek dönem ValueError; süren dönem bugüne kırpılır."""
    b = bugun or datetime.now(IST).date()
    if not s:
        ilk = b.replace(day=1); onceki = (ilk - timedelta(days=1)).replace(day=1)
        s = onceki.strftime("%Y-%m")
    s = str(s).strip().upper()
    if m := _AY_RE.match(s):
        y, a = int(m.group(1)), int(m.group(2)); bas = date(y, a, 1); bit = date(y + (a == 12), a % 12 + 1, 1); tur = "ay"; etiket = f"{AYLAR[a - 1]} {y}"
    elif m := _CEYREK_RE.match(s):
        y, q = int(m.group(1)), int(m.group(2)); bas = date(y, 3 * q - 2, 1); bit = date(y + (q == 4), (3 * q) % 12 + 1, 1); tur = "ceyrek"; etiket = f"{y} {q}. çeyrek"
    elif m := _YIL_RE.match(s):
        y = int(m.group(1)); bas = date(y, 1, 1); bit = date(y + 1, 1, 1); tur = "yil"; etiket = f"{y} yılı"
    else:
        raise ValueError("donem YYYY-MM, YYYY-QN ya da YYYY olmalı")
    if bas > b:
        raise ValueError("gelecek dönem için rapor üretilmez")
    kirpildi = bit > b + timedelta(days=1)
    if kirpildi:
        bit = b + timedelta(days=1)   # süren dönem: bugüne kadar (bugün dâhil)
    return {"tur": tur, "kod": s, "bas": bas, "bit": bit, "etiket": etiket + (" (süren dönem, bugüne kadar)" if kirpildi else ""), "kirpildi": kirpildi,
            "saat": int((bit - bas).days * 24)}


def _utc(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time(), tzinfo=IST).astimezone(timezone.utc)


# ---------------- veri ----------------
def gunluk(tenant_id, plant: dict, bas: date, bit: date) -> pd.DataFrame:
    """Günlük (Türkiye günü) gerçekleşen kWh (geçerli SCADA; energy_kwh yoksa power_kw × 1 sa), saat sayısı, POA toplamı (Wh/m² → kWh/m²), beklenen P50/P10/P90."""
    with tenant_baglami(tenant_id) as s:
        g = pd.read_sql(text(
            "SELECT (ts_utc AT TIME ZONE 'Europe/Istanbul')::date AS gun, sum(COALESCE(energy_kwh, power_kw)) AS kwh, count(*) AS saat, "
            "sum(poa_wm2) / 1000.0 AS poa_kwh_m2, count(poa_wm2) AS poa_saat FROM scada_hourly "
            "WHERE plant_id = CAST(:p AS uuid) AND flag = 'valid' AND ts_utc >= :a AND ts_utc < :b GROUP BY 1 ORDER BY 1"),
            s.connection(), params={"p": plant["id"], "a": _utc(bas), "b": _utc(bit)})
        f = pd.read_sql(text("SELECT gun, p50_kwh, p10_kwh, p90_kwh FROM forecast_daily WHERE plant_id = CAST(:p AS uuid) AND gun >= :a AND gun < :b ORDER BY gun"),
                        s.connection(), params={"p": plant["id"], "a": bas, "b": bit})
    gunler = pd.DataFrame({"gun": pd.date_range(bas, bit - timedelta(days=1), freq="D").date})
    g["gun"] = pd.to_datetime(g["gun"]).dt.date if not g.empty else g.get("gun")
    f["gun"] = pd.to_datetime(f["gun"]).dt.date if not f.empty else f.get("gun")
    df = gunler.merge(g, on="gun", how="left").merge(f, on="gun", how="left")
    for c in ("kwh", "saat", "poa_kwh_m2", "poa_saat", "p50_kwh", "p10_kwh", "p90_kwh"):
        if c not in df.columns:
            df[c] = None
    df["saat"] = df["saat"].fillna(0).astype(int); df["poa_saat"] = df["poa_saat"].fillna(0).astype(int)
    df["sapma_pct"] = ((df["kwh"] - df["p50_kwh"]) / df["p50_kwh"] * 100).where((df["p50_kwh"] > 0) & df["kwh"].notna())
    return df


def olaylar(tenant_id, plant: dict, bas: date, bit: date) -> list[dict]:
    from pvquant.services import olay_service
    kap = float(plant.get("ac_limit_kw") or plant.get("capacity_kwp") or 0.0)
    a, b = _utc(bas), _utc(bit)
    out = []
    for o in olay_service.aralik(tenant_id, plant["id"], a, b):
        s0 = max(o["baslangic"], a); s1 = min(o["bitis"] or b, b)
        sure = max(0.0, (s1 - s0).total_seconds() / 3600)
        kw = float(o["etkilenen_kw"]) if o.get("etkilenen_kw") else kap
        out.append({"tur": o["tur"], "etiket": olay_service.TUR_ETIKET.get(o["tur"], o["tur"]), "baslangic": o["baslangic"].astimezone(IST).isoformat(timespec="minutes"),
                    "bitis": o["bitis"].astimezone(IST).isoformat(timespec="minutes") if o.get("bitis") else None, "sure_saat": round(sure, 1), "etkilenen_kw": kw,
                    "donem_icinde_saat": round(sure, 1), "neden": o.get("neden"), "istisna": bool(olay_service.TUR_KURAL.get(o["tur"], {}).get("istisna")),
                    "ariza": o["tur"] in ("ariza", "hasar")})
    return out


def kullanilabilirlik_olay(olaylar_: list[dict], kap_kw: float, saat: int) -> dict | None:
    """Olay kaydına göre, kapasite ağırlıklı zaman kullanılabilirliği: 1 − Σ(arıza/hasar süresi × devre dışı güç / kapasite) / dönem saati; planlı
    bakım, talimat, acil kesme ve şebeke kesintisi istisnadır (santralın elinde değil). SCADA tabanlı kullanılabilirlik Doğruluk sayfasındadır."""
    if not kap_kw or not saat:
        return None
    ariza = sum(o["sure_saat"] * min(1.0, o["etkilenen_kw"] / kap_kw) for o in olaylar_ if o["ariza"])
    istisna = sum(o["sure_saat"] * min(1.0, o["etkilenen_kw"] / kap_kw) for o in olaylar_ if o["istisna"])
    return {"oran": round(1 - ariza / saat, 4), "ariza_esdeger_saat": round(ariza, 1), "istisna_esdeger_saat": round(istisna, 1), "saat": saat,
            "not": "olay kaydına göre (arıza ve hasar); planlı bakım, talimat, acil kesme ve şebeke kesintisi istisna; devre dışı güç girilmemişse tesisin tamamı"}


def pr_temel(df: pd.DataFrame, kwp: float) -> dict | None:
    """IEC 61724-1 temel performans oranı: PR = (E_ac / P_stc) / (H_poa / G_stc); sıcaklık düzeltmesi yok. POA ölçümü olan günlerle (≥ 10 gün)."""
    m = df["poa_saat"] > 0
    if int(m.sum()) < 10 or not kwp:
        return None
    e = float(df.loc[m, "kwh"].fillna(0).sum()); h = float(df.loc[m, "poa_kwh_m2"].sum())
    if h <= 0:
        return None
    return {"pr": round((e / kwp) / h, 3), "gun": int(m.sum()), "e_kwh": round(e, 1), "h_kwh_m2": round(h, 1),
            "not": "IEC 61724-1 temel PR (sıcaklık düzeltmesiz; kırpma dışlanmadı); ölçülen düzlem ışınımı olan günler"}


def performans(tenant_id, plant: dict, d: dict, bugun: date | None = None) -> dict | None:
    """v2.542 (P8b-2): dönemin ölçülen havayla beklenen üretimi ve EPI'si (performans_service.donem); referans PR ve ışınım endeksi notuyla.
    Hesap alınamazsa None (rapor düşmez); beklenen yazılamayan aylar tire."""
    try:
        from pvquant.services import performans_service as ps
        r = ps.donem(tenant_id, plant, d["bas"], d["bit"] - timedelta(days=1), bugun)   # donem_cozumle bit HARİÇ; ps.donem bit DÂHİL
    except Exception as e:   # noqa: BLE001
        return {"durum": "hata", "hata": f"{type(e).__name__}: {e}"}
    if r.get("durum") != "ok":
        return {"durum": r.get("durum"), "not": r.get("not"), "sensor": r.get("sensorler", {}).get("etiket")}
    tp = r["toplam"]
    return {"durum": "ok", "referans": r["referans"]["etiket"], "sicaklik": r["sicaklik"]["etiket"], "sensor": r["sensorler"]["etiket"],
            "epi": tp["epi"], "uretim_kwh": tp["uretim_kwh"], "beklenen_kwh": tp["beklenen_kwh"], "ay_ok": tp["ay_ok"], "ay": tp["ay"],
            "isinim": {"durum": r["isinim"]["durum"], "yil": r["isinim"]["yil"], "not": r["isinim"]["not"]},
            "aylar": [{"ay": a["ay"], "uretim_kwh": a["uretim_kwh"], "beklenen_kwh": a["beklenen_kwh"], "epi": a["epi"], "epi_temiz": a["epi_temiz"],
                       "isinim_endeksi": a.get("isinim_endeksi"), "poa_kapsam": a["poa_kapsam"]} for a in r["aylar"]],
            "not": r["not"]}


def uzlastirma(tenant_id, plant: dict, d: dict) -> dict | None:
    """Ay döneminde PVQuant uzlaştırma kalemleri (yeniden hesap) + yüklü EPİAŞ bildirimi; öbür dönemlerde None (not yazılır)."""
    if d["tur"] != "ay":
        return None
    from pvquant.services import mutabakat_service
    try:
        pv = mutabakat_service.pvquant_kalemleri(tenant_id, plant, d["bas"])
        bil = mutabakat_service.bildirim(tenant_id, plant["id"], d["bas"])
    except Exception as e:   # noqa: BLE001
        return {"hata": str(e)[:160]}
    kal = pv.get("kalemler") or {}
    satirlar = []
    for kod, etiket in (("imbalance", "Enerji dengesizlik tutarı"), ("kupst", "KGÜP sapma tutarı (KÜPST)"), ("res", "YEK alacağı (kaba)")):
        if kod in kal:
            satirlar.append({"kalem": etiket, "pvquant_alacak_tl": kal[kod].get("alacak_tl"), "pvquant_borc_tl": kal[kod].get("borc_tl"),
                             "epias_alacak_tl": None, "epias_borc_tl": None})
    if bil:
        for r in bil["kalemler"]:
            for s_ in satirlar:
                if (r["kod"] == "imbalance" and s_["kalem"].startswith("Enerji")) or (r["kod"] == "kupst" and "KÜPST" in s_["kalem"]) or (r["kod"] == "res" and s_["kalem"].startswith("YEK")):
                    s_["epias_alacak_tl" if r["yon"] == "alacak" else "epias_borc_tl"] = r["tutar_tl"]
    return {"satirlar": satirlar, "saat": pv.get("saat", 0), "beklenen_saat": pv.get("beklenen_saat"), "guvenilirlik": (pv.get("guvenilirlik") or {}).get("etiket"),
            "nedenler": (pv.get("guvenilirlik") or {}).get("nedenler", []), "bildirim": ({"surum": bil["surum_etiket"], "zaman": bil["zaman"]} if bil else None),
            "sayac": pv.get("sayac"), "kural_surumu": pv.get("kural_surumu"), "hata": pv.get("hata"),
            "uretim_kaynak": (pv.get("uretim_kaynak") or {}).get("etiket"), "kupst_kaynak": pv.get("kupst_kaynak")}   # v2.541 (EK-2 DK-367): gerçekleşen kaynağı ve katsayı kaynağı raporda


# ---------------- rapor ----------------
def veri(tenant_id, plant: dict, donem: str | None = None, bugun: date | None = None) -> dict:
    d = donem_cozumle(donem, bugun)
    df = gunluk(tenant_id, plant, d["bas"], d["bit"])
    kap = float(plant.get("ac_limit_kw") or plant.get("capacity_kwp") or 0.0); kwp = float(plant.get("capacity_kwp") or 0.0)
    ol = olaylar(tenant_id, plant, d["bas"], d["bit"])
    uretim = float(df["kwh"].fillna(0).sum()); beklenen = float(df["p50_kwh"].fillna(0).sum())
    saat_t = int(df["saat"].sum()); p50_var = bool(df["p50_kwh"].notna().any())
    ortak = df["kwh"].notna() & df["p50_kwh"].notna()
    u_o = float(df.loc[ortak, "kwh"].sum()); b_o = float(df.loc[ortak, "p50_kwh"].sum())
    # 02.11 inceleme (veri bütünlüğü): ölçüm hiç yoksa üretim 0 değil «yok» (None); beklenen de arşivde gün başı tahmini yoksa None.
    ozet = {"uretim_kwh": (round(uretim, 1) if saat_t > 0 else None), "beklenen_kwh": (round(beklenen, 1) if p50_var else None), "ortak_gun": int(ortak.sum()), "sapma_pct": (round((u_o - b_o) / b_o * 100, 1) if b_o > 0 else None),
            "gun_sayisi": int(len(df)), "veri_gun": int((df["saat"] > 0).sum()), "saat": int(df["saat"].sum()), "beklenen_saat": d["saat"],
            "kapsam_pct": round(float(df["saat"].sum()) / d["saat"] * 100, 1) if d["saat"] else None,
            "olay": len(ol), "ariza": sum(1 for o in ol if o["ariza"]), "en_iyi_gun": None, "en_dusuk_gun": None}
    # veri durumu: tam (ölçülü saat ≥ %99,5) | kismi | yok — önizleme, HTML ve JSON aynı sınıfı taşır; eksik saat tahminle doldurulmaz
    kp = ozet["kapsam_pct"] or 0.0
    ozet["veri_durumu"] = "yok" if saat_t == 0 else ("tam" if kp >= 99.5 else "kismi")
    ozet["veri_durumu_metni"] = {"yok": f"Veri yok: dönemde geçerli SCADA ölçümü yok; üretim, sapma ve performans oranı verilmez ({d['saat']} saat beklenirdi).",
                                 "tam": f"Tam: dönemin {d['saat']} saatinin {saat_t}'i ölçülü.",
                                 "kismi": f"Kısmi: {saat_t}/{d['saat']} saat ölçülü (%{kp:.0f}); toplamlar yalnız ölçülü saatleri kapsar, eksik saatler tahminle doldurulmaz."}[ozet["veri_durumu"]]
    if d.get("kirpildi"):
        ozet["veri_durumu_metni"] += " Süren dönem; bugüne kadar."
    if (df["saat"] > 0).any():
        v = df[df["saat"] > 0]; ozet["en_iyi_gun"] = {"gun": str(v.loc[v["kwh"].idxmax(), "gun"]), "kwh": round(float(v["kwh"].max()), 1)}
        ozet["en_dusuk_gun"] = {"gun": str(v.loc[v["kwh"].idxmin(), "gun"]), "kwh": round(float(v["kwh"].min()), 1)}
    aylik = None
    if d["tur"] != "ay":
        x = df.copy(); x["ay"] = pd.to_datetime(x["gun"]).dt.strftime("%Y-%m")
        a = x.groupby("ay").agg(uretim_kwh=("kwh", lambda s: float(s.fillna(0).sum())), beklenen_kwh=("p50_kwh", lambda s: float(s.fillna(0).sum())), saat=("saat", "sum"), gun=("gun", "count")).reset_index()
        a["sapma_pct"] = ((a["uretim_kwh"] - a["beklenen_kwh"]) / a["beklenen_kwh"] * 100).where(a["beklenen_kwh"] > 0)
        aylik = [{k: (None if pd.isna(v) else (round(float(v), 1) if isinstance(v, float) else int(v) if not isinstance(v, str) else v)) for k, v in r.items()} for r in a.to_dict("records")]
    gun_satirlari = [{"gun": str(r["gun"]), "kwh": (None if pd.isna(r["kwh"]) else round(float(r["kwh"]), 1)), "saat": int(r["saat"]),
                      "p50_kwh": (None if pd.isna(r["p50_kwh"]) else round(float(r["p50_kwh"]), 1)), "p10_kwh": (None if pd.isna(r["p10_kwh"]) else round(float(r["p10_kwh"]), 1)),
                      "p90_kwh": (None if pd.isna(r["p90_kwh"]) else round(float(r["p90_kwh"]), 1)), "sapma_pct": (None if pd.isna(r["sapma_pct"]) else round(float(r["sapma_pct"]), 1))}
                     for r in df.to_dict("records")]
    try:   # v2.559 (V4): veri kaynağı niteliği (kaynak / nitelik / revizyon) — izlenebilir doğruluk
        from pvquant.services import kaynak_secim_service as _ks
        nitelik = _ks.nitelik_ozeti(tenant_id, plant, _utc(d["bas"]), _utc(d["bit"]) + timedelta(days=1))
    except Exception:   # noqa: BLE001
        nitelik = None
    return {"donem": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in d.items()}, "santral": plant.get("name"), "kapasite_kwp": kwp, "ac_kw": plant.get("ac_limit_kw"),
            "ozet": ozet, "gunler": gun_satirlari if d["tur"] == "ay" else [], "aylar": aylik, "olaylar": ol, "kaynak_niteligi": nitelik,
            "kullanilabilirlik": kullanilabilirlik_olay(ol, kap, d["saat"]), "pr": pr_temel(df, kwp), "uzlastirma": uzlastirma(tenant_id, plant, d),
            "performans": performans(tenant_id, plant, d, bugun),   # v2.542 (P8b-2): ölçülen havayla beklenen üretim, EPI, ışınım endeksi
            "notlar": ["Beklenen = gün başlamadan verilmiş tahminin günlük P50 toplamı (arşiv; geriye dönük değişmez); sapma yalnız iki değerin de bulunduğu günlerde.",
                       "Üretim SCADA ölçümüdür (geçerli saatler); EPİAŞ uzlaştırmaya esas sayaç verisi değildir.",
                       "Uzlaştırma kalemleri PVQuant'ın yürürlükteki kuralla yeniden hesabıdır; EPİAŞ bildirimi esastır." if d["tur"] == "ay" else
                       "Uzlaştırma kalemlerinin yeniden hesabı yalnız ay döneminde verilir; çeyrek ve yıl için Mutabakat sayfasına bakın."],
            "kaynaklar": [("Üretim: SCADA saatlik ölçümü (geçerli saatler). " + nitelik["metin"]) if nitelik else "Üretim: SCADA saatlik ölçümü (geçerli saatler)", "Beklenen: tahmin arşivi, gün başı P50 (forecast_daily; geriye dönük değişmez)",
                          "Olaylar ve kullanılabilirlik: olay kaydı", "Uzlaştırma: PVQuant yeniden hesabı + yüklü EPİAŞ bildirimi (Mutabakat)" if d["tur"] == "ay" else "Uzlaştırma: yalnız ay döneminde",
                          "PR: SCADA düzlem ışınımı (POA) ölçümü" if pr_temel(df, kwp) else "PR: ölçülen düzlem ışınımı yok"],
            "uretim_zamani": datetime.now(IST).isoformat(timespec="minutes")}


def _tl(v) -> str:
    return "—" if v is None else f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _kwh(v) -> str:
    return "—" if v is None else f"{v:,.0f}".replace(",", ".")


def rapor(tenant_id, plant: dict, donem: str | None = None, bugun: date | None = None) -> tuple[rs.Rapor, dict]:
    v = veri(tenant_id, plant, donem, bugun); oz = v["ozet"]; d = v["donem"]
    bol: list = []
    ozet_df = pd.DataFrame([{"Veri durumu": oz["veri_durumu_metni"], "Üretim (kWh)": _kwh(oz["uretim_kwh"]), "Beklenen P50 (kWh)": _kwh(oz["beklenen_kwh"]),
                             "Sapma (ortak günler)": ("—" if oz["sapma_pct"] is None else f"%{oz['sapma_pct']:+.1f}".replace(".", ",")),
                             "Veri kapsamı": f"{oz['saat']}/{oz['beklenen_saat']} saat (%{oz['kapsam_pct'] or 0:.0f})", "Olay": f"{oz['olay']} ({oz['ariza']} arıza/hasar)",
                             "Kullanılabilirlik (olay kaydı)": ("—" if not v["kullanilabilirlik"] else f"%{v['kullanilabilirlik']['oran'] * 100:.1f}".replace(".", ",")),
                             "PR (temel)": ("ölçülen düzlem ışınımı yok" if not v["pr"] else f"{v['pr']['pr']:.3f}".replace(".", ",")),
                             "EPI (ölçülen hava)": (f"%{v['performans']['epi'] * 100:.1f}".replace(".", ",") if v.get("performans") and v["performans"].get("durum") == "ok" and v["performans"].get("epi") is not None else "—")}]).T.rename(columns={0: "Değer"})   # v2.542
    bol.append(("Özet", ozet_df))
    if v["gunler"]:
        g = pd.DataFrame(v["gunler"]).rename(columns={"gun": "Gün", "kwh": "Üretim (kWh)", "saat": "Saat", "p50_kwh": "Beklenen P50 (kWh)", "p10_kwh": "P10", "p90_kwh": "P90", "sapma_pct": "Sapma %"})
        bol.append(("Günlük üretim ve beklenti", g))
    if v["aylar"]:
        a = pd.DataFrame(v["aylar"]).rename(columns={"ay": "Ay", "uretim_kwh": "Üretim (kWh)", "beklenen_kwh": "Beklenen P50 (kWh)", "saat": "Saat", "gun": "Gün", "sapma_pct": "Sapma %"})
        bol.append(("Aylık üretim ve beklenti", a))
    if v.get("kaynak_niteligi"):   # v2.559 (V4): veri kaynağı niteliği tablosu
        kn = v["kaynak_niteligi"]; satirlar = [{"Kaynak": x["etiket"], "Nitelik": "üretim serisi (geçerli)", "Saat": x["saat"]} for x in kn["uretim_serisi"]]
        satirlar += [{"Kaynak": x["etiket"], "Nitelik": f"gölge görünüm · {x['tamlik_etiketi']}", "Saat": x["saat"]} for x in (kn.get("golge") or {}).get("kaynaklar", [])]
        if satirlar:
            bol.append(("Veri kaynağı niteliği", pd.DataFrame(satirlar)))
    if v["olaylar"]:
        o = pd.DataFrame([{"Tür": x["etiket"], "Başlangıç": x["baslangic"], "Bitiş": x["bitis"] or "açık", "Süre (sa)": x["sure_saat"], "Devre dışı güç (kW)": x["etkilenen_kw"],
                           "Not": x["neden"] or ""} for x in v["olaylar"]])
        bol.append(("Olay kaydı", o))
    else:
        bol.append(("Olay kaydı", "Dönemde olay kaydı yok."))
    u = v["uzlastirma"]
    if u and u.get("satirlar"):
        t = pd.DataFrame([{"Kalem": s["kalem"], "PVQuant alacak (TL)": _tl(s["pvquant_alacak_tl"]), "PVQuant borç (TL)": _tl(s["pvquant_borc_tl"]),
                           "EPİAŞ alacak (TL)": _tl(s["epias_alacak_tl"]), "EPİAŞ borç (TL)": _tl(s["epias_borc_tl"])} for s in u["satirlar"]])
        bol.append(("Uzlaştırma kalemleri (yeniden hesap ↔ EPİAŞ bildirimi)", t))
        bol.append(("Uzlaştırma notu", f"{u['guvenilirlik'] or ''}: {'; '.join(u['nedenler'])}. " + (f"EPİAŞ bildirimi: {u['bildirim']['surum']}, yükleme {u['bildirim']['zaman']}." if u["bildirim"] else "EPİAŞ bildirimi yüklenmedi (Mutabakat sayfası).")
                     + (f" Sayaç: {u['sayac']['yuklu']}/{u['sayac']['toplam_saat']} saat." if u.get("sayac") and u["sayac"].get("yuklu") else "")
                     + (f" Gerçekleşen üretim kaynağı: {u['uretim_kaynak']}." if u.get("uretim_kaynak") else "")
                     + (f" KÜPST katsayı kaynağı: {u['kupst_kaynak']}." if u.get("kupst_kaynak") else "")
                     + " Bu bölümdeki yeniden hesap, SCADA tabanlı doğruluk karnesiyle aynı veri değildir; uzlaştırma EPİAŞ sayacına (UEVM) dayanır."))   # v2.541 (DK-367)
    elif u and u.get("hata"):
        bol.append(("Uzlaştırma kalemleri", f"Hesap alınamadı: {u['hata']}"))
    if v["pr"]:
        bol.append(("Performans oranı", f"PR {v['pr']['pr']:.3f} — {v['pr']['gun']} gün; E {_kwh(v['pr']['e_kwh'])} kWh, H {v['pr']['h_kwh_m2']} kWh/m². {v['pr']['not']}."))
    pf = v.get("performans")   # v2.542 (P8b-2): ölçülen havayla beklenen üretim ve EPI
    if pf and pf.get("durum") == "ok":
        e = pd.DataFrame([{"Ay": x["ay"], "Üretim (kWh)": _kwh(x["uretim_kwh"]), "Beklenen, ölçülen hava (kWh)": ("—" if x["beklenen_kwh"] is None else _kwh(x["beklenen_kwh"])),
                           "EPI": ("—" if x["epi"] is None else f"%{x['epi'] * 100:.1f}".replace(".", ",")),
                           "EPI (kırpma/kısıntı dışı)": ("—" if x["epi_temiz"] is None else f"%{x['epi_temiz'] * 100:.1f}".replace(".", ",")),
                           "Işınım endeksi": ("—" if x["isinim_endeksi"] is None else f"{x['isinim_endeksi']:.2f}".replace(".", ",")),
                           "Işınım ölçüm kapsamı": f"%{x['poa_kapsam'] * 100:.0f}"} for x in pf["aylar"]])
        bol.append(("Beklenen üretim (ölçülen hava) ve EPI", e))
        bol.append(("Beklenen üretim notu", f"Referans PR: {pf['referans']}. Hücre sıcaklığı: {pf['sicaklik']}. Işınım sensörü: {pf['sensor']}. {pf['isinim']['not']} {pf['not']}"))
    elif pf and pf.get("durum") not in (None, "hata"):
        bol.append(("Beklenen üretim (ölçülen hava)", pf.get("not") or "Hesaplanamadı."))
    bol.append(("Notlar", " ".join(v["notlar"]) + " Kaynaklar: " + "; ".join(v["kaynaklar"]) + "."))
    r = rs.Rapor(baslik=f"PVQuant dönem raporu — {plant.get('name', '')}", donem=d["etiket"], santral=plant.get("name", ""), bolumler=bol)
    try:
        from pvquant.services.kaynak_service import rapor_kunye_satiri
        r.kunye = rapor_kunye_satiri() + f" Üretim zamanı {v['uretim_zamani']}."
    except Exception:   # noqa: BLE001
        r.kunye = f"Veriler PVQuant tarafından işlenmiştir. Üretim zamanı {v['uretim_zamani']}."
    return r, v


def html(r: rs.Rapor) -> str:
    from pvquant.services.sablon_rapor_service import html_sar
    return html_sar(r)


# ---------------- zamanlanmış gönderim ----------------
def gonderim_ayari(pj: dict | None) -> dict:
    g = dict(GONDERIM_VARSAYILAN); g.update({k: v for k, v in ((pj or {}).get("rapor_gonderim") or {}).items() if k in ("aktif", "gun", "alicilar", "son_gonderim", "son_durum", "son_donem", "deneme")})
    g["aktif"] = bool(g.get("aktif")); g["gun"] = int(g.get("gun") or 3); g["alicilar"] = [x for x in (g.get("alicilar") or []) if isinstance(x, str) and x.strip()]
    return g


def gonderim_dogrula(g: dict) -> dict:
    out: dict = {}
    if "aktif" in g:
        if not isinstance(g["aktif"], bool):
            raise ValueError("aktif")
        out["aktif"] = g["aktif"]
    if "gun" in g:
        try:
            n = int(g["gun"])
        except (TypeError, ValueError):
            raise ValueError("gun")
        if not (1 <= n <= 28):
            raise ValueError("gun")
        out["gun"] = n
    if "alicilar" in g:
        al = g["alicilar"] or []
        if not isinstance(al, list) or any(not isinstance(x, str) or "@" not in x or len(x) > 120 for x in al) or len(al) > 10:
            raise ValueError("alicilar")
        out["alicilar"] = [x.strip() for x in al if x.strip()]
    return out


def alicilar(plant: dict) -> list[str]:
    from pvquant.services import alarm_service
    g = gonderim_ayari(alarm_service._pj(plant))
    return g["alicilar"] or alarm_service.alicilar(plant)


def gonder(tenant_id, plant: dict, donem: str | None = None, bugun: date | None = None, kaynak: str = "zamanlanmis") -> dict:
    """Dönem raporunu HTML gövdeli e-postayla alıcılara gönderir; sonucu params_json.rapor_gonderim'e ve denetim izine yazar. SMTP yoksa gönderilmez."""
    from pvquant.services import posta_service, plant_service, denetim_service
    kime = alicilar(plant)
    try:
        r, v = rapor(tenant_id, plant, donem, bugun)
    except Exception as e:   # noqa: BLE001 — 02.11 inceleme: rapor üretim hatası, e-posta hatasından ayrı tutulur ve kayda düşer
        print("[rapor_gonderim][rapor]", type(e).__name__, e)
        d = donem_cozumle(donem, bugun)
        r, v, durum = None, {"donem": {k: (x.isoformat() if isinstance(x, date) else x) for k, x in d.items()}}, "rapor_hatasi"
    if r is None:
        pass
    elif not kime:
        durum = "alici_yok"
    elif not posta_service.yapilandirildi():
        durum = "posta_yapilandirilmadi"
    else:
        ok = posta_service.gonder(", ".join(kime), f"[PVQuant] Dönem raporu — {plant.get('name', '')} — {v['donem']['etiket']}", r.markdown(), html=html(r))
        durum = "gonderildi" if ok else "gonderim_hatasi"
    g = gonderim_ayari(plant.get("params_json") if isinstance(plant.get("params_json"), dict) else None)
    # deneme sayacı: aynı dönem için başarısız denemeler sayılır (yeniden deneme kuralı için); başarıda ya da yeni dönemde sıfırlanır
    deneme = (int(g.get("deneme") or 0) + 1) if (durum != "gonderildi" and g.get("son_donem") == v["donem"]["kod"]) else (0 if durum == "gonderildi" else 1)
    g.update({"son_gonderim": datetime.now(IST).isoformat(timespec="minutes"), "son_durum": durum, "son_donem": v["donem"]["kod"], "deneme": deneme})
    try:
        plant_service.params_birlestir(tenant_id, plant["id"], rapor_gonderim={k: g[k] for k in ("aktif", "gun", "alicilar", "son_gonderim", "son_durum", "son_donem", "deneme")})
        denetim_service.kaydet("musteri", "rapor_gonderim", aktor_id=None, tenant_id=tenant_id, nesne_tur="plant", nesne_id=plant["id"],
                               ayrinti={"donem": v["donem"]["kod"], "durum": durum, "alici": len(kime), "kaynak": kaynak})
    except Exception as e:   # noqa: BLE001 — kayıt düşse de gönderim sonucu döner
        print("[rapor_gonderim][kayit]", type(e).__name__, e)
    return {"durum": durum, "donem": v["donem"]["kod"], "etiket": v["donem"]["etiket"], "alici": len(kime), "zaman": g["son_gonderim"]}


def gonderilmeli_mi(pj: dict | None, bugun: date) -> bool:
    """Worker: aktif, bugün ayın gönderim günü (ya da geçmişse ve bu ay henüz gönderilmemişse) ve bu ayın dönemi daha gönderilmemişse.
    02.11 inceleme: başarısız deneme (e-posta/rapor hatası, SMTP yok, alıcı yok) dönemi «bitti» saymaz — en çok GONDERIM_DENEME kez,
    günde bir yeniden denenir; başarı (gonderildi) dönemi kapatır. Elle «Şimdi gönder» de aynı sayaçla kaydedilir, yineleme olmaz."""
    g = gonderim_ayari(pj)
    if not g["aktif"] or bugun.day < g["gun"]:
        return False
    hedef = (bugun.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")   # önceki ay
    if g.get("son_donem") != hedef:
        return True
    if g.get("son_durum") in (None, "", "gonderildi"):   # gönderildi (ya da durumu yazılmamış eski kayıt) → dönem kapalı
        return False
    if g.get("son_gonderim", "")[:10] == bugun.isoformat():   # bugün denendi
        return False
    return int(g.get("deneme") or 0) < GONDERIM_DENEME
