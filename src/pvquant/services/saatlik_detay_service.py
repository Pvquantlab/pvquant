"""v2.527 (P2b-2) — EPYS saatlik uzlaştırma detayı: içe alma ve PVQuant dökümüyle saat saat, eş kapsamlı kıyas.

Kaynak ekranlar (EPYS Uzlaştırma Modülü Kullanıcı Kılavuzu s.22, 28–33; 2024 ön yüz paketi; 02-24): «Uzlaştırma Dönemi Detay Listeleme» (saatlik; PTF, SMF,
KUDÜP, BUDÜP, YALM, YATM, UEVM, UEÇM, pozitif/negatif EDM ve EDT, KÜPSM, KÜPST), «Dengesizlik Uzlaştırma» (UEVM, UEÇM, EDM, EDT), «KÜPST Detay» (PTF, SMF,
KUDÜP, YALM, YATM, BUDÜP). Resmî dosya başlıkları GÖRÜLMEDİ — kılavuzdaki ekran kolon adlarından türetildi; gerçek dosyayla sınanmalı. Dosya tanıma
esnektir: başlık satırında tarih (+ saat) sütunu ve en az iki bilinen ölçüm sütunu aranır.

Dürüstlük: EPİAŞ saatlik tutarı esastır; PVQuant dökümü yeniden hesaptır. Kıyas yalnız iki tarafta da bulunan saatlerde (ortak saatler) yapılır — eş kapsamlı
karşılaştırma budur; aylık bildirim toplamıyla değil. Fark ayrıştırması saat bazında girdilere bakar: fiyat (PTF/SMF), üretim (UEVM ↔ PVQuant gerçekleşen),
program (BUDÜP ↔ PVQuant programı); girdiler eşitken EDT farklıysa «kural/hesap farkı»."""
from __future__ import annotations

from pvquant.zaman import PIYASA_TZ

import hashlib
import io
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import text

from pvquant.db import tenant_baglami
# v2.535 dayanak künyeleri [DUY, KARAR_14907] — bu dosyadaki madde atıflarının birincil yayımı (RG tarih-sayı, karar no); metin kunye.py sicilinden üretildi,
# tests/test_kunye_bekcisi.py sicille eş tutar (kaynak: 03.11.2026 doğrulama arşivi 03_Kaynak_Envanteri).
DAYANAK_KUNYELERI = (
    'DUY: Elektrik Piyasası Dengeleme ve Uzlaştırma Yönetmeliği, RG 14.04.2009-27200; değişiklikler RG 28.03.2015-29309, 30.10.2016-29873, 18.01.2018-30305, 09.08.2019-30857, 02.02.2020-31027, 19.11.2022-32018, 19.12.2023-32404, 17.12.2024-32755, 21.01.2025-32789, 29.12.2025-33122, 19.10.2026-33405, 21.10.2026-33407; '
    'Karar 14907: EPDK Kurul Kararı 14907 (KÜPST, 1.11.2026 çıkarım), RG 19.10.2026-33405'
)

IST = ZoneInfo(PIYASA_TZ)
EN_BUYUK = 5_000_000   # bayt

# sade başlık → alan; sıra önemli (ilk eşleşen kazanır); «pozitif edt» «edt»den önce
KOLONLAR: list[tuple[tuple[str, ...], str]] = [
    (("pozitif edt", "edt pozitif", "pozitif dengesizlik tutar", "poz edt"), "edt_poz_tl"),
    (("negatif edt", "edt negatif", "negatif dengesizlik tutar", "neg edt"), "edt_neg_tl"),
    (("pozitif edm", "edm pozitif", "pozitif dengesizlik miktar", "poz edm"), "edm_poz_mwh"),
    (("negatif edm", "edm negatif", "negatif dengesizlik miktar", "neg edm"), "edm_neg_mwh"),
    (("kupsm",), "kupsm_mwh"), (("kupst",), "kupst_tl"),
    (("kudup",), "kudup_mwh"), (("budup",), "budup_mwh"), (("yalm",), "yalm_mwh"), (("yatm",), "yatm_mwh"),
    (("uevm",), "uevm_mwh"), (("uecm",), "uecm_mwh"),
    (("ptf", "piyasa takas"), "ptf"), (("smf", "sistem marjinal"), "smf"),
    (("versiyon", "version", "surum"), "versiyon"),
]
ALANLAR = [a for _, a in KOLONLAR if a != "versiyon"]
ALAN_ETIKET = {"ptf": "PTF (TL/MWh)", "smf": "SMF (TL/MWh)", "uevm_mwh": "UEVM (MWh)", "uecm_mwh": "UEÇM (MWh)", "kudup_mwh": "KUDÜP (MWh)", "budup_mwh": "BUDÜP (MWh)",
               "yalm_mwh": "YALM (MWh)", "yatm_mwh": "YATM (MWh)", "edm_poz_mwh": "Pozitif EDM (MWh)", "edm_neg_mwh": "Negatif EDM (MWh)",
               "edt_poz_tl": "Pozitif EDT (TL)", "edt_neg_tl": "Negatif EDT (TL)", "kupsm_mwh": "KÜPSM (MWh)", "kupst_tl": "KÜPST (TL)"}
