"""10.11.2026 v2.573 (Faz 1 paketi F1-B, Stage 3) — ÖLÇÜM UYGUNLUK KATMANI: bir dönemdeki HER saatin doğrulamaya girip giremeyeceği ve nedeni.

Bugüne kadar karne yalnız `scada_hourly.flag='valid'` satırlarını INNER JOIN ile alıyor; eksik saat sessizce atlanıyor, arıza/bakım/kısıntı
olayı dışlanmıyor, kısmi saat geçerli sayılıyor, dışlanan saatlerin nedeni hiçbir yerde sayılmıyordu. Bu katman tek bir tablo döner:
her beklenen saat için `durum` (olculdu | dislandi) ve `neden`:
  eksik               satır yok (0 değil, bilinmiyor)
  bayrak:<flag>       yükleme doğrulaması geçerli saymadı (negative_power, over_capacity, frozen_value, night_production, duplicate_time,
                      dst_ambiguous, unparseable, gunluk_ozet, partial_hour, kisinti, anomali …)
  kismi_saat          kapsama_dk < KISMI_SAAT_DK (eski yüklemelerde kapsama NULL → kural uygulanmaz, «bilinmiyor» sayılır)
  olay:<tür>          olay kaydında üretimi etkileyen olay (planlı bakım, arıza, talimat, acil kesme, şebeke kesintisi, hasar); tahmin bu saatte
                      santralın yapabileceğini değil olayı görür — tahmin hatası sayılmaz, ayrı raporlanır
  sayac:<nitelik>     sayaç kaynağında saat ölçülmüş değil (tahmini / doldurulmuş / elle)
Öncelik: eksik > bayrak > kismi_saat > olay > olculdu. `kirpma` dışlamaz, bilgi sütunudur (karne sayar, ayrı raporlanır).
Ölçüm sınırı açıkça yazılır: SCADA = tesis brüt AC, sayaç = bağlantı noktası net / uzlaştırma. Hiçbir eksik saat 0 sayılmaz.
Saf çekirdek (`siniflandir`, `dokum`) DB'siz; `saat_durumlari` DB okur, hiçbir tabloya yazmaz. Çekirdek tahmin matematiğine dokunmaz.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

KISMI_SAAT_DK = 45
DURUM_OLCULDU = "olculdu"
DURUM_DISLANDI = "dislandi"
NEDEN_EKSIK = "eksik"
NEDEN_KISMI = "kismi_saat"
SINIR = {"scada": ("plant_gross_ac", "tesis brüt AC (SCADA)"), "sayac": ("pcc_net", "bağlantı noktası net (sayaç)")}
SAYAC_OLCULMUS = "olculmus"
SURUM = "2026-11-10"


def olay_turleri() -> list[str]:
    """Üretimi etkileyen olay türleri: EAK'yi düşüren ya da kullanılabilirlik istisnası olanlar (uzaktan açma hariç)."""
    from pvquant.services.olay_service import TUR_KURAL
    return [t for t, k in TUR_KURAL.items() if k.get("eak_dusur") or k.get("istisna")]


def saat_izgarasi(bas: datetime, bit: datetime) -> pd.DatetimeIndex:
    """[bas, bit) saat başı UTC ızgarası."""
    a = pd.Timestamp(bas); b = pd.Timestamp(bit)
    a = a.tz_localize("UTC") if a.tzinfo is None else a.tz_convert("UTC")
    b = b.tz_localize("UTC") if b.tzinfo is None else b.tz_convert("UTC")
    return pd.date_range(a.floor("h"), b, freq="h", inclusive="left", name="ts_utc")


