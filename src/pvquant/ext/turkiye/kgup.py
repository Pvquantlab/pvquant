"""KGÜP bildirim dosyası — saatlik program, teslim kuralları, 15 dk bayrağı, EAK, gün içi revizyon, teklif kantili.

DUY m.68–69, m.69/A (son değişiklik RG 19.10.2026-33405; 29.10.2026'da konsolide metinden okundu): KGÜP ve EAK her gün
15:30'a kadar Sistem İşletmecisine (TPYS); PYS erişimi olmayanlar 14:30'a kadar BYTM'ye; TEİAŞ 17:00'a kadar teyit (m.69(4)).
Saatlik MWh (24 satır; Türkiye'de yaz saati yok). 15 dk dilimleme YALNIZ dengeleme güç piyasası kapsamındaki DENGELEME BİRİMİ
için, ardışık iki saat farkı ≥ 200 MWh ise (m.69(3)); GES dengeleme birimi olmaktan muaf (m.22(4)) → varsayılan dilimleme yok,
`dengeleme_birimi` bayrağıyla açılır. Gün içi güncelleme: GİP kapı kapanışı + 30 dk'ya kadar (m.69(1)).
EAK = güç (MW), saat başına bir değer (m.4(1), m.69/A(1)); çeyrek satırlarda BÖLÜNMEZ. KGÜP (MWh) ≤ EAK (MW×1 s) ≤ kurulu güç.
Eksik tahmin saati 0 yazılmaz: dosya üretilmez, eksik saatler bildirilir (KGÜP 0 olan saatte üretimin tamamı sapma sayılır).
TPYS CSV şablonu resmî olarak TEYİT EDİLEMEDİ (TPYS girişi gerekir) → kolonlar parametrik (`Sablon`; params_json.kgup_sablon
ile eşlenir); ekranda «resmî şablonla karşılaştırılmadı» notu kalır. Dosya üretimi = bildirim DEĞİLDİR; gönderim müşterinin TPYS'sinden.
Teklif: KGÜP olarak P50 yerine kantil (P10/P25/P50/P75/P90) seçilebilir; öneri dengesizlik.optimal_teklif_kantili.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

IST = "Europe/Istanbul"
TESLIM_BAS, TESLIM_SON, TEYIT = (14, 0), (15, 30), (17, 0)
SICRAMA_ESIK_MWH = 200.0


SABLON_DURUMU = "resmî TPYS şablonuyla henüz karşılaştırılmadı; EPYS'den indirdiğiniz bir dosyayı yükleyerek biçimi eşleyebilirsiniz"   # 29.10 dil: «pilotta» iç terim
TAKVIM = {"pencere_acilis": "14:00", "bytm_son": "14:30", "son": "15:30", "teyit": "17:00"}   # m.69(1), (4); EPİAŞ KGÜP sayfası


@dataclass
class Sablon:
    """TPYS CSV kolon adları — TEİAŞ şablonuyla eşlenir (teyit edilemedi; varsayılanlar açıklayıcı). EAK birimi MW."""
    tarih: str = "Tarih"; saat: str = "Saat"; uevcb: str = "UEVCB"; kgup: str = "KGUP_MWh"; eak: str = "EAK_MW"
    ceyrek: str = "Ceyrek"       # 15 dk satırları için 0/15/30/45
    ayrac: str = ";"; ondalik: str = ","; tarih_bicim: str = "%d.%m.%Y"
    sira: str = "tarih,saat,uevcb,kgup,eak"   # 29.10 (v2.506): kolon sırası — müşteri şablonundan öğrenilir; listede olmayan rol yazılmaz

    def roller(self) -> list[str]:
        r = [x.strip() for x in (self.sira or "").split(",") if x.strip() in ROLLER]
        return r if "kgup" in r else ["tarih", "saat", "uevcb", "kgup", "eak"]

    @classmethod
    def params_json_dan(cls, pj: dict | None) -> "Sablon":
        """params_json.kgup_sablon: {"kgup": "KGUP", "eak": "EAK", "ayrac": ";", ...} — yalnız bilinen alanlar."""
        e = (pj or {}).get("kgup_sablon") or {}
        alanlar = {f for f in cls.__dataclass_fields__}
        return cls(**{k: str(v) for k, v in e.items() if k in alanlar and v})


@dataclass
class KgupSonucu:
    tablo: pd.DataFrame
    sicrama_saatleri: list[int]
    uyarilar: list[str] = field(default_factory=list)
    eksik_saatler: list[int] = field(default_factory=list)   # tahmini olmayan saatler (dosya üretilmez)


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
    eksik = [int(h) for h in np.where(k.isna().values)[0]]
    if eksik:
        uyar.append(f"{len(eksik)} saat tahmin yok (saat {', '.join(map(str, eksik))}) → dosya üretilmez; 0 yazılmaz"); k = k.fillna(0.0)
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
    tablo = pd.DataFrame({"tarih": idx.date, "saat": idx.hour, "uevcb": uevcb, "kgup_mwh": np.round(k.values, 3), "eak_mw": np.round(eak.values, 3)})
    return KgupSonucu(tablo, sicrama, uyar, eksik)


def ceyrek_dilimle(sonuc: KgupSonucu, tahmin_15dk_mw: pd.Series | None = None) -> pd.DataFrame:
    """≥200 MWh sıçrama saatlerini 15 dk'lık dört satıra açar (m.69(3)) — YALNIZ dengeleme birimi için çağrılır.
    KGÜP çeyrek değeri MWh/4; EAK güçtür, çeyrek satırda saatlik EAK aynen yazılır (bölünmez). 15 dk tahmin yoksa doğrusal geçiş."""
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
                satirlar.append({**r, "ceyrek": q * 15, "kgup_mwh": round(v, 3), "eak_mw": round(r["eak_mw"], 3)})
        else:
            satirlar.append({**r, "ceyrek": None})
    return pd.DataFrame(satirlar)


def tpys_csv(tablo: pd.DataFrame, yol: str | Path, sablon: Sablon = Sablon()) -> Path:
    yol = Path(yol); yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_bytes(csv_baytlari(tablo, sablon))
    return yol


def csv_metni(tablo: pd.DataFrame, sablon: Sablon = Sablon()) -> str:
    """TPYS CSV gövdesi (BOM'suz metin; BOM yalnız csv_baytlari'nda — tek yerde). 29.10 (v2.506): kolon sırası ve kümesi şablonun
    `sira`sından (müşteri dosyasından öğrenilmiş olabilir); varsayılan beş kolon aynı sırayla — eski çıktı bayt bayt aynı."""
    deger = {"tarih": pd.to_datetime(tablo["tarih"]).dt.strftime(sablon.tarih_bicim), "saat": tablo["saat"].astype(int),
             "uevcb": tablo["uevcb"], "kgup": tablo["kgup_mwh"], "eak": tablo["eak_mw"]}
    df = pd.DataFrame({getattr(sablon, rol): deger[rol] for rol in sablon.roller()})
    if "ceyrek" in tablo and tablo["ceyrek"].notna().any():
        df[sablon.ceyrek] = tablo["ceyrek"].astype("Int64")
    return df.to_csv(sep=sablon.ayrac, decimal=sablon.ondalik, index=False, float_format="%.3f")


ROLLER = ("tarih", "saat", "uevcb", "kgup", "eak")
# başlık ipuçları (küçük harf, Türkçe karakterler sadeleştirilmiş): rol → aranan parçalar; ilk eşleşen başlık alınır
_IPUCU = {"tarih": ("tarih", "date", "gun"), "saat": ("saat", "hour", "donem", "period", "zaman"),
          "uevcb": ("uevcb", "birim", "unit", "santral"), "kgup": ("kgup", "program", "plan", "mwh", "miktar", "uretim"),
          "eak": ("eak", "emre", "kapasite", "capacity", "mw"), "ceyrek": ("ceyrek", "dakika", "minute")}


def _sade(s: str) -> str:
    return str(s).strip().lower().translate(str.maketrans("çğıöşüâî", "cgiosuai"))


def sablon_ogren(b: bytes, dosya_adi: str = "") -> dict:
    """29.10 (v2.506) — müşterinin EPYS/TPYS'den indirdiği KGÜP dosyasından (CSV ya da Excel) biçimi öğrenir: kolon adları ve sırası,
    ayraç, ondalık, tarih biçimi. Resmî şablon elimizde olmadan dışa aktarma müşterinin dosyasıyla birebir aynı biçime gelir.
    Zorunlu roller: saat ve kgup; bulunamazsa ValueError (başlıklar hata metninde). Dönüş: {sablon, eslesme, eslesmeyen, bicim, uyarilar}."""
    uyar: list[str] = []
    if b[:2] == b"PK":   # xlsx (zip)
        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(b), read_only=True, data_only=True); ws = wb.worksheets[0]
        satirlar = [[("" if c is None else str(c)) for c in r] for r in ws.iter_rows(values_only=True, max_row=30)]
        satirlar = [r for r in satirlar if any(x.strip() for x in r)]
        if not satirlar:
            raise ValueError("Excel sayfası boş")
        baslik = [x.strip() for x in satirlar[0]]; ornek = satirlar[1] if len(satirlar) > 1 else []
        ayrac, ondalik, bicim = ";", ",", "xlsx"
        uyar.append("Excel dosyası: dışa aktarma CSV'dir (aynı kolon adları ve sırası; ayraç «;», ondalık «,»)")
    else:
        metin = b.decode("utf-8-sig", errors="replace"); hatlar = [h for h in metin.splitlines() if h.strip()]
        if not hatlar:
            raise ValueError("dosya boş")
        ilk = hatlar[0]; ayrac = max((";", ",", "\t", "|"), key=lambda a: ilk.count(a))
        if ilk.count(ayrac) == 0:
            raise ValueError("ayraç bulunamadı (; , sekme ya da | bekleniyor)")
        baslik = [x.strip().strip('"') for x in ilk.split(ayrac)]
        ornek = [x.strip().strip('"') for x in hatlar[1].split(ayrac)] if len(hatlar) > 1 else []
        sayisal = " ".join(x for x in ornek if any(ch.isdigit() for ch in x))
        ondalik = "," if ("," in sayisal and ayrac != ",") else "."
        bicim = "csv"
    eslesme: dict[str, str] = {}; kullanilan: set[str] = set()
    for rol, ipuclari in _IPUCU.items():
        for h in baslik:
            if h in kullanilan or not h:
                continue
            sade = _sade(h)
            if rol == "eak" and "kgup" in sade:
                continue
            if any(ip in sade for ip in ipuclari):
                eslesme[rol] = h; kullanilan.add(h); break
    eksik = [r for r in ("saat", "kgup") if r not in eslesme]
    if eksik:
        raise ValueError(f"şablonda zorunlu kolon bulunamadı: {', '.join(eksik)}; başlıklar: {', '.join(baslik)}")
    eslesmeyen = [h for h in baslik if h and h not in kullanilan]
    if eslesmeyen:
        uyar.append(f"eşlenmeyen kolon(lar) yazılmaz: {', '.join(eslesmeyen)}")
    tarih_bicim = "%d.%m.%Y"
    if "tarih" in eslesme and ornek:
        i = baslik.index(eslesme["tarih"]); v = ornek[i] if i < len(ornek) else ""
        if len(v) >= 10 and v[4] == "-": tarih_bicim = "%Y-%m-%d"
        elif len(v) >= 10 and v[2] == "/": tarih_bicim = "%d/%m/%Y"
    sira = [rol for rol in baslik_rolleri(baslik, eslesme)]
    sab = {rol: eslesme[rol] for rol in eslesme if rol in Sablon.__dataclass_fields__}
    sab.update({"ayrac": ayrac, "ondalik": ondalik, "tarih_bicim": tarih_bicim, "sira": ",".join(sira)})
    return {"sablon": sab, "eslesme": eslesme, "eslesmeyen": eslesmeyen, "bicim": bicim, "uyarilar": uyar, "dosya_adi": dosya_adi}


def baslik_rolleri(baslik: list[str], eslesme: dict[str, str]) -> list[str]:
    """Başlık sırasına göre rol listesi (yalnız eşleşen roller; ceyrek hariç — o ayrı sütun olarak eklenir)."""
    ters = {h: rol for rol, h in eslesme.items() if rol in ROLLER}
    return [ters[h] for h in baslik if h in ters]


def csv_baytlari(tablo: pd.DataFrame, sablon: Sablon = Sablon()) -> bytes:
    """Dosyanın baytları: UTF-8 BOM + gövde (her üretim yolunda aynı; SHA-256 bu baytlar üzerinden)."""
    return csv_metni(tablo, sablon).encode("utf-8-sig")


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
    if (t["kgup_mwh"] > t["eak_mw"] + 1e-9).any(): h.append("KGÜP > EAK")
    if t["saat"].tolist() != list(range(24)): h.append("saat sırası bozuk")
    return h