# kıyas toleransları (PVQuant işletme ölçütü; mevzuat değil)
TOL_FIYAT_TL_MWH = 0.01
TOL_MWH = 0.0005          # 0,5 kWh — döküm 3 ondalık MWh
TOL_TL = 0.5
TOL_YUVARLAMA_TL = 5.0    # girdiler tolerans içinde ama sıfır değilken küçük tutar farkı: yuvarlama/ondalık
NEDEN_ACIKLAMA = {"fiyat": "PTF ya da SMF farklı (fiyat kaynağı / sürümü)", "uretim": "UEVM ile PVQuant gerçekleşeni (SCADA ya da yüklü sayaç) farklı",
                  "program": "BUDÜP ile PVQuant programı (bildirilen KGÜP ya da öneri) farklı",
                  "pozisyon": "üretim ve program eşit ama EPİAŞ'ın dengesizlik miktarı (EDM) PVQuant sapmasından farklı — ikili anlaşma / piyasa pozisyonu (olası neden: DSG grup payı — dosya içeriği bilinmeden kesinleştirilemez)",
                  "yuvarlama": "girdiler tolerans içinde (ondalık farkı) ve tutar farkı küçük — yuvarlama",
                  "kural": "fiyat, üretim, program ve miktar eşitken tutar farklı — sistem yönü (k/l katsayıları), kural sürümü ya da hesap"}
NOT = ("Saatlik detay kıyası EPYS'den indirilen saatlik detay dosyasıyla PVQuant dökümünü yalnız iki tarafta da bulunan saatlerde karşılaştırır (eş kapsamlı); "
       "aylık bildirim toplamıyla karşılaştırma değildir. EPİAŞ tutarı esastır. Fark ayrıştırması saat bazında girdilere bakar: fiyat (PTF/SMF), üretim (UEVM ↔ "
       "PVQuant gerçekleşen — SCADA ya da yüklü sayaç), program (BUDÜP ↔ PVQuant programı); girdiler eşitken dengesizlik tutarı farklıysa kural/hesap farkıdır. "
       "Resmî dosya başlıkları görülmediğinden tanıma kılavuzdaki ekran adlarına dayanır; tanınmayan sütunlar yoksayılır.")


def _sade(s) -> str:
    from pvquant.services.mutabakat_service import _sade as f
    return f(s)


def _satirlar(b: bytes) -> tuple[list[list], str]:
    """CSV ya da XLSX → hücre matrisi; saatlik dosya 744+ satır olduğundan sınır 20.000 satır (mutabakat_service._satirlar 400 ile sınırlı)."""
    if b[:2] == b"PK":
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(b), read_only=True, data_only=True)
        out: list[list] = []
        for ws in wb.worksheets:
            for r in ws.iter_rows(values_only=True, max_row=20000):
                out.append([("" if c is None else c) for c in r])
            if out:
                break   # ilk dolu sayfa
        return out, "xlsx"
    metin = b.decode("utf-8-sig", errors="replace")
    hatlar = [h for h in metin.splitlines() if h.strip()]
    if not hatlar:
        return [], "csv"
    ornek = "\n".join(hatlar[:20])
    ayrac = max((";", ",", "\t", "|"), key=lambda a: ornek.count(a))
    import csv as _csv
    return [list(r) for r in _csv.reader(hatlar[:20000], delimiter=ayrac)], "csv"


def _sayi(v):
    from pvquant.services.mutabakat_service import _sayi as f
    return f(v)


