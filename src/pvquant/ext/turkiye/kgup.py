"""KGÜP bildirim dosyası — saatlik program, teslim kuralları, 15 dk bayrağı, EAK, gün içi revizyon, teklif kantili.

DUY md. 68–69 (RG 29/12/2025): D+1 KGÜP her gün 14:00–15:30 (İstanbul) TEİAŞ TPYS'ye; TEİAŞ 17:00'a kadar teyit.
Saatlik MWh (24 satır; Türkiye'de yaz saati yok). Ardışık iki saat farkı ≥ 200 MWh ise ikinci saat 15 dk'lık
dilimlerle (md. 69(3)). Gün içi güncelleme: GİP kapı kapanışı (teslimattan 1 s önce) + 30 dk'ya kadar (md. 69(1)).
Emre amade kapasite (EAK) de 15:30'a kadar (md. 69/A). TPYS CSV şablonu resmi olarak TEYİT EDİLEMEDİ → kolonlar
parametrik (`Sablon`); kullanıcı TPYS'den indirdiği şablonla eşler.
Teklif: KGÜP olarak P50 yerine 'optimal kantil' (dengesizlik.optimal_teklif_kantili) seçilebilir.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

IST = "Europe/Istanbul"
TESLIM_BAS, TESLIM_SON, TEYIT = (14, 0), (15, 30), (17, 0)
SICRAMA_ESIK_MWH = 200.0


@dataclass
class Sablon:
    """TPYS CSV kolon adları — TEİAŞ şablonuyla eşlenir (teyit edilemedi; varsayılanlar açıklayıcı)."""
    tarih: str = "Tarih"; saat: str = "Saat"; uevcb: str = "UEVCB"; kgup: str = "KGUP_MWh"; eak: str = "EAK_MWh"
    ceyrek: str = "Ceyrek"       # 15 dk satırları için 0/15/30/45
    ayrac: str = ";"; ondalik: str = ","; tarih_bicim: str = "%d.%m.%Y"


@dataclass
class KgupSonucu:
    tablo: pd.DataFrame
    sicrama_saatleri: list[int]
    uyarilar: list[str] = field(default_factory=list)


def piyasa_gunu(gun: str | pd.Timestamp) -> pd.DatetimeIndex:
    g = pd.Timestamp(gun).tz_localize(IST) if pd.Timestamp(gun).tz is None else pd.Timestamp(gun).tz_convert(IST)
    return pd.date_range(g.normalize(), periods=24, freq="h", tz=IST)


def program_uret(tahmin_mw: pd.Series, gun: str, uevcb: str, kurulu_guc_mw: float, eak_mw: pd.Series | float | None = None,
                 bakim_saatleri: list[int] | None = None, kantil: pd.Series | None = None) -> KgupSonucu:
    """tahmin_mw: saatlik ortalama güç (UTC ya da IST index) → 24 saatlik KGÜP (MWh = MW × 1 s). kantil verilirse onu kullanır."""
    idx = piyasa_gunu(gun)
    kaynak = (kantil if kantil is not None else tahmin_mw).copy()
    kaynak.index = kaynak.index.tz_convert(IST) if kaynak.index.tz is not None else kaynak.index.tz_localize("UTC").tz_convert(IST)
    k = kaynak.reindex(idx)
    uyar = []
    if k.isna().any():
        uyar.append(f"{int(k.isna().sum())} saat tahmin yok → 0 yazıldı"); k = k.fillna(0.0)
    k = k.clip(lower=0.0, upper=kurulu_guc_mw)
    if eak_mw is None:
        eak = pd.Series(kurulu_guc_mw, index=idx)
    elif isinstance(eak_mw, (int, float)):
        eak = pd.Series(float(eak_mw), index=idx)
    else:
        e = eak_mw.copy(); e.index = e.index.tz_convert(IST) if e.index.tz is not None else e.index.tz_localize("UTC").tz_convert(IST)
        eak = e.reindex(idx).fillna(kurulu_guc_mw)
    if bakim_saatleri:
        eak.iloc[bakim_saatleri] = 0.0; k.iloc[bakim_saatleri] = 0.0; uyar.append(f"bakım saatleri {bakim_saatleri}: KGÜP ve EAK 0")
    k = pd.concat([k, eak], axis=1).min(axis=1)   # KGÜP ≤ EAK
    fark = k.diff().abs().fillna(0.0)
    sicrama = [int(h) for h in np.where(fark.values >= SICRAMA_ESIK_MWH)[0]]
    tablo = pd.DataFrame({"tarih": idx.date, "saat": idx.hour, "uevcb": uevcb, "kgup_mwh": np.round(k.values, 3), "eak_mwh": np.round(eak.values, 3)})
    return KgupSonucu(tablo, sicrama, uyar)


def ceyrek_dilimle(sonuc: KgupSonucu, tahmin_15dk_mw: pd.Series | None = None) -> pd.DataFrame:
    """≥200 MWh sıçrama saatlerini 15 dk'lık dört satıra açar (md. 69(3)); 15 dk tahmin yoksa doğrusal geçiş."""
    t = sonuc.tablo.copy(); satirlar = []
    for i, r in t.iterrows():
        if r["saat"] in sonuc.sicrama_saatleri:
            onceki = t.iloc[i - 1]["kgup_mwh"] if i > 0 else r["kgup_mwh"]
            for q in range(4):
                if tahmin_15dk_mw is not None:
                    ts = pd.Timestamp(f"{r['tarih']} {int(r['saat']):02d}:{q*15:02d}", tz=IST)
                    v = float(tahmin_15dk_mw.reindex([ts.tz_convert(tahmin_15dk_mw.index.tz or 'UTC')]).iloc[0]) / 4.0
                else:
                    v = (onceki + (r["kgup_mwh"] - onceki) * (q + 1) / 4.0) / 4.0
                satirlar.append({**r, "ceyrek": q * 15, "kgup_mwh": round(v, 3), "eak_mwh": round(r["eak_mwh"] / 4.0, 3)})
        else:
            satirlar.append({**r, "ceyrek": None})
    return pd.DataFrame(satirlar)


