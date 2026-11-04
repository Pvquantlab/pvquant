"""v2.523 (P4a) — Sayaç izleme: uzlaştırmaya esas sayaç verisi (OSOS / MASS / EPYS dışa aktarımı) SCADA serisinden AYRI saklanır;
veri geliş beklentisi (Ölçüm Sistemleri Yön. m.8(2)–(3)), «eksik saat» uyarısı, 12. gün 17:30 geri sayımı (DUY m.81(1), m.82(4)),
SCADA ile sayaç serisinin günlük farkı, değer başına kaynak ve nitelik etiketi; lisanssızda SCADA bağlantı durumu, kopukluk gün sayacı,
uzaktan açma olayı ve Karar 14909 bedel göstergesi (müşterinin girdiği aylık sistem kullanım bedeliyle; askı 30.4.2027 — kısmen teyit).

Dürüstlük: sayaç verisi PVQuant'a dosyayla gelir; EPİAŞ'taki fiilî geliş PVQuant'tan görülmez, beklenen an mevzuattan yazılır. Fark için
eşik ya da «normal oran» uydurulmaz: SCADA brüt AC üretim, sayaç şebekeye verilen net enerjidir (öz tüketim, trafo/hat kaybı, ölçüm noktası).
Bedel göstergesi dağıtım şirketi faturası değildir. Tahmin çekirdeği ve uzlaştırma formülleri değişmez.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import text

from pvquant.db import tenant_baglami
from pvquant.ext.turkiye import takvim as tk
from pvquant.services.mutabakat_service import _sade, _satirlar, _sayi
# v2.535 dayanak künyeleri [OLCUM, KARAR_13995, KARAR_14982, OSOS_UE, LUY, DUY] — bu dosyadaki madde atıflarının birincil yayımı (RG tarih-sayı, karar no); metin kunye.py sicilinden üretildi,
# tests/test_kunye_bekcisi.py sicille eş tutar (kaynak: 03.11.2026 doğrulama arşivi 03_Kaynak_Envanteri).
DAYANAK_KUNYELERI = (
    'Ölçüm Sist. Yön.: Elektrik Piyasası Ölçüm Sistemleri Yönetmeliği, RG 28.12.2023-32413; değişiklikler RG 07.06.2024-32569, 25.09.2024-32673, 21.12.2024-32759, 21.01.2026-33144; '
    'Karar 13995: Akıllı Sayaç Sistemlerinin Yaygınlaştırılmasına ve Kullanımına İlişkin Usul ve Esaslar, Karar 13995, RG 05.12.2025-33098; '
    'Karar 14982: EPDK Kurul Kararı 14982 (dağıtım şirketi mobil uygulaması), RG 24.10.2026-33410; '
    'OSOS U&E: OSOS Kapsamına Giren Tesislere İlişkin Usul ve Esaslar, RG 08.08.2015-29439; '
    'LÜY: Elektrik Piyasasında Lisanssız Elektrik Üretim Yönetmeliği, RG 12.05.2019-30772; değişiklikler RG 09.05.2021-31479, 02.04.2026-33212, 19.10.2026-33405; '
    'DUY: Elektrik Piyasası Dengeleme ve Uzlaştırma Yönetmeliği, RG 14.04.2009-27200; değişiklikler RG 28.03.2015-29309, 30.10.2016-29873, 18.01.2018-30305, 09.08.2019-30857, 02.02.2020-31027, 19.11.2022-32018, 19.12.2023-32404, 17.12.2024-32755, 21.01.2025-32789, 29.12.2025-33122, 19.10.2026-33405, 21.10.2026-33407'
)

IST = ZoneInfo("Europe/Istanbul")

KAYNAKLAR = ("osos", "mass", "epys", "elle")
KAYNAK_ETIKET = {"osos": "OSOS (dağıtım şirketi portalı; bilgi amaçlı, uzlaştırmaya esas UEVM değil)", "mass": "MASS (Millî Akıllı Sayaç Sistemi, massportal.com.tr kullanıcı uygulaması; bilgi amaçlı)", "epys": "EPYS sayaç verisi", "elle": "elle girilen"}
KAYNAK_ONCELIK = {"epys": 0, "osos": 1, "mass": 2, "elle": 3}   # aynı saat için uzlaştırmaya en yakın kaynak gösterilir
NITELIKLER = ("olculmus", "tahmini", "doldurulmus", "elle", "yok")
NITELIK_ETIKET = {"olculmus": "ölçülmüş", "tahmini": "tahmini", "doldurulmus": "doldurulmuş", "elle": "elle girilmiş", "yok": "veri yok"}
_NITELIK_SIRA = {"yok": 0, "tahmini": 1, "doldurulmus": 2, "elle": 3, "olculmus": 4}
# EDAŞ portalı durum kodları (06-46: Estimated, FilledByDiff, BackupMeterData, ManuelData, NoData) ve Türkçe karşılıkları
_NITELIK_ESLEME = (("nodata", "yok"), ("veri yok", "yok"), ("yok", "yok"), ("estimated", "tahmini"), ("tahmin", "tahmini"),
                   ("filledbydiff", "doldurulmus"), ("filled", "doldurulmus"), ("doldur", "doldurulmus"), ("manueldata", "elle"), ("manuel", "elle"),
                   ("elle", "elle"), ("backupmeterdata", "olculmus"), ("backup", "olculmus"), ("olcul", "olculmus"), ("olcum", "olculmus"),
                   ("gercek", "olculmus"), ("actual", "olculmus"), ("measured", "olculmus"), ("ok", "olculmus"))

SAYAC_TURLERI = {"15dk_endeks": "15 dakikalık endeks alınabilen sayaç", "diger": "diğer sayaç (aylık bildirim, saatlik değer)"}
SCADA_DURUMLARI = {"bagli": "bağlı", "kopuk": "bağlantı kopuk / arızalı", "yok": "entegrasyon yok"}
SCADA_ESIK_KW = 50.0            # LÜY m.21(7): 50 kW ve üzeri lisanssız tesis şebeke işletmecisinin SCADA'sına bağlanır (01-16)
LISANSSIZ = ("lisanssiz_iletim", "lisanssiz_dagitim", "oz_tuketim_saatlik")
ASKI_BITIS = date(2027, 4, 30)   # LÜY Geçici m.14(2) askısı — ikincil kaynaktan, kısmen teyit (01-16)
UZAKTAN_ACMA_TUR = "uzaktan_acma"
GELIS_KAYNAK = ("Elektrik Piyasası Ölçüm Sistemleri Yönetmeliği (RG 28.12.2023-32413; son değişiklik RG 21.01.2026-33144) m.8(2): 15 dakikalık endeks alınabilen sayaçların veriş-çekiş değerleri EPİAŞ ile en geç ilgili "
                "saatin 2 saat sonrasında paylaşılır; m.8(3): diğer sayaçlar ayın uzlaştırma takvimindeki son güne kadar. DUY m.81(1): sayaç değerleri dönem sonunu "
                "izleyen ilk 10 gün içinde PYS'ye; m.82(4): 12. gün 17:30'dan sonraki düzeltme o ayın hesabına girmez.")
DAGITIMA_BAGLI = ("lisanssiz_dagitim", "oz_tuketim_saatlik")   # Dağıtım Sistemine Bağlantı Anlaşması tarafı; iletime bağlı lisanssızda anlaşma TEİAŞ'la (kapsam dışı)
M75_ESIK_KW = 900.0             # DUY m.75(4)(ç): acil durum talimatı 900 kW ve üzeri dağıtıma bağlı lisanssızdan başlar; (f) yalnız bu kapsamda (01-16)
BEDEL_KAYNAK = ("Karar 14909 (24.09.2026; RG 19.10.2026-33405, s.6): «Lisanssız Elektrik Üreticileri İçin Dağıtım Sistemine Bağlantı Anlaşması» m.16(1)'e eklenen bedel maddeleri — "
                "(f) SCADA entegrasyonu yoksa her ay için aylık sistem kullanım bedelinin bir katı (yalnız DUY m.75(4) kapsamı: GTŞ/toplayıcı portföyündeki dağıtıma bağlı "
                "lisanssız, 900 kW ve üzeri); (g) acil durum talimatında uzaktan açma yapılamazsa ihlal başına bir kat, ay içinde toplam üç katı aşamaz; (ç) arızalı SCADA bir "
                "ayda onarılmazsa her gün için bedelin %1'i, (g)'nin uygulandığı günde (ç) uygulanmaz. Askı: LÜY Geçici m.14 — bedel maddeleri 30.4.2027'ye kadar uygulanmaz "
                "(Karar metninde tarih yok; ikincil kaynaktan, kısmen teyit).")
NOT = ("Sayaç verisi PVQuant'a dosyayla gelir (OSOS, MASS ya da EPYS dışa aktarımı); EPİAŞ'taki fiilî geliş PVQuant'tan görülmez, beklenen an mevzuattan yazılır. "
       "SCADA/inverter ölçümü brüt AC üretim, sayaç şebekeye verilen net enerjidir; öz tüketim, trafo ve hat kayıpları, ölçüm noktası ve saat dilimi farkı iki seriyi ayırır. "
       "Fark için PVQuant eşik koymaz; oran santrale özgüdür. Bedel göstergesi dağıtım şirketinin faturası değildir.")

_TARIH_RE = re.compile(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})|(\d{4})-(\d{1,2})-(\d{1,2})")
_SAAT_RE = re.compile(r"(\d{1,2}):(\d{2})")
_ZAMAN_IPUCU = ("tarih", "zaman", "saat", "date", "time", "profil", "okuma", "periyot", "period", "timestamp")
_VERIS_IPUCU = ("veris", "uretim", "aktif uretim", "export", "generation", "production", "verilen", "cikis", "active energy")
_CEKIS_IPUCU = ("cekis", "tuketim", "import", "consumption", "alinan", "giris")
_NITELIK_IPUCU = ("durum", "nitelik", "status", "veri tipi", "veri turu", "kaynak", "quality", "kalite")
_ENDEKS_IPUCU = ("endeks", "index")


# ---------------- dosya tanıma ----------------
def _zaman(tarih, saat=None) -> datetime | None:
    """'01.10.2026 08:00' / '2026-10-01 08:00:00' / tarih + ayrı saat ('08:00', '08:00-09:00', '8') → UTC (Türkiye saati varsayılır, dilim başı)."""
    st = str(tarih or "").strip()
    m = _TARIH_RE.search(st)
    if not m:
        return None
    if m.group(1):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        y, mo, d = int(m.group(4)), int(m.group(5)), int(m.group(6))
    hh = mm = 0
    ss = str(saat).strip() if saat not in (None, "") else ""
    h = _SAAT_RE.search(ss) if ss else None
    if h:
        hh, mm = int(h.group(1)), int(h.group(2))
    elif ss and re.fullmatch(r"\d{1,2}", ss):
        hh = int(ss)
    else:
        h2 = _SAAT_RE.search(st[m.end():]) or _SAAT_RE.search(st[:m.start()])
        if h2:
            hh, mm = int(h2.group(1)), int(h2.group(2))
    gun_ek = 0
    if hh == 24:
        hh, gun_ek = 0, 1
    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    try:
        naive = datetime(y, mo, d, hh, mm) + timedelta(days=gun_ek)
    except ValueError:
        return None
    return naive.replace(tzinfo=IST).astimezone(timezone.utc)


def _nitelik(v) -> str:
    s = _sade(v)
    if not s:
        return "olculmus"
    for ip, kod in _NITELIK_ESLEME:
        if ip in s:
            return kod
    return "olculmus"


def _basliklar(satir: list) -> dict | None:
    """Başlık satırını tanı: zaman sütunu (+ ayrı saat), veriş, çekiş, nitelik, birim çarpanı. Endeks (kümülatif) sütunları değer sütunu sayılmaz."""
    adlar = [_sade(c) for c in satir]
    zaman = [i for i, a in enumerate(adlar) if any(ip in a for ip in _ZAMAN_IPUCU)]
    if not zaman:
        return None
    deger = [i for i, a in enumerate(adlar) if i not in zaman and not any(e in a for e in _ENDEKS_IPUCU) and a and a not in ("", "no", "sira")]
    veris = next((i for i in deger if any(ip in adlar[i] for ip in _VERIS_IPUCU)), None)
    cekis = next((i for i in deger if any(ip in adlar[i] for ip in _CEKIS_IPUCU) and i != veris), None)
    belirsiz = False
    if veris is None:
        aday = [i for i in deger if ("kwh" in adlar[i] or "mwh" in adlar[i] or "enerji" in adlar[i] or "energy" in adlar[i]) and i != cekis
                and not any(ip in adlar[i] for ip in _NITELIK_IPUCU)]
        veris = aday[0] if aday else None
        belirsiz = veris is not None and len(aday) > 1   # birden çok enerji sütunu, hiçbiri «veriş/üretim» demiyor
    if veris is None:
        return None
    tarih = zaman[0]
    saat = next((i for i in zaman[1:] if "saat" in adlar[i] or "time" in adlar[i]), None)
    if saat is None and len(zaman) > 1 and ("tarih" in adlar[tarih] or "date" in adlar[tarih]):
        saat = zaman[1]
    nitelik = next((i for i, a in enumerate(adlar) if any(ip in a for ip in _NITELIK_IPUCU) and i not in (veris, cekis, tarih, saat)), None)
    carpan = 1000.0 if "mwh" in adlar[veris] else (0.001 if re.search(r"\bwh\b", adlar[veris]) and "kwh" not in adlar[veris] else 1.0)
    return {"tarih": tarih, "saat": saat, "veris": veris, "cekis": cekis, "nitelik": nitelik, "carpan": carpan, "belirsiz": belirsiz,
            "adlar": {"zaman": str(satir[tarih]), "veris": str(satir[veris]), "cekis": str(satir[cekis]) if cekis is not None else None,
                      "nitelik": str(satir[nitelik]) if nitelik is not None else None}}


def dosya_oku(b: bytes, dosya_adi: str = "", simdi: datetime | None = None) -> dict:
    """OSOS / MASS / EPYS dışa aktarımı (CSV ya da XLSX) → saatlik satırlar. Dakikalık dilimler saate toplanır (kWh); nitelik saatin en zayıf
    dilimidir. Zaman Türkiye saati, dilim başı varsayılır. Tanınmayan dosya → ValueError."""
    satirlar, bicim = _satirlar(b)
    if not satirlar:
        raise ValueError("dosya boş")
    bas, kol = None, None
    for i, s in enumerate(satirlar[:60]):
        kol = _basliklar(s)
        if kol:
            bas = i + 1
            break
    uyarilar: list[str] = []
    if kol is None:   # başlıksız yedek: ilk sütun zaman, ikinci sayı — yalnız satırların en az %90'ı bu biçimdeyse (belirsiz dosya sessizce kayıt üretmez)
        kol = {"tarih": 0, "saat": None, "veris": 1, "cekis": None, "nitelik": None, "carpan": 1.0, "belirsiz": False, "adlar": {"zaman": "1. sütun", "veris": "2. sütun", "cekis": None, "nitelik": None}}
        bas = 0
        uyan = sum(1 for r in satirlar if len(r) >= 2 and _zaman(r[0]) is not None and _sayi(r[1]) is not None)
        if len(satirlar) < 2 or uyan < 0.9 * len(satirlar):
            raise ValueError("başlık satırı tanınmadı (zaman + veriş/üretim kWh sütunu bekleniyor) ve satırlar «zaman;kWh» biçiminde değil; dosya alınmadı")
        uyarilar.append("başlık satırı tanınmadı; 1. sütun zaman, 2. sütun kWh varsayıldı")
    elif kol.get("belirsiz"):
        uyarilar.append(f"veriş sütunu «{kol['adlar']['veris']}» ad ipucu olmadan seçildi (birden çok enerji sütunu var); yanlışsa dosyayı veriş/üretim başlığıyla yükleyin")
    saatler: dict[datetime, dict] = {}
    n_satir = 0; atlanan = 0; gelecek = 0; negatif = 0; yinelenen = 0; dilimler: set[int] = set(); onceki = None
    sinir = (simdi or datetime.now(timezone.utc)) + timedelta(hours=1)   # sayaç verisi gelecekte olamaz (dilim başı ≤ şimdi)
    dilim_kayit: dict[datetime, tuple] = {}
    for s in satirlar[bas:]:
        if len(s) <= kol["veris"]:
            continue
        ts = _zaman(s[kol["tarih"]], s[kol["saat"]] if kol["saat"] is not None and kol["saat"] < len(s) else None)
        v = _sayi(s[kol["veris"]])
        if ts is None or v is None:
            atlanan += 1
            continue
        if ts > sinir:
            gelecek += 1
            continue
        if v < 0:
            negatif += 1
            continue
        n_satir += 1
        if onceki is not None:
            dk = int((ts - onceki).total_seconds() // 60)
            if 0 < dk <= 60:
                dilimler.add(dk)
        onceki = ts
        c = _sayi(s[kol["cekis"]]) if kol["cekis"] is not None and kol["cekis"] < len(s) else None
        nit = _nitelik(s[kol["nitelik"]]) if kol["nitelik"] is not None and kol["nitelik"] < len(s) else "olculmus"
        if ts in dilim_kayit:
            yinelenen += 1   # aynı dilim yeniden: dosyadaki son satır geçerli (düzeltilmiş değer), toplama iki kez girmez
        dilim_kayit[ts] = (v, c, nit)
    for ts, (v, c, nit) in dilim_kayit.items():
        h = ts.replace(minute=0, second=0, microsecond=0)
        k = saatler.setdefault(h, {"ts_utc": h, "veris_kwh": 0.0, "cekis_kwh": None, "nitelik": "olculmus", "n_dilim": 0})
        k["veris_kwh"] += v * kol["carpan"]
        if c is not None:
            k["cekis_kwh"] = (k["cekis_kwh"] or 0.0) + c * kol["carpan"]
        k["n_dilim"] += 1
        if _NITELIK_SIRA[nit] < _NITELIK_SIRA[k["nitelik"]]:
            k["nitelik"] = nit
    if not saatler:
        raise ValueError("dosyada zaman + enerji satırı bulunamadı (beklenen: tarih/saat sütunu ve veriş ya da üretim kWh sütunu; endeks sütunu tek başına yetmez)")
    cozunurluk = min(dilimler) if dilimler else 60
    if atlanan:
        uyarilar.append(f"{atlanan} satır okunamadı (zaman ya da sayı değil)")
    if gelecek:
        uyarilar.append(f"{gelecek} satır gelecek tarihli, alınmadı")
    if negatif:
        uyarilar.append(f"{negatif} satırda negatif veriş değeri, alınmadı (işaret kuralını kontrol edin)")
    if yinelenen:
        uyarilar.append(f"{yinelenen} dilim dosyada birden çok kez geçiyor; son satır alındı")
    if cozunurluk < 60 and any(k["n_dilim"] * cozunurluk < 60 for k in saatler.values()):
        uyarilar.append("bazı saatlerde dilim eksik; saat toplamı eksik dilimle hesaplandı")
    sira = sorted(saatler.values(), key=lambda k: k["ts_utc"])
    for k in sira:
        k["veris_kwh"] = round(k["veris_kwh"], 3)
        if k["cekis_kwh"] is not None:
            k["cekis_kwh"] = round(k["cekis_kwh"], 3)
    sayim: dict[str, int] = {}
    for k in sira:
        sayim[k["nitelik"]] = sayim.get(k["nitelik"], 0) + 1
    return {"bicim": bicim, "satirlar": sira, "n_satir": n_satir, "n_saat": len(sira), "bas": sira[0]["ts_utc"], "bit": sira[-1]["ts_utc"],
            "cozunurluk_dk": cozunurluk, "nitelik_sayim": sayim, "uyarilar": uyarilar, "kolonlar": kol["adlar"],
            "atlanan": {"okunamayan": atlanan, "gelecek": gelecek, "negatif": negatif, "yinelenen": yinelenen},
            "toplam_veris_kwh": round(sum(k["veris_kwh"] for k in sira), 1)}


# ---------------- kayıt ----------------
def kaydet(tenant_id, plant: dict, b: bytes, dosya_adi: str, kaynak: str, yukleyen=None, simdi: datetime | None = None) -> dict:
    if kaynak not in KAYNAKLAR:
        raise ValueError("kaynak osos / mass / epys / elle olmalı")
    if len(b) > 8 * 1024 * 1024:
        raise ValueError("dosya 8 MB'ı aşıyor")
    o = dosya_oku(b, dosya_adi, simdi=simdi)
    sha = hashlib.sha256(b).hexdigest()
    yid = str(uuid.uuid4())
    try:
        yukleyen = str(uuid.UUID(str(yukleyen))) if yukleyen else None
    except ValueError:
        yukleyen = None
    with tenant_baglami(tenant_id) as s:
        s.execute(text("INSERT INTO sayac_saatlik(tenant_id, plant_id, ts_utc, kaynak, veris_kwh, cekis_kwh, nitelik, n_dilim, yukleme_id) "
                       "VALUES (CAST(:t AS uuid), CAST(:p AS uuid), :ts, :k, :v, :c, :n, :d, CAST(:y AS uuid)) "
                       "ON CONFLICT (plant_id, ts_utc, kaynak) DO UPDATE SET veris_kwh = EXCLUDED.veris_kwh, cekis_kwh = EXCLUDED.cekis_kwh, "
                       "nitelik = EXCLUDED.nitelik, n_dilim = EXCLUDED.n_dilim, yukleme_id = EXCLUDED.yukleme_id, guncelleme = now()"),
                  [{"t": tenant_id, "p": plant["id"], "ts": r["ts_utc"], "k": kaynak, "v": r["veris_kwh"], "c": r["cekis_kwh"], "n": r["nitelik"], "d": r["n_dilim"], "y": yid}
                   for r in o["satirlar"]])
        s.execute(text("INSERT INTO sayac_yukleme(id, tenant_id, plant_id, kaynak, dosya_adi, sha256, bicim, bas_utc, bit_utc, n_saat, n_satir, nitelik_json, uyarilar_json, yukleyen) "
                       "VALUES (CAST(:id AS uuid), CAST(:t AS uuid), CAST(:p AS uuid), :k, :f, :sha, :b, :bas, :bit, :ns, :nr, CAST(:nj AS jsonb), CAST(:uj AS jsonb), "
                       "CAST(:y AS uuid))"),
                  {"id": yid, "t": tenant_id, "p": plant["id"], "k": kaynak, "f": dosya_adi[:200], "sha": sha, "b": o["bicim"], "bas": o["bas"], "bit": o["bit"],
                   "ns": o["n_saat"], "nr": o["n_satir"], "nj": json.dumps(o["nitelik_sayim"]), "uj": json.dumps(o["uyarilar"], ensure_ascii=False), "y": yukleyen})
    return {"yukleme_id": yid, "kaynak": kaynak, "kaynak_etiket": KAYNAK_ETIKET[kaynak], "dosya_adi": dosya_adi, "sha256": sha, "bicim": o["bicim"],
            "bas": o["bas"].isoformat(), "bit": o["bit"].isoformat(), "n_saat": o["n_saat"], "n_satir": o["n_satir"], "cozunurluk_dk": o["cozunurluk_dk"],
            "nitelik_sayim": o["nitelik_sayim"], "toplam_veris_kwh": o["toplam_veris_kwh"], "kolonlar": o["kolonlar"], "uyarilar": o["uyarilar"], "atlanan": o["atlanan"]}


def yuklemeler(tenant_id, plant_id, n: int = 20) -> list[dict]:
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text("SELECT id, kaynak, dosya_adi, sha256, bicim, bas_utc, bit_utc, n_saat, n_satir, nitelik_json, uyarilar_json, olusturma "
                              "FROM sayac_yukleme WHERE plant_id = CAST(:p AS uuid) ORDER BY olusturma DESC LIMIT :n"), {"p": plant_id, "n": n}).mappings().all()
    return [{"yukleme_id": str(r["id"]), "kaynak": r["kaynak"], "kaynak_etiket": KAYNAK_ETIKET.get(r["kaynak"], r["kaynak"]), "dosya_adi": r["dosya_adi"],
             "sha256": r["sha256"], "bicim": r["bicim"], "bas": r["bas_utc"].isoformat() if r["bas_utc"] else None, "bit": r["bit_utc"].isoformat() if r["bit_utc"] else None,
             "n_saat": int(r["n_saat"] or 0), "n_satir": int(r["n_satir"] or 0), "nitelik_sayim": r["nitelik_json"] or {}, "uyarilar": r["uyarilar_json"] or [],
             "zaman": r["olusturma"].isoformat()} for r in rows]


def sayac_oku(tenant_id, plant_id, bas: datetime, bit: datetime) -> pd.DataFrame:
    """[bas, bit) aralığı; aynı saatte birden çok kaynak varsa uzlaştırmaya en yakın olan (epys > osos > mass > elle). UTC indeks."""
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text("SELECT ts_utc, kaynak, veris_kwh, cekis_kwh, nitelik, n_dilim FROM sayac_saatlik "
                              "WHERE plant_id = CAST(:p AS uuid) AND ts_utc >= :a AND ts_utc < :b ORDER BY ts_utc"),
                         s.connection(), params={"p": plant_id, "a": bas, "b": bit}, parse_dates=["ts_utc"])
    if df.empty:
        return pd.DataFrame(columns=["kaynak", "veris_kwh", "cekis_kwh", "nitelik", "n_dilim"], index=pd.DatetimeIndex([], tz="UTC", name="ts_utc"))
    df["_o"] = df["kaynak"].map(KAYNAK_ONCELIK).fillna(9)
    df = df.sort_values(["ts_utc", "_o"]).drop_duplicates("ts_utc").drop(columns="_o").set_index("ts_utc")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def scada_oku(tenant_id, plant_id, bas: datetime, bit: datetime) -> pd.DataFrame:
    """Geçerli SCADA saatleri (kWh: energy_kwh, yoksa power_kw × 1 sa) + kaynak etiketi (scada_dosya / epias_seffaflik; v2.278 partisi)."""
    with tenant_baglami(tenant_id) as s:
        df = pd.read_sql(text("SELECT h.ts_utc, COALESCE(h.energy_kwh, h.power_kw) AS kwh, h.flag, "
                              "CASE WHEN b.filename = 'epias_realtime' THEN 'epias_seffaflik' ELSE 'scada_dosya' END AS kaynak "
                              "FROM scada_hourly h LEFT JOIN ingestion_batches b ON b.id = h.batch_id "
                              "WHERE h.plant_id = CAST(:p AS uuid) AND h.flag = 'valid' AND h.ts_utc >= :a AND h.ts_utc < :b ORDER BY h.ts_utc"),
                         s.connection(), params={"p": plant_id, "a": bas, "b": bit}, parse_dates=["ts_utc"])
    if df.empty:
        return pd.DataFrame(columns=["kwh", "flag", "kaynak"], index=pd.DatetimeIndex([], tz="UTC", name="ts_utc"))
    df = df.set_index("ts_utc")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


# ---------------- SCADA ↔ sayaç farkı ----------------
def _birlestir(scada: pd.DataFrame, sayac: pd.DataFrame) -> pd.DataFrame:
    """Saat bazında dış birleşim: scada_kwh, sayac_kwh, nitelik, ortak (iki seri de var), olculmus (ortak ve sayaç niteliği ölçülmüş), tahmini (tahmini/doldurulmuş/yok)."""
    s = scada[["kwh", "kaynak"]].rename(columns={"kwh": "scada_kwh"}) if not scada.empty else pd.DataFrame(columns=["scada_kwh", "kaynak"])
    m = sayac[["veris_kwh", "nitelik", "kaynak"]].rename(columns={"veris_kwh": "sayac_kwh", "kaynak": "sayac_kaynak"}) if not sayac.empty else pd.DataFrame(columns=["sayac_kwh", "nitelik", "sayac_kaynak"])
    j = s.join(m, how="outer").copy()
    for c in ("scada_kwh", "sayac_kwh"):
        j[c] = pd.to_numeric(j[c], errors="coerce")   # boş taraf object kalmasın
    if j.empty:
        return j
    j["gun"] = j.index.tz_convert(IST).strftime("%Y-%m-%d")
    j["ortak"] = j["scada_kwh"].notna() & j["sayac_kwh"].notna()
    j["ortak_scada"] = j["scada_kwh"].where(j["ortak"]); j["ortak_sayac"] = j["sayac_kwh"].where(j["ortak"])
    j["tahmini"] = j["nitelik"].isin(["tahmini", "doldurulmus", "yok"])
    j["olculmus"] = j["ortak"] & j["nitelik"].eq("olculmus")
    j["olc_scada"] = j["scada_kwh"].where(j["olculmus"]); j["olc_sayac"] = j["sayac_kwh"].where(j["olculmus"])
    return j


def _kiyas(scada_kwh: float | None, sayac_kwh: float | None, saat: int) -> dict:
    """Toplam çifti → fark (sayaç − SCADA) ve yüzde (SCADA toplamına oranla); SCADA 0 ya da saat yoksa yüzde yok."""
    if not saat or scada_kwh is None or sayac_kwh is None:
        return {"saat": int(saat or 0), "scada_kwh": None, "sayac_kwh": None, "fark_kwh": None, "fark_pct": None}
    fark = sayac_kwh - scada_kwh
    return {"saat": int(saat), "scada_kwh": round(scada_kwh, 1), "sayac_kwh": round(sayac_kwh, 1), "fark_kwh": round(fark, 1), "fark_pct": (round(fark / scada_kwh * 100, 1) if scada_kwh > 0 else None)}


def fark_df(scada: pd.DataFrame, sayac: pd.DataFrame) -> pd.DataFrame:
    """Saf hesap: günlük (Türkiye günü) SCADA kWh, sayaç veriş kWh, fark (sayaç − SCADA), yüzde (SCADA'ya oranla, yalnız ortak saatlerde), saat sayıları,
    tahmini/doldurulmuş saat sayısı ve yalnız ölçülmüş saatlerin fark yüzdesi. Yalnız iki serinin de bulunduğu saatler kıyaslanır; tek taraflı saatler ayrı sayılır."""
    j = _birlestir(scada, sayac)
    if j.empty:
        return pd.DataFrame(columns=["gun", "scada_kwh", "sayac_kwh", "ortak_scada_kwh", "ortak_sayac_kwh", "fark_kwh", "fark_pct", "saat_scada", "saat_sayac", "saat_ortak", "saat_tahmini", "saat_olculmus", "olc_fark_pct"])
    g = j.groupby("gun")
    out = pd.DataFrame({"scada_kwh": g["scada_kwh"].sum(min_count=1), "sayac_kwh": g["sayac_kwh"].sum(min_count=1),
                        "ortak_scada_kwh": g["ortak_scada"].sum(min_count=1), "ortak_sayac_kwh": g["ortak_sayac"].sum(min_count=1),
                        "saat_scada": g["scada_kwh"].count(), "saat_sayac": g["sayac_kwh"].count(), "saat_ortak": g["ortak"].sum(), "saat_tahmini": g["tahmini"].sum(),
                        "saat_olculmus": g["olculmus"].sum(), "olc_scada": g["olc_scada"].sum(min_count=1), "olc_sayac": g["olc_sayac"].sum(min_count=1)})
    out["fark_kwh"] = out["ortak_sayac_kwh"] - out["ortak_scada_kwh"]
    out["fark_pct"] = (out["fark_kwh"] / out["ortak_scada_kwh"] * 100).where(out["ortak_scada_kwh"] > 0)
    out["olc_fark_pct"] = ((out["olc_sayac"] - out["olc_scada"]) / out["olc_scada"] * 100).where(out["olc_scada"] > 0)
    out = out.drop(columns=["olc_scada", "olc_sayac"]).reset_index()
    for c in ("scada_kwh", "sayac_kwh", "ortak_scada_kwh", "ortak_sayac_kwh", "fark_kwh", "fark_pct", "olc_fark_pct"):
        out[c] = pd.to_numeric(out[c], errors="coerce").astype(float).round(1)
    for c in ("saat_scada", "saat_sayac", "saat_ortak", "saat_tahmini", "saat_olculmus"):
        out[c] = out[c].astype(int)
    return out


def _sayim(j: pd.DataFrame) -> dict:
    return {str(k): int(v) for k, v in j.items()}


def fark(tenant_id, plant: dict, gun: int = 30, bugun: date | None = None) -> dict:
    b = bugun or datetime.now(IST).date()
    bas = datetime.combine(b - timedelta(days=gun - 1), datetime.min.time(), tzinfo=IST).astimezone(timezone.utc)   # bugün dâhil tam `gun` gün
    bit = datetime.combine(b + timedelta(days=1), datetime.min.time(), tzinfo=IST).astimezone(timezone.utc)
    sc = scada_oku(tenant_id, plant["id"], bas, bit); sy = sayac_oku(tenant_id, plant["id"], bas, bit)
    df = fark_df(sc, sy); j = _birlestir(sc, sy)
    # yalnız ölçülmüş sayaç saatleri (tahmini / doldurulmuş / elle / «veri yok» dışarıda) ↔ tahmini dâhil bütün ortak saatler
    if not j.empty and j["olculmus"].any():
        olculmus = _kiyas(float(j["olc_scada"].sum()), float(j["olc_sayac"].sum()), int(j["olculmus"].sum()))
    else:
        olculmus = _kiyas(None, None, 0)
    gunler = [{k: (None if pd.isna(v) else (float(v) if isinstance(v, float) else int(v) if hasattr(v, "item") and not isinstance(v, str) else v)) for k, v in r.items()}
              for r in df.to_dict("records")]
    ortak = df[df["saat_ortak"] > 0]
    toplam = {"scada_kwh": round(float(df["scada_kwh"].sum()), 1) if not df.empty else 0.0, "sayac_kwh": round(float(df["sayac_kwh"].sum()), 1) if not df.empty else 0.0,
              "ortak_scada_kwh": round(float(ortak["ortak_scada_kwh"].sum()), 1) if not ortak.empty else None,
              "ortak_sayac_kwh": round(float(ortak["ortak_sayac_kwh"].sum()), 1) if not ortak.empty else None,
              "saat_scada": int(df["saat_scada"].sum()) if not df.empty else 0, "saat_sayac": int(df["saat_sayac"].sum()) if not df.empty else 0,
              "saat_ortak": int(df["saat_ortak"].sum()) if not df.empty else 0, "saat_tahmini": int(df["saat_tahmini"].sum()) if not df.empty else 0}
    if toplam["ortak_scada_kwh"]:
        toplam["fark_kwh"] = round(toplam["ortak_sayac_kwh"] - toplam["ortak_scada_kwh"], 1)
        toplam["fark_pct"] = round(toplam["fark_kwh"] / toplam["ortak_scada_kwh"] * 100, 1)
    else:
        toplam["fark_kwh"] = None; toplam["fark_pct"] = None
    en_buyuk = None
    if not ortak.empty and ortak["fark_pct"].notna().any():
        r = ortak.loc[ortak["fark_pct"].abs().idxmax()]
        en_buyuk = {"gun": r["gun"], "fark_kwh": float(r["fark_kwh"]), "fark_pct": float(r["fark_pct"])}
    # değer başına kaynak etiketi: pencere saatlerinin kaynağa göre dağılımı
    kaynak = {"scada_dosya": int((sc["kaynak"] == "scada_dosya").sum()) if not sc.empty else 0, "epias_seffaflik": int((sc["kaynak"] == "epias_seffaflik").sum()) if not sc.empty else 0,
              **{f"sayac_{n}": (int((sy["nitelik"] == n).sum()) if not sy.empty else 0) for n in NITELIKLER}}
    toplam_saat = int(((bit - bas).total_seconds()) // 3600)
    kaynak["gercek_yok"] = max(0, toplam_saat - (0 if sc.empty else len(sc)))
    kaynak["sayac_yok_saat"] = max(0, toplam_saat - (0 if sy.empty else len(sy)))
    sayac_kaynak = _sayim(sy["kaynak"].value_counts()) if not sy.empty else {}
    tahmini_dahil = _kiyas(toplam["ortak_scada_kwh"], toplam["ortak_sayac_kwh"], toplam["saat_ortak"])
    return {"pencere_gun": gun, "bas": bas.astimezone(IST).date().isoformat(), "bit": b.isoformat(), "gunler": gunler, "toplam": toplam, "en_buyuk_fark": en_buyuk,
            "olculmus": olculmus, "tahmini_dahil": tahmini_dahil,
            "kapsam": {"pencere_saat": toplam_saat, "ortak_saat": toplam["saat_ortak"], "ortak_pct": round(toplam["saat_ortak"] / toplam_saat * 100, 1) if toplam_saat else None,
                       "yalniz_scada_saat": toplam["saat_scada"] - toplam["saat_ortak"], "yalniz_sayac_saat": toplam["saat_sayac"] - toplam["saat_ortak"],
                       "ikisi_de_yok_saat": max(0, toplam_saat - (0 if j.empty else len(j)))},
            "kaynak_sayim": kaynak, "sayac_kaynak_sayim": sayac_kaynak, "pencere_saat": toplam_saat,
            "aciklama": ("Fark = sayaç − SCADA, yalnız iki serinin de bulunduğu saatlerde; yüzde SCADA toplamına oranla. SCADA/inverter brüt AC üretimdir, sayaç "
                         "şebekeye verilen net enerjidir: öz tüketim, trafo ve hat kayıpları, ölçüm noktası (AG/OG) ve saat dilimi farkı iki seriyi ayırır. "
                         "Oran santrale özgüdür; PVQuant eşik koymaz. Tahmini ya da doldurulmuş sayaç saatleri ayrıca sayılır; düzeltme talebi dağıtım şirketine/TEİAŞ'a başvuruyla yapılır (DUY m.82(3)); 12. gün 17:30 sonrası o aya girmez (m.82(4)).")}


# ---------------- veri geliş beklentisi ----------------
def _ay_bas(d: date) -> date:
    return d.replace(day=1)


def _onceki_ay(d: date) -> date:
    return (d.replace(day=1) - timedelta(days=1)).replace(day=1)


def gelis(tenant_id, plant: dict, pj: dict, simdi: datetime | None = None) -> dict:
    """Sayaç türüne göre beklenen EPİAŞ geliş anı (m.8(2) saat + 2 sa / m.8(3) takvim), PVQuant'taki son sayaç ve SCADA saati, bu ayın eksik
    saatleri (15 dk sayaçta: ay başından şimdi − 2 saate kadar sayaç satırı olmayan saatler), dönem düzeltme geri sayımı (10. gün, 12. gün 17:30)."""
    now = simdi or datetime.now(timezone.utc)
    now_ist = now.astimezone(IST)
    tur = pj.get("sayac_turu") if pj.get("sayac_turu") in SAYAC_TURLERI else None
    with tenant_baglami(tenant_id) as s:
        son_sayac = s.execute(text("SELECT max(ts_utc) FROM sayac_saatlik WHERE plant_id = CAST(:p AS uuid)"), {"p": plant["id"]}).scalar()
        son_scada = s.execute(text("SELECT max(ts_utc) FROM scada_hourly WHERE plant_id = CAST(:p AS uuid) AND flag = 'valid'"), {"p": plant["id"]}).scalar()
    ay_bas = datetime.combine(_ay_bas(now_ist.date()), datetime.min.time(), tzinfo=IST).astimezone(timezone.utc)
    gecen_bit = now.replace(minute=0, second=0, microsecond=0)                              # başlamış saat dilimleri (bu saat hariç)
    son_beklenen = gecen_bit - timedelta(hours=2)                                           # m.8(2): saat + 2 sa (dilim sonundan sayıldı — koruyucu; sayım başlangıcı metinde açık değil)
    gecen_saat = max(0, int((gecen_bit - ay_bas).total_seconds() // 3600))
    beklenen_saat_ay = max(0, int((son_beklenen - ay_bas).total_seconds() // 3600)) if tur == "15dk_endeks" else None
    ay_df = sayac_oku(tenant_id, plant["id"], ay_bas, max(ay_bas, son_beklenen if beklenen_saat_ay is not None else gecen_bit))
    yuklu = int(len(ay_df)); yuklu_tahmini = int(ay_df["nitelik"].isin(["tahmini", "doldurulmus", "yok"]).sum()) if yuklu else 0
    ay_sayac = yuklu
    eksik = (beklenen_saat_ay - yuklu) if beklenen_saat_ay is not None else None
    siniflama = {"gecen_saat": gecen_saat, "vadesi_gelen": beklenen_saat_ay, "vadesi_gelmemis": (gecen_saat - beklenen_saat_ay) if beklenen_saat_ay is not None else None,
                 "yuklu": yuklu, "yuklu_olculmus": yuklu - yuklu_tahmini, "yuklu_tahmini": yuklu_tahmini, "eksik": (max(0, eksik) if eksik is not None else None),
                 "not": ("«Vadesi gelen»: ay başından, şu anki saatten 2 saat öncesine kadar başlamış saat dilimleri (m.8(2); dilim sonundan sayıldı). «Eksik»: vadesi gelen "
                         "ama PVQuant'a yüklenmemiş saat; EPİAŞ'a ulaşıp ulaşmadığı PVQuant'tan görülmez. Geç geliş EPİAŞ tarafında ölçülemez; PVQuant yalnız yükleme anını tutar.")}
    if tur == "15dk_endeks":
        beklenen = {"kural": "her saat için ilgili saat + 2 saat; tam gün en geç ertesi gün ≈ 02:00", "dayanak": "Ölçüm Sist. Yön. m.8(2)", "kesinlik": "belirsiz",
                    "not": "«2 saat sonrası»nın saatin başından mı sonundan mı sayıldığı metinde açık değil; dağıtım şirketlerinin fiilî uyumu doğrulanmadı.",
                    "son_beklenen_saat": (son_beklenen - timedelta(hours=1)).astimezone(IST).isoformat(),   # beklenen SON saat diliminin başı
                    "son_beklenen_dilim": f"{(son_beklenen - timedelta(hours=1)).astimezone(IST):%H:%M}–{son_beklenen.astimezone(IST):%H:%M}"}
    elif tur == "diger":
        beklenen = {"kural": "ayın uzlaştırma takvimindeki son güne kadar (Ölçüm Sist. Yön. m.8(3)); dönem sonunu izleyen ilk 10 gün (DUY m.81(1))", "dayanak": "Ölçüm Sist. Yön. m.8(3); DUY m.81(1)", "kesinlik": "belirsiz",
                    "not": "m.8(3) «takvimin son günü» ile m.81(1) «ilk 10 gün» eşitlemesi yorumdur (v2.537 DK-392).", "son_beklenen_saat": None, "son_beklenen_dilim": None}
    else:
        beklenen = {"kural": "sayaç türü seçilmedi", "dayanak": None, "kesinlik": None, "not": "Sayaç türünü seçin: 15 dakikalık endeks alınabilen sayaçta saat bazlı, diğerlerinde aylık beklenti uygulanır.", "son_beklenen_saat": None, "son_beklenen_dilim": None}
    # dönem düzeltme geri sayımı: son biten ay; 12. gün 17:30 geçtiyse bir sonraki dönem de gösterilir
    def _donem(d: date) -> dict:
        ol = {o["kod"]: o for o in tk.donem_takvimi(d.year, d.month)}
        sv, it = ol["sayac_veri"], ol["itiraz_son"]
        it_dt = datetime.fromisoformat(it["tarih"] + "T17:30").replace(tzinfo=IST)
        kalan = it_dt - now_ist
        # dönemin sayaç kapsamı: bitmiş ay ise bütün saatleri vadesi gelmiş; süren ay ise vadesi gelen kısmı
        d_bas = datetime.combine(d, datetime.min.time(), tzinfo=IST).astimezone(timezone.utc)
        d_bit = datetime.combine(tk.ay_ekle(d, 1), datetime.min.time(), tzinfo=IST).astimezone(timezone.utc)
        vade_bit = min(d_bit, son_beklenen) if tur == "15dk_endeks" else (d_bit if d_bit <= now else None)
        if vade_bit is not None and vade_bit > d_bas:
            x = sayac_oku(tenant_id, plant["id"], d_bas, vade_bit)
            toplam = int((vade_bit - d_bas).total_seconds() // 3600); y = int(len(x)); t = int(x["nitelik"].isin(["tahmini", "doldurulmus", "yok"]).sum()) if y else 0
            kapsam = {"vadesi_gelen": toplam, "yuklu": y, "olculmus": y - t, "tahmini": t, "eksik": max(0, toplam - y), "tam_ay": vade_bit >= d_bit}
        else:
            kapsam = {"vadesi_gelen": 0, "yuklu": 0, "olculmus": 0, "tahmini": 0, "eksik": 0, "tam_ay": False}
        return {"donem": d.strftime("%Y-%m"), "sayac_veri": sv["tarih"], "itiraz_son": it["tarih"] + " 17:30", "kalan_saat": round(kalan.total_seconds() / 3600, 1),
                "gecti": kalan.total_seconds() < 0, "hafta_sonu": bool(it.get("hafta_sonu")), "not": it.get("not"), "kaynak": it["kaynak"], "kapsam": kapsam}
    onceki = _donem(_onceki_ay(now_ist.date()))
    donemler = [onceki] + ([_donem(_ay_bas(now_ist.date()))] if onceki["gecti"] else [])
    return {"sayac_turu": tur, "sayac_turu_etiket": SAYAC_TURLERI.get(tur) if tur else None, "beklenen": beklenen,
            "son_sayac": son_sayac.isoformat() if son_sayac else None, "son_scada": son_scada.isoformat() if son_scada else None,
            "son_sayac_saat_once": round((now - son_sayac).total_seconds() / 3600, 1) if son_sayac else None,
            "ay": now_ist.strftime("%Y-%m"), "ay_sayac_saat": int(ay_sayac), "ay_beklenen_saat": beklenen_saat_ay, "ay_eksik_saat": (max(0, eksik) if eksik is not None else None),
            "siniflama": siniflama, "donemler": donemler, "kaynak": GELIS_KAYNAK}


# ---------------- lisanssız SCADA durumu ve Karar 14909 bedel göstergesi ----------------
def _kurulu_kw(plant: dict) -> float:
    return float(plant.get("ac_limit_kw") or plant.get("capacity_kwp") or 0.0)


def scada_durumu(plant: dict, pj: dict, segment: str | None, bugun: date, uzaktan_acma_ay: int = 0, uzaktan_acma_gunleri: set | None = None) -> dict | None:
    """Lisanssız tesiste SCADA yükümlülüğü (LÜY m.21(7): 50 kW ve üzeri), beyan edilen bağlantı durumu, kopukluk gün sayacı, bu ayın uzaktan açma olayları ve
    Karar 14909 bedel göstergesi (aylık sistem kullanım bedeli girilmişse; yalnız dağıtıma bağlı lisanssız — Dağıtım Sistemine Bağlantı Anlaşması tarafı).
    (f) yalnız DUY m.75(4) kapsamı (900 kW ve üzeri); (ç) yalnız bu ayın 30 günü aşan günleri, (g) uygulanan günler hariç. Lisanslı segmentte None."""
    if segment not in LISANSSIZ:
        return None
    kw = _kurulu_kw(plant)
    yukumlu = kw >= SCADA_ESIK_KW
    anlasma = segment in DAGITIMA_BAGLI
    m75 = kw >= M75_ESIK_KW
    durum = pj.get("scada_durum") if pj.get("scada_durum") in SCADA_DURUMLARI else None
    bas = tk._tarih(pj.get("scada_kopukluk_baslangic"))
    kopuk_gun = (bugun - bas).days if (durum == "kopuk" and bas) else None
    bedel = pj.get("sistem_kullanim_bedeli_tl_ay")
    try:
        bedel = float(bedel) if bedel not in (None, "") else None
    except (TypeError, ValueError):
        bedel = None
    kalemler = []; uygulanmayan = []
    if yukumlu and anlasma:
        if durum == "yok":
            if m75:
                kalemler.append({"kod": "entegrasyon_yok", "etiket": "SCADA entegrasyonu yok — m.16(1)(f)", "kat": 1.0, "birim": "aylık bedelin bir katı / ay", "tutar_tl": (bedel if bedel else None), "aski": "kapsamda",
                                 "not": "Yalnız DUY m.75(4) kapsamındaki tesisler (GTŞ/toplayıcı portföyünde, 900 kW ve üzeri); portföy üyeliği beyan edilmedi, kurulu güce göre sayıldı."})
            else:
                uygulanmayan.append(f"m.16(1)(f) SCADA entegrasyonu yok: kurulu güç {kw:,.0f} kW < {M75_ESIK_KW:,.0f} kW (DUY m.75(4) kapsamı dışı), gösterge uygulanmadı".replace(",", "."))
        if uzaktan_acma_ay:
            kat = min(3.0, float(uzaktan_acma_ay))
            kalemler.append({"kod": "uzaktan_acma", "etiket": f"uzaktan açma yapılamadı — m.16(1)(g) ({uzaktan_acma_ay} olay; ay içinde en çok 3 kat)", "kat": kat, "birim": "ihlal başına bir kat",
                             "tutar_tl": (round(bedel * kat, 2) if bedel else None), "aski": "kapsamda"})
        if durum == "kopuk" and bas is not None and kopuk_gun is not None and kopuk_gun > 30:
            ay_bas = _ay_bas(bugun); esik_gun = bas + timedelta(days=30)
            gunler = [ay_bas + timedelta(days=i) for i in range((bugun - ay_bas).days + 1)]
            sayilan = [g for g in gunler if g > esik_gun and g not in (uzaktan_acma_gunleri or set())]
            g = len(sayilan)
            if g:
                kalemler.append({"kod": "onarim_gecikti", "etiket": f"arızalı SCADA bir ayda onarılmadı — m.16(1)(ç) (bu ay {g} gün; günlük %1)", "kat": round(g * 0.01, 2), "birim": "bedelin %1'i / gün",
                                 "tutar_tl": (round(bedel * g * 0.01, 2) if bedel else None), "kesinlik": "belirsiz", "aski": "dogrulanmadi",
                                 "not": "(ç) Karar 14909'dan önce de anlaşmadaydı; LÜY Geçici m.14 askısının (ç)'yi kapsayıp kapsamadığı doğrulanmadı. Günlük %1'in bir aylık sürenin "
                                        "sonrasındaki günler için mi, bütün günler için mi sayıldığı karar metninden açık değil; burada bu ayın 30 günü aşan günleri sayıldı, (g) uygulanan günler hariç."})
    elif yukumlu and not anlasma:
        uygulanmayan.append("İletime bağlı lisanssız tesis: bağlantı anlaşması TEİAŞ'la; Karar 14909 dağıtım bağlantı anlaşmasına ilişkindir, gösterge uygulanmadı (TEİAŞ anlaşmasındaki hükümler doğrulanmadı)")
    toplam = round(sum(k["tutar_tl"] for k in kalemler if k["tutar_tl"] is not None), 2) if bedel and kalemler else None
    toplam_aski = round(sum(k["tutar_tl"] for k in kalemler if k["tutar_tl"] is not None and k.get("aski") == "kapsamda"), 2) if bedel and kalemler else None
    toplam_aski_disi = round(sum(k["tutar_tl"] for k in kalemler if k["tutar_tl"] is not None and k.get("aski") != "kapsamda"), 2) if bedel and kalemler else None
    return {"yukumlu": yukumlu, "esik_kw": SCADA_ESIK_KW, "kurulu_kw": kw, "kurulu_kaynak": "AC sınırı" if plant.get("ac_limit_kw") else "kurulu güç (kWp)",
            "anlasma": "dagitim" if anlasma else "iletim", "m75_kapsam": m75, "m75_esik_kw": M75_ESIK_KW,
            "durum": durum, "durum_etiket": SCADA_DURUMLARI.get(durum) if durum else "girilmedi", "durum_kaynagi": "beyan",
            "kopukluk_baslangic": bas.isoformat() if bas else None, "kopukluk_gun": kopuk_gun,
            "uzaktan_acma_var": pj.get("uzaktan_acma_var") if isinstance(pj.get("uzaktan_acma_var"), bool) else None, "uzaktan_acma_ay": int(uzaktan_acma_ay),
            "bedel_tl_ay": bedel, "kalemler": kalemler, "uygulanmayan": uygulanmayan, "toplam_tl": toplam, "toplam_aski_tl": toplam_aski, "toplam_aski_disi_tl": toplam_aski_disi, "tutar_niteligi": "varsayimsal",
            "aski_kapsami": "Askı (LÜY Geçici m.14) Karar 14909'un eklediği (f) ve (g) içindir; (ç) anlaşmada önceden vardı, askı kapsamı doğrulanmadı.",
            "aski_bitis": ASKI_BITIS.isoformat(), "aski_kesinlik": "kismen_teyit", "aski_gecti": bugun > ASKI_BITIS, "aski_kalan_gun": (ASKI_BITIS - bugun).days,
            "kaynak": BEDEL_KAYNAK, "dayanak_yukumluluk": "LÜY m.21(7): kurulu gücü 50 kW ve üzeri lisanssız tesis şebeke işletmecisinin SCADA'sına bağlanır; ekipman üreticiye ait",
            "not": ("Bağlantı durumu beyandır (bu sayfada girilir); PVQuant şebeke işletmecisinin SCADA'sına bağlı değildir, bağlantı sağlığını ölçmez. Gösterge, girdiğiniz aylık "
                    "sistem kullanım bedeliyle Karar 14909 bedel maddelerinin kaba uygulamasıdır: varsayımsal tutardır, tebliğ edilmiş bir borç değildir; dağıtım şirketinin "
                    "faturası ya da tebligatı esastır. Bedel girilmezse tutar verilmez. Askı süresi bitene kadar (30.4.2027; tarih kısmen teyit) bedel uygulanmaz.")}


def ayar_dogrula(g: dict) -> dict:
    """PUT sayac-ayar: yalnız verilen alanlar; None temizler. Hatalı alan → ValueError(alan)."""
    out: dict = {}
    if "sayac_turu" in g:
        v = g["sayac_turu"]
        if v not in (None, "") and v not in SAYAC_TURLERI:
            raise ValueError("sayac_turu")
        out["sayac_turu"] = v or None
    if "scada_durum" in g:
        v = g["scada_durum"]
        if v not in (None, "") and v not in SCADA_DURUMLARI:
            raise ValueError("scada_durum")
        out["scada_durum"] = v or None
    if "scada_kopukluk_baslangic" in g:
        v = g["scada_kopukluk_baslangic"]
        if v in (None, ""):
            out["scada_kopukluk_baslangic"] = None
        else:
            try:
                d = date.fromisoformat(str(v)[:10])
            except ValueError:
                raise ValueError("scada_kopukluk_baslangic")
            if d > datetime.now(IST).date():
                raise ValueError("scada_kopukluk_baslangic")   # gelecekte başlayan kopukluk olmaz
            out["scada_kopukluk_baslangic"] = d.isoformat()
    if "uzaktan_acma_var" in g:
        v = g["uzaktan_acma_var"]
        if v is not None and not isinstance(v, bool):
            raise ValueError("uzaktan_acma_var")
        out["uzaktan_acma_var"] = v
    if "uzlastirma_girdi" in g:   # v2.526 (P4a-2): uzlaştırma yeniden hesabında gerçekleşen üretim kaynağı
        v = g["uzlastirma_girdi"]
        if v not in (None, "", "scada", "sayac"):
            raise ValueError("uzlastirma_girdi")
        out["uzlastirma_girdi"] = v or None
    if "sistem_kullanim_bedeli_tl_ay" in g:
        v = g["sistem_kullanim_bedeli_tl_ay"]
        if v in (None, ""):
            out["sistem_kullanim_bedeli_tl_ay"] = None
        else:
            try:
                x = float(v)
            except (TypeError, ValueError):
                raise ValueError("sistem_kullanim_bedeli_tl_ay")
            if not (0 <= x <= 1e9):
                raise ValueError("sistem_kullanim_bedeli_tl_ay")
            out["sistem_kullanim_bedeli_tl_ay"] = x
    return out


# ---------------- müşteri ucu ----------------
def ozet(tenant_id, plant: dict, gun: int = 30, simdi: datetime | None = None) -> dict:
    from pvquant.services import dengesizlik_service, olay_service
    now = simdi or datetime.now(timezone.utc)
    bugun = now.astimezone(IST).date()
    pj = dengesizlik_service._pj(plant.get("params_json")); seg = dengesizlik_service.segment_bilgisi(plant.get("params_json"))
    ay_bas = datetime.combine(_ay_bas(bugun), datetime.min.time(), tzinfo=IST)
    try:
        uz_olaylar = olay_service.aralik(tenant_id, plant["id"], ay_bas, now, turler=[UZAKTAN_ACMA_TUR])
    except Exception:   # noqa: BLE001
        uz_olaylar = []
    uz = len(uz_olaylar); uz_gunler = {o["baslangic"].astimezone(IST).date() for o in uz_olaylar if o.get("baslangic")}
    return {"bugun": bugun.isoformat(), "pencere_gun": gun, "segment": seg["segment"],
            "ayar": {"sayac_turu": pj.get("sayac_turu") if pj.get("sayac_turu") in SAYAC_TURLERI else None, "scada_durum": pj.get("scada_durum") if pj.get("scada_durum") in SCADA_DURUMLARI else None,
                     "scada_kopukluk_baslangic": pj.get("scada_kopukluk_baslangic") or None, "uzaktan_acma_var": pj.get("uzaktan_acma_var") if isinstance(pj.get("uzaktan_acma_var"), bool) else None,
                     "sistem_kullanim_bedeli_tl_ay": pj.get("sistem_kullanim_bedeli_tl_ay"),
                     "uzlastirma_girdi": dengesizlik_service.uretim_secimi(pj)},   # v2.526 (P4a-2)
            "uretim_secenekleri": [{"kod": k, "etiket": v} for k, v in dengesizlik_service.URETIM_SECENEKLERI.items()],
            "gelis": gelis(tenant_id, plant, pj, now), "fark": fark(tenant_id, plant, gun, bugun), "scada": scada_durumu(plant, pj, seg["segment"], bugun, uz, uz_gunler),
            "scada_notu": (None if seg["segment"] in LISANSSIZ else
                           "Segment seçilmedi (Santralim › Santral ayarları); SCADA yükümlülüğü belirlenemedi." if not seg["segment"] else
                           "Lisanslı santral: LÜY m.21(7) SCADA yükümlülüğü ve Karar 14909 bedel maddeleri lisanssız tesisler içindir; bu kart gösterilmez."),
            "yuklemeler": yuklemeler(tenant_id, plant["id"]),
            "kaynaklar": [{"kod": k, "etiket": KAYNAK_ETIKET[k]} for k in KAYNAKLAR], "nitelikler": [{"kod": n, "etiket": NITELIK_ETIKET[n]} for n in NITELIKLER],
            "sayac_turleri": [{"kod": k, "etiket": v} for k, v in SAYAC_TURLERI.items()], "scada_durumlari": [{"kod": k, "etiket": v} for k, v in SCADA_DURUMLARI.items()],
            "not": NOT}


def fark_csv(f: dict, plant_ad: str) -> str:
    """Günlük SCADA ↔ sayaç tablosu (; ayraç, BOM, Türkçe ondalık)."""
    out = io.StringIO(); out.write("﻿")
    out.write("santral;gun;scada_kwh;sayac_kwh;ortak_scada_kwh;ortak_sayac_kwh;fark_kwh;fark_pct;saat_scada;saat_sayac;saat_ortak;saat_tahmini\n")
    tr = lambda v: "" if v is None else str(v).replace(".", ",")   # noqa: E731
    for g in f["gunler"]:
        out.write(";".join([plant_ad, g["gun"], tr(g["scada_kwh"]), tr(g["sayac_kwh"]), tr(g["ortak_scada_kwh"]), tr(g["ortak_sayac_kwh"]), tr(g["fark_kwh"]), tr(g["fark_pct"]),
                            str(g["saat_scada"]), str(g["saat_sayac"]), str(g["saat_ortak"]), str(g["saat_tahmini"])]) + "\n")
    return out.getvalue()


def ay_saat(d: date) -> int:
    return monthrange(d.year, d.month)[1] * 24