_TARIH_RE = re.compile(r"(\d{1,2})[./-](\d{1,2})[./-](20\d{2})|(20\d{2})-(\d{1,2})-(\d{1,2})")
_SAAT_RE = re.compile(r"(\d{1,2})[:.](\d{2})")


def _zaman(tarih, saat=None) -> datetime | None:
    """Tarih hücresi (dd.mm.yyyy[ HH:MM] | yyyy-mm-dd[ HH:MM[:SS]] | datetime) + isteğe bağlı saat hücresi (HH:MM | «HH:00-HH:00» | 0–23) → UTC saat başı."""
    if isinstance(tarih, datetime):
        dt = tarih if tarih.tzinfo else tarih.replace(tzinfo=IST)
    else:
        s = str(tarih or "").strip()
        m = _TARIH_RE.search(s)
        if not m:
            return None
        if m.group(1):
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            y, mo, d = int(m.group(4)), int(m.group(5)), int(m.group(6))
        hh = 0
        ms = _SAAT_RE.search(s[m.end():])
        if ms:
            hh = int(ms.group(1))
        try:
            dt = datetime(y, mo, d, hh, tzinfo=IST)
        except ValueError:
            return None
    if saat not in (None, ""):
        if isinstance(saat, (int, float)) and not isinstance(saat, bool):
            hh = int(saat)
        else:
            ms = _SAAT_RE.search(str(saat))
            hh = int(ms.group(1)) if ms else (int(str(saat).strip()) if str(saat).strip().isdigit() else None)
        if hh is None or not (0 <= hh <= 23):
            return None
        dt = dt.replace(hour=hh)
    return dt.replace(minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def _basliklar(satir: list) -> dict | None:
    """Başlık satırı: tarih sütunu + en az iki bilinen alan. Dönüş {alan: sütun indeksi} + 'tarih' (+ 'saat')."""
    sade = [_sade(c) for c in satir]
    idx: dict = {}
    for i, s in enumerate(sade):
        if not s:
            continue
        if "tarih" not in idx and ("tarih" in s or s in ("date", "datetime", "zaman", "tarih saat")):
            idx["tarih"] = i; continue
        if "saat" not in idx and (s in ("saat", "hour", "saat dilimi") or s.startswith("saat ")) and "tarih" not in s:
            idx["saat"] = i; continue
        for anahtarlar, alan in KOLONLAR:
            if alan in idx:
                continue
            if any(s == a or s.startswith(a + " ") or s.startswith(a + "(") or (a in s and alan not in ("ptf", "smf")) for a in anahtarlar):
                idx[alan] = i; break
    return idx if ("tarih" in idx and sum(1 for k in idx if k in ALANLAR) >= 2) else None


def dosya_oku(b: bytes, dosya_adi: str = "") -> dict:
    """Saatlik detay dosyasını okur. Dönüş: {satirlar: [{ts_utc, alanlar…}], donem, kolonlar, kaynak_ekran, bicim, uyarilar, atlanan}."""
    satirlar, bicim = _satirlar(b)
    if not satirlar:
        raise ValueError("dosya boş")
    idx = None; bas_i = 0
    for i, r in enumerate(satirlar[:60]):
        idx = _basliklar(r)
        if idx:
            bas_i = i; break
    if not idx:
        raise ValueError("saatlik detay başlığı bulunamadı: tarih sütunu ve en az iki ölçüm sütunu (PTF, SMF, UEVM, KUDÜP, BUDÜP, EDM, EDT, KÜPSM, KÜPST) gerekir")
    kolonlar = [a for a in ALANLAR if a in idx]
    out: dict[datetime, dict] = {}; atlanan = 0; uyar: list[str] = []
    for r in satirlar[bas_i + 1:]:
        if not any(str(c).strip() for c in r):
            continue
        tarih = r[idx["tarih"]] if idx["tarih"] < len(r) else None
        saat = r[idx["saat"]] if "saat" in idx and idx["saat"] < len(r) else None
        ts = _zaman(tarih, saat)
        if ts is None:
            atlanan += 1; continue
        kayit = {"ts_utc": ts, "versiyon": (str(r[idx["versiyon"]]).strip()[:40] if "versiyon" in idx and idx["versiyon"] < len(r) and str(r[idx["versiyon"]]).strip() else None)}
        for a in kolonlar:
            kayit[a] = _sayi(r[idx[a]]) if idx[a] < len(r) else None
        if ts in out:
            atlanan += 1   # aynı saat yinelenmiş: son satır kazanır
        out[ts] = kayit
    if not out:
        raise ValueError("tarih/saat okunabilen satır yok")
    kayitlar = [out[k] for k in sorted(out)]
    ilk, son = kayitlar[0]["ts_utc"].astimezone(IST), kayitlar[-1]["ts_utc"].astimezone(IST)
    donem = date(ilk.year, ilk.month, 1)
    if (son - timedelta(hours=1)).strftime("%Y-%m") != ilk.strftime("%Y-%m") and son.strftime("%Y-%m") != ilk.strftime("%Y-%m"):
        uyar.append(f"satırlar birden çok aya yayılıyor ({ilk:%m.%Y} – {son:%m.%Y}); dönem ilk satırdan alındı, öbür aylar da saklandı")
    if atlanan:
        uyar.append(f"{atlanan} satır tarih/saat okunamadığından ya da yinelendiğinden atlandı")
    edt = any(a in kolonlar for a in ("edt_poz_tl", "edt_neg_tl", "edm_poz_mwh", "edm_neg_mwh", "uevm_mwh"))
    kup = any(a in kolonlar for a in ("kupsm_mwh", "kupst_tl", "kudup_mwh", "budup_mwh"))
    kaynak = "detay" if (edt and kup) else ("dengesizlik" if edt else "kupst")
    if not any(a in kolonlar for a in ("edt_poz_tl", "edt_neg_tl", "kupst_tl")):
        uyar.append("dosyada tutar sütunu (EDT ya da KÜPST) yok; yalnız miktar/fiyat kıyası yapılabilir")
    return {"satirlar": kayitlar, "donem": donem, "kolonlar": kolonlar, "kaynak_ekran": kaynak, "bicim": bicim, "uyarilar": uyar, "atlanan": atlanan}


def kaydet(tenant_id, plant: dict, b: bytes, dosya_adi: str, donem=None, yukleyen=None) -> dict:
    """Dosyayı okur, satırları yeni yukleme_id ile saklar (önceki yüklemeler silinmez). donem (YYYY-MM) verilirse dosyayla uyuşmalı."""
    if not b or len(b) > EN_BUYUK:
        raise ValueError("dosya boş ya da 5 MB'tan büyük")
    o = dosya_oku(b, dosya_adi)
    d = o["donem"]
    if donem:
        from pvquant.services.mutabakat_service import _donem
        dd = _donem(donem)
        if dd != d:
            raise ValueError(f"dosyadaki saatler {d.strftime('%m.%Y')} dönemine ait; seçilen dönem {dd.strftime('%m.%Y')}")
    if d > datetime.now(IST).date().replace(day=1):
        raise ValueError("dönem gelecekte olamaz")
    yid = str(uuid.uuid4()); sha = hashlib.sha256(b).hexdigest()
    try:
        yukleyen = str(uuid.UUID(str(yukleyen))) if yukleyen else None
    except ValueError:
        yukleyen = None
    alanlar = ", ".join(ALANLAR); yer = ", ".join(f":{a}" for a in ALANLAR)
    with tenant_baglami(tenant_id) as s:
        for k in o["satirlar"]:
            s.execute(text(f"INSERT INTO uzlastirma_saatlik(tenant_id, plant_id, donem, yukleme_id, ts_utc, versiyon, kaynak_ekran, {alanlar}, dosya_adi, sha256, yukleyen) "
                           f"VALUES (:t, :p, :d, :y, :ts, :v, :ke, {yer}, :da, :sha, :yu)"),
                      {"t": tenant_id, "p": plant["id"], "d": d, "y": yid, "ts": k["ts_utc"], "v": k.get("versiyon"), "ke": o["kaynak_ekran"],
                       **{a: k.get(a) for a in ALANLAR}, "da": (dosya_adi or "")[:200], "sha": sha, "yu": yukleyen})
    return {"yukleme_id": yid, "donem": d.isoformat()[:7], "saat": len(o["satirlar"]), "kolonlar": o["kolonlar"], "kolon_etiketleri": [ALAN_ETIKET[a] for a in o["kolonlar"]],
            "kaynak_ekran": o["kaynak_ekran"], "bicim": o["bicim"], "sha256": sha, "uyarilar": o["uyarilar"], "dosya_adi": dosya_adi}


def yuklemeler(tenant_id, plant_id, n: int = 20) -> list[dict]:
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text("SELECT donem, yukleme_id, kaynak_ekran, max(olusturma) AS z, max(dosya_adi) AS dosya, max(sha256) AS sha, count(*) AS n, "
                              "min(ts_utc) AS bas, max(ts_utc) AS bit FROM uzlastirma_saatlik WHERE plant_id = CAST(:p AS uuid) "
                              "GROUP BY donem, yukleme_id, kaynak_ekran ORDER BY z DESC LIMIT :n"), {"p": plant_id, "n": n}).fetchall()
    return [{"donem": r.donem.isoformat()[:7], "yukleme_id": str(r.yukleme_id), "kaynak_ekran": r.kaynak_ekran, "zaman": r.z.astimezone(IST).isoformat(timespec="minutes"),
             "dosya_adi": r.dosya, "sha256": r.sha, "saat": int(r.n), "bas": r.bas.astimezone(IST).isoformat(timespec="minutes"), "bit": r.bit.astimezone(IST).isoformat(timespec="minutes")} for r in rows]