def tpys_csv(tablo: pd.DataFrame, yol: str | Path, sablon: Sablon = Sablon()) -> Path:
    df = pd.DataFrame({sablon.tarih: pd.to_datetime(tablo["tarih"]).dt.strftime(sablon.tarih_bicim), sablon.saat: tablo["saat"].astype(int),
                       sablon.uevcb: tablo["uevcb"], sablon.kgup: tablo["kgup_mwh"], sablon.eak: tablo["eak_mwh"]})
    if "ceyrek" in tablo and tablo["ceyrek"].notna().any():
        df[sablon.ceyrek] = tablo["ceyrek"].astype("Int64")
    yol = Path(yol); yol.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(yol, sep=sablon.ayrac, decimal=sablon.ondalik, index=False, encoding="utf-8-sig")
    return yol


def teslim_durumu(simdi: pd.Timestamp | None = None) -> dict:
    """15:30 kuralı: pencere açık mı, kaç dakika kaldı, hangi gün için."""
    t = (simdi or pd.Timestamp.now(tz=IST)); t = t.tz_convert(IST) if t.tz is not None else t.tz_localize(IST)
    bas = t.normalize() + pd.Timedelta(hours=TESLIM_BAS[0], minutes=TESLIM_BAS[1])
    son = t.normalize() + pd.Timedelta(hours=TESLIM_SON[0], minutes=TESLIM_SON[1])
    teyit = t.normalize() + pd.Timedelta(hours=TEYIT[0])
    hedef = (t.normalize() + pd.Timedelta(days=1)).date()
    if t < bas:
        return {"hedef_gun": str(hedef), "durum": "erken", "dakika_kaldi": int((son - t) / pd.Timedelta(minutes=1)), "teyit_saati": str(teyit.time())}
    if bas <= t <= son:
        return {"hedef_gun": str(hedef), "durum": "pencere_acik", "dakika_kaldi": int((son - t) / pd.Timedelta(minutes=1)), "teyit_saati": str(teyit.time())}
    return {"hedef_gun": str(hedef), "durum": "gecikti", "dakika_kaldi": 0, "teyit_saati": str(teyit.time())}


def gun_ici_revizyon_penceresi(teslimat_saati: pd.Timestamp) -> dict:
    """GİP kapı kapanışı = teslimat − 1 s; KGÜP revizyonu kapanış + 30 dk'ya kadar (md. 69(1))."""
    t = teslimat_saati.tz_convert(IST) if teslimat_saati.tz is not None else teslimat_saati.tz_localize(IST)
    kapanis = t - pd.Timedelta(hours=1)
    return {"teslimat": t, "gip_kapi_kapanis": kapanis, "kgup_revizyon_son": kapanis + pd.Timedelta(minutes=30)}


def dogrula(sonuc: KgupSonucu, kurulu_guc_mw: float) -> list[str]:
    t = sonuc.tablo; h = []
    if len(t) != 24: h.append(f"satır sayısı {len(t)} ≠ 24")
    if (t["kgup_mwh"] < 0).any(): h.append("negatif KGÜP")
    if (t["kgup_mwh"] > kurulu_guc_mw + 1e-9).any(): h.append("KGÜP > kurulu güç")
    if (t["kgup_mwh"] > t["eak_mwh"] + 1e-9).any(): h.append("KGÜP > EAK")
    if t["saat"].tolist() != list(range(24)): h.append("saat sırası bozuk")
    return h