def olay_saatleri(olaylar: list[dict], bas: datetime, bit: datetime) -> dict:
    """{ts_utc (saat başı UTC): tür} — aynı saatte birden çok olay varsa türler «+» ile birleşir (alfabetik)."""
    out: dict = {}
    b = pd.Timestamp(bit); b = b.tz_localize("UTC") if b.tzinfo is None else b.tz_convert("UTC")
    a = pd.Timestamp(bas); a = a.tz_localize("UTC") if a.tzinfo is None else a.tz_convert("UTC")
    for o in olaylar or []:
        t = pd.Timestamp(o["baslangic"]); t = (t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")).floor("h")
        son = o.get("bitis"); son = b if son is None else pd.Timestamp(son)
        son = son.tz_localize("UTC") if son.tzinfo is None else son.tz_convert("UTC")
        while t < son and t < b:
            if t >= a:
                turler = set(out.get(t, "").split("+")) - {""} | {str(o["tur"])}
                out[t] = "+".join(sorted(turler))
            t += pd.Timedelta(hours=1)
    return out


def siniflandir(izgara: pd.DatetimeIndex, olcum: pd.DataFrame | None, olaylar: dict | None = None, kaynak: str = "scada") -> pd.DataFrame:
    """SAF. izgara: beklenen saatler (UTC). olcum: ts_utc indeksli; scada için power_kw/energy_kwh/flag/kirpma/kapsama_dk,
    sayaç için veris_kwh/nitelik. Döner: ts_utc, kwh, durum, neden, kirpma, kapsama_dk."""
    o = olcum if olcum is not None else pd.DataFrame()
    if not o.empty:
        o = o.copy()
        ix = pd.DatetimeIndex(o.index)
        o.index = ix.tz_localize("UTC") if ix.tz is None else ix.tz_convert("UTC")
        o = o[~o.index.duplicated(keep="first")]
    mevcut = pd.Series(izgara.isin(o.index), index=izgara) if not o.empty else pd.Series(False, index=izgara)   # satırı olan saatler
    o = o.reindex(izgara)
    df = pd.DataFrame(index=izgara)
    if kaynak == "sayac":
        df["kwh"] = pd.to_numeric(o.get("veris_kwh"), errors="coerce") if "veris_kwh" in o else float("nan")
        var = mevcut & df["kwh"].notna()
        nitelik = o["nitelik"].astype(object) if "nitelik" in o else pd.Series(None, index=izgara, dtype=object)
        df["kirpma"] = False
        df["kapsama_dk"] = pd.Series(float("nan"), index=izgara)
        neden = pd.Series(NEDEN_EKSIK, index=izgara, dtype=object)
        sayac_degil = var & nitelik.notna() & (nitelik != SAYAC_OLCULMUS)
        neden[var] = DURUM_OLCULDU
        neden[sayac_degil] = "sayac:" + nitelik[sayac_degil].astype(str)
    else:
        e = pd.to_numeric(o.get("energy_kwh"), errors="coerce") if "energy_kwh" in o else pd.Series(float("nan"), index=izgara)
        p = pd.to_numeric(o.get("power_kw"), errors="coerce") if "power_kw" in o else pd.Series(float("nan"), index=izgara)
        df["kwh"] = e.where(e.notna(), p)
        var = mevcut
        flag = o["flag"].astype(object) if "flag" in o else pd.Series("valid", index=izgara, dtype=object)
        df["kirpma"] = o["kirpma"].fillna(False).astype(bool) if "kirpma" in o else False
        df["kapsama_dk"] = pd.to_numeric(o.get("kapsama_dk"), errors="coerce") if "kapsama_dk" in o else pd.Series(float("nan"), index=izgara)
        neden = pd.Series(NEDEN_EKSIK, index=izgara, dtype=object)
        neden[var] = DURUM_OLCULDU
        bayrakli = var & flag.notna() & (flag != "valid")
        neden[bayrakli] = "bayrak:" + flag[bayrakli].astype(str)
        kismi = var & ~bayrakli & df["kapsama_dk"].notna() & (df["kapsama_dk"] < KISMI_SAAT_DK)
        neden[kismi] = NEDEN_KISMI
    if olaylar:
        for ts, tur in olaylar.items():
            t = pd.Timestamp(ts); t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
            if t in neden.index and neden[t] == DURUM_OLCULDU:
                neden[t] = f"olay:{tur}"
    df["neden"] = neden
    df["durum"] = (neden == DURUM_OLCULDU).map({True: DURUM_OLCULDU, False: DURUM_DISLANDI})
    df.loc[df["durum"] == DURUM_DISLANDI, "kwh"] = df.loc[df["durum"] == DURUM_DISLANDI, "kwh"].where(df.loc[df["durum"] == DURUM_DISLANDI, "neden"] != NEDEN_EKSIK)
    return df.reset_index()[["ts_utc", "kwh", "durum", "neden", "kirpma", "kapsama_dk"]]


def dokum(df: pd.DataFrame, kaynak: str = "scada") -> dict:
    """Dışlama dökümü: beklenen saat, ölçülen saat, kapsama %, neden → saat sayısı, kırpma saati, ölçüm sınırı."""
    n = int(len(df)); olc = int((df["durum"] == DURUM_OLCULDU).sum()) if n else 0
    dis = df.loc[df["durum"] == DURUM_DISLANDI, "neden"].value_counts().to_dict() if n else {}
    sinir_kod, sinir_etiket = SINIR.get(kaynak, SINIR["scada"])
    return {"beklenen_saat": n, "olculdu_saat": olc, "kapsama_pct": (round(olc / n * 100, 1) if n else None),
            "dislanan": {str(k): int(v) for k, v in sorted(dis.items(), key=lambda kv: (-kv[1], kv[0]))},
            "kirpma_saat": int(df["kirpma"].fillna(False).astype(bool).sum()) if n else 0,
            "kapsama_bilinmeyen_saat": int((df["kapsama_dk"].isna() & (df["durum"] == DURUM_OLCULDU)).sum()) if n else 0,
            "kaynak": kaynak, "sinir": sinir_kod, "sinir_etiketi": sinir_etiket, "surum": SURUM}


def saat_durumlari(tenant_id, plant: dict, bas: datetime, bit: datetime, kaynak: str = "scada") -> tuple[pd.DataFrame, dict]:
    """DB: [bas, bit) için saat tablosu ve döküm. Yalnız okur."""
    from sqlalchemy import text
    from pvquant.db import tenant_baglami
    from pvquant.services import olay_service
    izgara = saat_izgarasi(bas, bit)
    a, b = izgara[0].to_pydatetime() if len(izgara) else bas, (izgara[-1] + pd.Timedelta(hours=1)).to_pydatetime() if len(izgara) else bit
    with tenant_baglami(tenant_id) as s:
        if kaynak == "sayac":
            from pvquant.services import sayac_service
            olcum = sayac_service.sayac_oku(tenant_id, plant["id"], a, b)
        else:
            olcum = pd.read_sql(text("SELECT ts_utc, power_kw, energy_kwh, flag, kirpma, kapsama_dk FROM scada_hourly "
                                     "WHERE plant_id = CAST(:p AS uuid) AND ts_utc >= :a AND ts_utc < :b ORDER BY ts_utc"),
                                s.connection(), params={"p": plant["id"], "a": a, "b": b}, parse_dates=["ts_utc"], index_col="ts_utc")
    olaylar = olay_service.aralik(tenant_id, plant["id"], a, b, olay_turleri())
    df = siniflandir(izgara, olcum, olay_saatleri(olaylar, a, b), kaynak)
    return df, dokum(df, kaynak)