def oku(tenant_id, plant_id, donem: date) -> tuple[pd.DataFrame, list[dict]]:
    """Dönemin saatlik detayı: her kaynak ekranın (detay / dengesizlik / kupst) EN SON yüklemesi; saat bazında dış birleşim, aynı alan için «detay» > öbürleri.
    Dönüş (df[ts_utc indeks, alanlar], kullanılan yüklemeler)."""
    with tenant_baglami(tenant_id) as s:
        son = s.execute(text("SELECT kaynak_ekran, yukleme_id, max(olusturma) AS z FROM uzlastirma_saatlik WHERE plant_id = CAST(:p AS uuid) AND donem = :d "
                             "GROUP BY kaynak_ekran, yukleme_id ORDER BY z DESC"), {"p": plant_id, "d": donem}).fetchall()
        secili: dict[str, str] = {}
        for r in son:
            secili.setdefault(r.kaynak_ekran, str(r.yukleme_id))
        if not secili:
            return pd.DataFrame(columns=ALANLAR, index=pd.DatetimeIndex([], tz="UTC", name="ts_utc")), []
        parcalar = []; kullanilan = []
        for ke in ("detay", "dengesizlik", "kupst"):
            if ke not in secili:
                continue
            df = pd.read_sql(text(f"SELECT ts_utc, versiyon, {', '.join(ALANLAR)}, dosya_adi, olusturma FROM uzlastirma_saatlik WHERE yukleme_id = CAST(:y AS uuid) ORDER BY ts_utc"),
                             s.connection(), params={"y": secili[ke]}, parse_dates=["ts_utc"])
            if df.empty:
                continue
            kullanilan.append({"kaynak_ekran": ke, "yukleme_id": secili[ke], "saat": int(len(df)), "dosya_adi": df["dosya_adi"].iloc[0],
                               "zaman": pd.Timestamp(df["olusturma"].iloc[0]).tz_convert(IST).isoformat(timespec="minutes"), "versiyon": (df["versiyon"].dropna().iloc[0] if df["versiyon"].notna().any() else None)})
            parcalar.append(df.drop(columns=["dosya_adi", "olusturma", "versiyon"]).set_index("ts_utc"))
    if not parcalar:
        return pd.DataFrame(columns=ALANLAR, index=pd.DatetimeIndex([], tz="UTC", name="ts_utc")), []
    out = parcalar[0]
    for p in parcalar[1:]:
        out = out.combine_first(p)   # «detay» önce geldiğinden önceliklidir
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    return out.sort_index(), kullanilan


def _pv_df(tenant_id, plant: dict, donem: date, bugun: date | None, uretim: str | None) -> pd.DataFrame:
    """PVQuant dökümünün dönem dilimi, UTC saat indeksi (dokum «zaman» Türkiye saatidir)."""
    from pvquant.services import dengesizlik_service
    b = bugun or datetime.now(IST).date()
    gun = max(14, min(365, (b - donem).days + 1))
    ur = uretim if uretim in dengesizlik_service.URETIM_SECENEKLERI else dengesizlik_service.uretim_secimi(plant.get("params_json"))
    df, _ = dengesizlik_service.dokum(tenant_id, plant, gun=gun, uretim="sayac") if ur == "sayac" else dengesizlik_service.dokum(tenant_id, plant, gun=gun)
    if df is None or df.empty:
        return pd.DataFrame()
    x = df[df["zaman"].str.startswith(donem.strftime("%Y-%m"))].copy()
    if x.empty:
        return x
    x["ts_utc"] = pd.to_datetime(x["zaman"]).dt.tz_localize(IST, ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")
    x = x.dropna(subset=["ts_utc"]).set_index("ts_utc")
    x.attrs["uretim"] = ur
    return x


def kiyas(tenant_id, plant: dict, donem: date, uretim: str | None = None, bugun: date | None = None, en_buyuk: int = 10) -> dict:
    """Eş kapsamlı saatlik kıyas: ortak saatlerde EPİAŞ ↔ PVQuant (fiyat, üretim, program, EDT, KÜPST), fark ayrıştırması, en büyük farklı saatler."""
    ofc, kullanilan = oku(tenant_id, plant["id"], donem)
    sonuc = {"donem": donem.isoformat()[:7], "yuklu": not ofc.empty, "yuklemeler": kullanilan, "epias_saat": int(len(ofc)), "kolonlar": [a for a in ALANLAR if a in ofc.columns and ofc[a].notna().any()],
             "not": NOT, "tolerans": {"fiyat_tl_mwh": TOL_FIYAT_TL_MWH, "mwh": TOL_MWH, "tl": TOL_TL}}
    if ofc.empty:
        sonuc.update({"pv_saat": 0, "ortak_saat": 0, "toplam": None, "ayristirma": None, "en_buyuk": [], "satirlar": []})
        return sonuc
    pv = _pv_df(tenant_id, plant, donem, bugun, uretim)
    sonuc["uretim"] = pv.attrs.get("uretim") if not pv.empty else None
    sonuc["pv_saat"] = int(len(pv))
    if pv.empty:
        sonuc.update({"ortak_saat": 0, "toplam": None, "ayristirma": None, "en_buyuk": [], "satirlar": []})
        return sonuc
    j = ofc.join(pv, how="inner", rsuffix="_pv")
    sonuc["ortak_saat"] = int(len(j)); sonuc["yalniz_epias_saat"] = int(len(ofc.index.difference(pv.index))); sonuc["yalniz_pvquant_saat"] = int(len(pv.index.difference(ofc.index)))
    if j.empty:
        sonuc.update({"toplam": None, "ayristirma": None, "en_buyuk": [], "satirlar": []})
        return sonuc
    n = lambda c: pd.to_numeric(j[c], errors="coerce") if c in j.columns else pd.Series(float("nan"), index=j.index)   # noqa: E731
    e_poz, e_neg = n("edt_poz_tl").fillna(0.0), n("edt_neg_tl").fillna(0.0)
    p_poz, p_neg = n("edt_alacak_tl").fillna(0.0), n("edt_borc_tl").fillna(0.0)
    e_net, p_net = e_poz - e_neg.abs(), p_poz - p_neg.abs()
    e_kup, p_kup = n("kupst_tl").fillna(0.0), n("kupst_tl_pv").fillna(0.0) if "kupst_tl_pv" in j.columns else n("kupst_tl").fillna(0.0) * 0
    var = lambda c: c in j.columns and pd.to_numeric(j[c], errors="coerce").notna().any()   # noqa: E731
    fiyat_f = ((n("ptf") - n("ptf_tl_mwh")).abs() > TOL_FIYAT_TL_MWH) | ((n("smf") - n("smf_tl_mwh")).abs() > TOL_FIYAT_TL_MWH) if (var("ptf") or var("smf")) else pd.Series(False, index=j.index)
    uretim_f = ((n("uevm_mwh") - n("gerceklesen_mwh")).abs() > TOL_MWH) if var("uevm_mwh") else pd.Series(False, index=j.index)
    program_f = ((n("budup_mwh") - n("program_mwh")).abs() > TOL_MWH) if var("budup_mwh") else pd.Series(False, index=j.index)
    edt_var = var("edt_poz_tl") or var("edt_neg_tl")
    edt_f = ((e_net - p_net).abs() > TOL_TL) if edt_var else pd.Series(False, index=j.index)
    fiyat_f, uretim_f, program_f = fiyat_f.fillna(False), uretim_f.fillna(False), program_f.fillna(False)
    # 03.11 inceleme: «girdiler eşit, tutar farklı» saatleri gerçek nedenine ayrılır — EDM (pozisyon/İA/DSG payı), yuvarlama, kalan = kural/yön
    edm_var = var("edm_poz_mwh") or var("edm_neg_mwh")
    edm_e = n("edm_poz_mwh").fillna(0.0) - n("edm_neg_mwh").fillna(0.0)
    sapma_p = n("sapma_mwh")
    if edm_var and var("sapma_mwh"):
        pozisyon_f = (((edm_e - sapma_p).abs() > TOL_MWH) & ~uretim_f & ~program_f).fillna(False)
    else:
        pozisyon_f = pd.Series(False, index=j.index)
    kucuk = pd.Series(False, index=j.index)
    for a_, b_ in (("ptf", "ptf_tl_mwh"), ("smf", "smf_tl_mwh"), ("uevm_mwh", "gerceklesen_mwh"), ("budup_mwh", "program_mwh")):
        if var(a_) and b_ in j.columns:
            kucuk = kucuk | ((n(a_) - n(b_)).abs() > 1e-9).fillna(False)
    temel = edt_f & ~fiyat_f & ~uretim_f & ~program_f & ~pozisyon_f
    yuvarlama_f = temel & kucuk & ((e_net - p_net).abs() <= TOL_YUVARLAMA_TL)
    kural_f = temel & ~yuvarlama_f
    toplam = {"edt_net_epias_tl": round(float(e_net.sum()), 2) if edt_var else None, "edt_net_pvquant_tl": round(float(p_net.sum()), 2),
              "edt_net_fark_tl": round(float((p_net - e_net).sum()), 2) if edt_var else None,
              "edt_poz_epias_tl": round(float(e_poz.sum()), 2) if edt_var else None, "edt_neg_epias_tl": round(float(e_neg.abs().sum()), 2) if edt_var else None,
              "edt_poz_pvquant_tl": round(float(p_poz.sum()), 2), "edt_neg_pvquant_tl": round(float(p_neg.abs().sum()), 2),
              "kupst_epias_tl": round(float(e_kup.sum()), 2) if var("kupst_tl") else None, "kupst_pvquant_tl": round(float(p_kup.sum()), 2),
              "kupst_fark_tl": round(float((p_kup - e_kup).sum()), 2) if var("kupst_tl") else None,
              "uevm_mwh": round(float(n("uevm_mwh").fillna(0).sum()), 3) if var("uevm_mwh") else None, "gerceklesen_pvquant_mwh": round(float(n("gerceklesen_mwh").fillna(0).sum()), 3),
              "fark_isareti": "artı: PVQuant daha çok alacak / daha az borç hesaplıyor (fark = PVQuant − EPİAŞ)"}
    ayr = {"fiyat_farki_saat": int(fiyat_f.sum()), "uretim_farki_saat": int(uretim_f.sum()), "program_farki_saat": int(program_f.sum()),
           "pozisyon_farki_saat": int(pozisyon_f.sum()), "yuvarlama_saat": int(yuvarlama_f.sum()),
           "kural_farki_saat": int(kural_f.sum()), "edt_farki_saat": int(edt_f.sum()) if edt_var else None, "uyumlu_saat": int((~edt_f).sum()) if edt_var else None,
           "fiyat_karsilastirildi": bool(var("ptf") or var("smf")), "uretim_karsilastirildi": bool(var("uevm_mwh")), "program_karsilastirildi": bool(var("budup_mwh")),
           "pozisyon_karsilastirildi": bool(edm_var and var("sapma_mwh")), "edt_karsilastirildi": bool(edt_var),
           "not": "Bir saatte birden çok neden olabilir. Fiyat/üretim/program farkı yoksa sırayla bakılır: EDM (pozisyon) farkı, yuvarlama, kalan kural/yön farkı."}
    z = j.index.tz_convert(IST)
    satirlar = []
    for i, ts in enumerate(j.index):
        satirlar.append({"zaman": z[i].strftime("%Y-%m-%d %H:%M"), "ptf_epias": _f(n("ptf").iloc[i]), "ptf_pvquant": _f(n("ptf_tl_mwh").iloc[i]), "smf_epias": _f(n("smf").iloc[i]), "smf_pvquant": _f(n("smf_tl_mwh").iloc[i]),
                         "uevm_mwh": _f(n("uevm_mwh").iloc[i], 3), "gerceklesen_pvquant_mwh": _f(n("gerceklesen_mwh").iloc[i], 3), "budup_mwh": _f(n("budup_mwh").iloc[i], 3), "program_pvquant_mwh": _f(n("program_mwh").iloc[i], 3),
                         "program_kaynak": (str(j["program_kaynak"].iloc[i]) if "program_kaynak" in j.columns else None),
                         "edm_epias_mwh": (_f(edm_e.iloc[i], 3) if edm_var else None), "sapma_pvquant_mwh": _f(sapma_p.iloc[i], 3),
                         "yon": (str(j["yon"].iloc[i]) if "yon" in j.columns and pd.notna(j["yon"].iloc[i]) else None), "durum_pvquant": (str(j["durum"].iloc[i]) if "durum" in j.columns else None),
                         "edt_net_epias_tl": (_f(e_net.iloc[i]) if edt_var else None), "edt_net_pvquant_tl": _f(p_net.iloc[i]), "edt_fark_tl": (_f(p_net.iloc[i] - e_net.iloc[i]) if edt_var else None),
                         "kupst_epias_tl": (_f(e_kup.iloc[i]) if var("kupst_tl") else None), "kupst_pvquant_tl": _f(p_kup.iloc[i]),
                         "nedenler": [ad for ad, m in (("fiyat", fiyat_f), ("uretim", uretim_f), ("program", program_f), ("pozisyon", pozisyon_f), ("yuvarlama", yuvarlama_f), ("kural", kural_f)) if bool(m.iloc[i])]})
    en = sorted((s for s in satirlar if s["edt_fark_tl"] is not None), key=lambda s: -abs(s["edt_fark_tl"]))[:en_buyuk]
    sonuc.update({"toplam": toplam, "ayristirma": ayr, "en_buyuk": en, "satirlar": satirlar, "neden_aciklama": NEDEN_ACIKLAMA})
    return sonuc


def _f(v, nd: int = 2):
    try:
        return None if v is None or pd.isna(v) else round(float(v), nd)
    except (TypeError, ValueError):
        return None


def kiyas_csv(k: dict) -> str:
    """UTF-8 BOM'lu, noktalı virgüllü, ondalık virgüllü CSV; ilk satır not."""
    kol = ["zaman", "ptf_epias", "ptf_pvquant", "smf_epias", "smf_pvquant", "uevm_mwh", "gerceklesen_pvquant_mwh", "budup_mwh", "program_pvquant_mwh", "program_kaynak",
           "edm_epias_mwh", "sapma_pvquant_mwh", "yon", "edt_net_epias_tl", "edt_net_pvquant_tl", "edt_fark_tl", "kupst_epias_tl", "kupst_pvquant_tl", "nedenler"]
    buf = io.StringIO(); buf.write("# " + NOT + "\n"); buf.write(";".join(kol) + "\n")
    for s in k.get("satirlar") or []:
        buf.write(";".join(("" if s.get(c) is None else (",".join(s[c]) if c == "nedenler" else (str(s[c]).replace(".", ",") if isinstance(s[c], float) else str(s[c])))) for c in kol) + "\n")
    return "﻿" + buf.getvalue()


def ozet_kisa(tenant_id, plant: dict, donem: date, uretim: str | None = None, bugun: date | None = None) -> dict | None:
    """Mutabakat sayfası için kısa özet (tablo yoksa None): yüklü/ortak saat, EDT net farkı, KÜPST farkı, ayrıştırma sayıları."""
    try:
        k = kiyas(tenant_id, plant, donem, uretim, bugun, en_buyuk=0)
    except Exception as e:   # noqa: BLE001 — tablo yoksa (eski DB) mutabakat etkilenmez
        print("[saatlik_detay][ozet]", type(e).__name__, e); return None
    if not k["yuklu"]:
        return {"yuklu": False, "epias_saat": 0, "ortak_saat": 0}
    return {"yuklu": True, "epias_saat": k["epias_saat"], "pv_saat": k.get("pv_saat", 0), "ortak_saat": k.get("ortak_saat", 0), "toplam": k.get("toplam"), "ayristirma": k.get("ayristirma"), "uretim": k.get("uretim")}
