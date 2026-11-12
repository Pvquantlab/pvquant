"""v2.522 (P2b-1) — EPİAŞ uzlaştırma bildirimiyle kalem kalem mutabakat.

Müşteri EPYS «Uzlaştırma Bildirimi» ekranından indirdiği dosyayı (CSV ya da XLSX; 02-23: «Aylık Alacak Özet» / «Aylık Borç Özet»,
kolonlar «Uzlaştırma Kalemleri» ve «Tutar (TL)») yükler. Dosyanın gerçek kolon başlıkları BULUNAMADI (02-23 açık kalan) → kolonlar ve
kalemler ipuçlarıyla tanınır (v2.506 şablon öğrenme yaklaşımı); tanınmayan kalem «diğer» olarak adıyla saklanır, atılmaz.
PVQuant yalnız santral verisinden hesaplanabilen kalemleri yeniden hesaplar: enerji dengesizlik tutarı (EDT alacak/borç), KGÜP sapma tutarı
(KÜPST), lisanslı YEKDEM'de YEK alacağı (kaba: UEVM × YEK fiyatı − m.23(6) dışı). GÖP/GİP/DGP/GDDK/fark tutarı/SBDT/PİÜ/faiz/zam kalemleri
«santral verisinden hesaplanamaz» etiketiyle yalnız bildirimden gösterilir. Yeniden hesap EPİAŞ sonucu değildir; mutabakat farkı bilgi amaçlıdır.
"""
from __future__ import annotations

from pvquant.zaman import PIYASA_TZ

import calendar
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
SURUMLER = ("on", "nihai")
SURUM_ETIKET = {"on": "ön bildirim", "nihai": "nihai bildirim"}
# kod → etiket (EPYS ekranı adı), ipuçları (sadeleştirilmiş), PVQuant hesaplar mı, EPYS kalem kodu (02-23 ön yüz paketi)
KALEMLER = [
    ("dam",          "GÖP",                        ("gop", "gun oncesi", "dam"),                          False, "DAM"),
    ("idm",          "GİP",                        ("gip", "gun ici", "idm"),                             False, "IDM"),
    ("res",          "YEK",                        ("yek", "yekdem", "res"),                              True,  "RES"),
    ("imbalance",    "Dengesizlik",                ("dengesizlik", "imbalance"),                          True,  "IMBALANCE"),
    ("bpm",          "DGP",                        ("dgp", "dengeleme guc", "bpm"),                       False, "BPM"),
    ("retrospective", "GDDK",                      ("gddk", "geriye donuk", "gecmise donuk", "retrospective"),             False, "RETROSPECTIVE"),
    ("side_payment", "Fark tutarı",                ("fark tutar", "side payment", "side_payment"),        False, "SIDE_PAYMENT"),
    ("zero_balance", "SBDT",                       ("sbdt", "sifir bakiye", "zero balance", "zero_balance"), False, "ZERO_BALANCE_ADJUSTMENT"),
    ("mof",          "PİÜ",                        ("piu", "piyasa isletim", "mof"),                      False, "MOF"),
    ("kupst",        "KÜPST",                      ("kupst", "sapma tutar"),                              True,  "KUPST"),
    ("rbs",          "RBS (Kaynak Bazında Destekleme)",                        ("rbs",),                                              False, "RBS"),
    ("default_interest", "Temerrüt faizi",         ("temerrut", "default interest", "default_interest"),  False, "DEFAULT_INTEREST"),
    ("late_fee",     "Gecikme zammı",              ("gecikme zam", "late fee", "late_fee"),               False, "LATE_FEE"),
    ("refund_overdue_interest", "Ödenmeyen alacak iade faizi", ("iade faiz", "refund overdue", "refund_overdue"), False, "REFUND_OVERDUE_RECEIVABLES_INTEREST"),
    ("overdue",      "Ödenmeyen alacak",           ("odenmeyen alacak", "overdue"),                       False, "OVERDUE_RECEIVABLES"),
    ("summary",      "Toplam",                     ("toplam", "summary", "total", "net alacak", "net borc"), False, "SUMMARY"),
]
KALEM_ETIKET = {k[0]: k[1] for k in KALEMLER}
HESAPLANIR = {k[0] for k in KALEMLER if k[3]}
UYUM_PCT = 2.0      # PVQuant işletme ölçütü (mevzuat toleransı değil): kalemin alacak ve borç bileşenlerinin HER BİRİ için |fark| ≤ max(%2 × bildirim, 50 TL)
UYUM_TL = 50.0
UYUM_NOTU = ("Uyum ölçütü PVQuant'ın işletme ölçütüdür, mevzuatta bir tolerans değildir: kalemin alacak ve borç bileşenleri ayrı ayrı bakılır; her biri için "
             "|fark| bildirim tutarının %2'sini ya da 50 TL'yi (hangisi büyükse) aşmıyorsa «uyumlu». Net tutar eşleşse bile bileşenler sapıyorsa «fark var».")
DOGRULAMA = {"gercek": "tam", "kismi": "kismi", "senaryo": "senaryo", "veri_yok": "yok"}   # 02.11 inceleme: satır/özet hükmünün doğrulama niteliği
GUVENILIRLIK_ETIKET = {"gercek": "Gerçek verilerle karşılaştırma", "kismi": "Kısmi karşılaştırma", "senaryo": "Senaryo hesabı", "veri_yok": "Gerçek verilerle doğrulanamadı"}
SURUM_KAYNAGI = ("dosya", "kullanici", "varsayilan")
NOT = ("Mutabakat PVQuant'ın yeniden hesabı ile EPİAŞ bildirimini kalem kalem yan yana koyar; EPİAŞ sonucu esastır. Yalnız santral verisinden "
       "hesaplanabilen kalemler (DUY m.132/A(4) sınıflaması; pozisyonsuz tek santral varsayımı) (enerji dengesizlik tutarı, KGÜP sapma tutarı, lisanslı YEKDEM'de YEK alacağı) yeniden hesaplanır; GÖP, GİP, DGP, "
       "GDDK, fark tutarı, SBDT, PİÜ, faiz ve zam kalemleri yalnız bildirimden gösterilir. Fark kaynakları: program sürümü (bildirilen KGÜP yüklü "
       "değilse PVQuant önerisi), sayaç verisi (SCADA ≠ UEVM), fiyat kaynağı (senaryo saatleri), geçmişe dönük düzeltme kalemi (DUY m.134(1); «GDDK» kısaltması mevzuatta yok).")


def _sade(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().replace("İ", "i").replace("I", "ı").lower().translate(str.maketrans("çğıöşüâîû", "cgiosuaiu")))


def kalem_tani(ad: str) -> str:
    """Kalem adını EPYS kalem koduna eşler; eşleşmezse 'diger'. Önce uzun/özel ipuçları (ödenmeyen alacak iade faizi > ödenmeyen alacak)."""
    s = _sade(ad)
    if not s:
        return "diger"
    for kod, _et, ipuclari, _h, epys in KALEMLER:
        if s == epys.lower() or s == kod:
            return kod
    sira = ["refund_overdue_interest", "overdue", "default_interest", "late_fee", "zero_balance", "side_payment", "retrospective", "kupst",
            "imbalance", "res", "bpm", "mof", "dam", "idm", "rbs", "summary"]
    tablo = {k[0]: k[2] for k in KALEMLER}
    for kod in sira:
        if any(ip in s for ip in tablo[kod]):
            return kod
    return "diger"


def _sayi(v) -> float | None:
    """'1.234.567,89' / '1234567.89' / '-12,5' / '(12,5)' → float; boş ya da metin → None."""
    if v is None:
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    s = str(v).strip().replace("TL", "").replace("₺", "").strip()
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace(" ", "")
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})*(,\d+)?", s) or re.fullmatch(r"-?\d+(,\d+)?", s):
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})*(\.\d+)?", s) or re.fullmatch(r"-?\d+(\.\d+)?", s):
        s = s.replace(",", "")
    else:
        return None
    try:
        x = float(s)
    except ValueError:
        return None
    return -x if neg else x


def _satirlar(b: bytes) -> tuple[list[list[str]], str]:
    """CSV ya da XLSX → hücre matrisi (metin) ve biçim adı."""
    if b[:2] == b"PK":
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(b), read_only=True, data_only=True)
        out: list[list[str]] = []
        for ws in wb.worksheets:
            for r in ws.iter_rows(values_only=True, max_row=400):
                out.append([("" if c is None else (c if isinstance(c, (int, float)) else str(c))) for c in r])
        return out, "xlsx"
    metin = b.decode("utf-8-sig", errors="replace")
    hatlar = [h for h in metin.splitlines() if h.strip()]
    if not hatlar:
        return [], "csv"
    ornek = "\n".join(hatlar[:20])
    ayrac = max((";", ",", "\t", "|"), key=lambda a: ornek.count(a))
    import csv as _csv
    return [list(r) for r in _csv.reader(hatlar, delimiter=ayrac)], "csv"


_DONEM_RE = re.compile(r"\b(20\d{2})[-./](0[1-9]|1[0-2])\b|\b(0[1-9]|1[0-2])[-./](20\d{2})\b")
_TAM_TARIH_RE = re.compile(r"\b\d{1,2}[-./]\d{1,2}[-./]20\d{2}\b|\b20\d{2}[-./]\d{1,2}[-./]\d{1,2}\b")   # gün.ay.yıl (kesinleşme/çalışma tarihi) dönem değildir
_AYLAR = {"ocak": 1, "subat": 2, "mart": 3, "nisan": 4, "mayis": 5, "haziran": 6, "temmuz": 7, "agustos": 8, "eylul": 9, "ekim": 10, "kasim": 11, "aralik": 12}


def _donem_bul(satirlar) -> date | None:
    """«Fatura Dönemi» (aynı ya da komşu hücrede) → ay. Satır bütün olarak okunur (etiket ve değer ayrı hücrelerde olabilir); gün.ay.yıl biçimli
    tam tarihler (kesinleşme, çalışma tarihi) önce silinir; sonra ay.yıl / yıl-ay ya da ay adı + yıl aranır."""
    for r in satirlar[:40]:
        birlesik = " ".join(str(c) for c in r if c is not None and str(c).strip())
        s = _sade(birlesik)
        if not ("donem" in s or "period" in s or any(a in s for a in _AYLAR)):
            continue
        temiz = _TAM_TARIH_RE.sub(" ", birlesik)
        m = _DONEM_RE.search(temiz)
        if m:
            y, a = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
            return date(int(y), int(a), 1)
        st = _sade(_TAM_TARIH_RE.sub(" ", birlesik))
        for ad, n in _AYLAR.items():
            i = st.find(ad)
            if i >= 0:
                y = re.search(r"20\d{2}", st[i:]) or re.search(r"20\d{2}", st)
                if y:
                    return date(int(y.group(0)), n, 1)
    return None


def _surum_bul(satirlar) -> str | None:
    for r in satirlar[:40]:
        for c in r:
            s = _sade(c)
            if "nihai" in s or "final" in s:
                return "nihai"
            if "on uzlastirma" in s or "on bildirim" in s or "preliminary" in s:
                return "on"
    return None


def dosya_oku(b: bytes, dosya_adi: str = "") -> dict:
    """EPYS uzlaştırma bildirimi dosyasından kalemleri çıkarır. Tanıma: başlık satırında «kalem» ve «tutar» (ya da «alacak»/«borç») sütunları;
    yoksa her satırda ilk metin hücresi kalem adı, son sayısal hücre tutar. Yön: ayrı alacak/borç sütunları, «alacak/borç» tipli sütun,
    bölüm başlığı («Aylık Alacak Özet» / «Aylık Borç Özet») ya da işaret (eksi → borç). Dönüş: {kalemler, donem, surum, bicim, uyarilar, taninmayan}."""
    satirlar, bicim = _satirlar(b)
    if not satirlar:
        raise ValueError("dosya boş")
    uyar: list[str] = []
    kalemler: list[dict] = []
    yon_bolum: str | None = None
    kalem_i = tutar_i = alacak_i = borc_i = tip_i = None
    for r in satirlar:
        hucre = [c for c in r]
        sade = [_sade(c) for c in hucre]
        birlesik = " ".join(sade)
        # bölüm başlığı
        if "alacak ozet" in birlesik or ("alacak" in birlesik and "ozet" in birlesik and not any(_sayi(c) is not None for c in hucre)):
            yon_bolum = "alacak"
        if "borc ozet" in birlesik or ("borc" in birlesik and "ozet" in birlesik and not any(_sayi(c) is not None for c in hucre)):
            yon_bolum = "borc"
        # başlık satırı: kalem + tutar / alacak + borç sütunları
        if any("kalem" in s or "item" in s for s in sade) and any(("tutar" in s or "amount" in s or "alacak" in s or "borc" in s) for s in sade):
            kalem_i = next(i for i, s in enumerate(sade) if "kalem" in s or "item" in s)
            alacak_i = next((i for i, s in enumerate(sade) if "alacak" in s and "net" not in s and i != kalem_i), None)
            borc_i = next((i for i, s in enumerate(sade) if "borc" in s and "net" not in s and i != kalem_i), None)
            tutar_i = next((i for i, s in enumerate(sade) if ("tutar" in s or "amount" in s) and i != kalem_i), None)
            tip_i = next((i for i, s in enumerate(sade) if s in ("tip", "tur", "yon", "alacak/borc", "type")), None)
            continue
        # veri satırı
        if kalem_i is not None and kalem_i < len(hucre):
            ad = str(hucre[kalem_i]).strip()
            if not ad:
                continue
            if alacak_i is not None or borc_i is not None:
                for i, yon in ((alacak_i, "alacak"), (borc_i, "borc")):
                    if i is not None and i < len(hucre):
                        t = _sayi(hucre[i])
                        if t is not None and t != 0:
                            kalemler.append({"kalem_ad": ad, "kod": kalem_tani(ad), "yon": yon, "tutar_tl": abs(t)})
                continue
            t = _sayi(hucre[tutar_i]) if tutar_i is not None and tutar_i < len(hucre) else None
            if t is None:
                continue
            yon = None
            if tip_i is not None and tip_i < len(hucre):
                ts = sade[tip_i]; yon = "alacak" if "alacak" in ts or "credit" in ts else ("borc" if "borc" in ts or "debit" in ts else None)
            yon = yon or yon_bolum or ("borc" if t < 0 else "alacak")
            kalemler.append({"kalem_ad": ad, "kod": kalem_tani(ad), "yon": yon, "tutar_tl": abs(t)})
            continue
        # başlıksız: ilk metin hücresi + son sayı
        metinler = [(i, c) for i, c in enumerate(hucre) if isinstance(c, str) and c.strip() and _sayi(c) is None]
        sayilar = [(i, _sayi(c)) for i, c in enumerate(hucre) if _sayi(c) is not None]
        if metinler and sayilar and kalem_i is None:
            ad = metinler[0][1].strip(); t = sayilar[-1][1]
            if kalem_tani(ad) == "diger" and len(sayilar) > 1:
                continue   # tarih/sayı dolu satır; kalem satırı değil
            yon = yon_bolum or ("borc" if t < 0 else "alacak")
            kalemler.append({"kalem_ad": ad, "kod": kalem_tani(ad), "yon": yon, "tutar_tl": abs(t)})
    if not kalemler:
        raise ValueError("kalem satırı bulunamadı: dosyada «Uzlaştırma Kalemleri» ve «Tutar (TL)» sütunları ya da kalem adı + tutar satırları bekleniyor")
    if kalem_i is None:
        uyar.append("başlık satırı bulunamadı; kalem adı ve tutar satırlardan çıkarıldı")
    if not any(k["kod"] in HESAPLANIR for k in kalemler):
        uyar.append("dengesizlik, KÜPST ya da YEK kalemi tanınmadı; mutabakat yalnız bildirim tarafında kalır")
    taninmayan = sorted({k["kalem_ad"] for k in kalemler if k["kod"] == "diger"})
    if taninmayan:
        uyar.append(f"tanınmayan kalem(ler) «diğer» olarak saklandı: {', '.join(taninmayan[:6])}")
    return {"kalemler": kalemler, "donem": _donem_bul(satirlar), "surum": _surum_bul(satirlar), "bicim": bicim, "uyarilar": uyar, "taninmayan": taninmayan}


def _donem(v) -> date:
    if isinstance(v, date):
        return v.replace(day=1)
    s = str(v or "").strip()
    m = re.fullmatch(r"(20\d{2})-(0[1-9]|1[0-2])(-\d{2})?", s)
    if not m:
        raise ValueError("donem YYYY-MM olmalı")
    return date(int(m.group(1)), int(m.group(2)), 1)


def kaydet(tenant_id, plant: dict, b: bytes, dosya_adi: str, donem=None, surum: str | None = None, yukleyen=None) -> dict:
    """Dosyayı okur, kalemleri yeni yukleme_id ile saklar (önceki yüklemeler silinmez). donem/surum verilmezse dosyadan; yoksa 422."""
    if not b or len(b) > 2_000_000:
        raise ValueError("dosya boş ya da 2 MB'tan büyük")
    o = dosya_oku(b, dosya_adi)
    d = _donem(donem) if donem else o["donem"]
    if d is None:
        raise ValueError("dönem dosyadan okunamadı; dönemi (YYYY-MM) seçin")
    if o["donem"] is not None and donem and o["donem"] != d:
        raise ValueError(f"dosyadaki fatura dönemi ({o['donem'].strftime('%m.%Y')}) seçilen dönemle ({d.strftime('%m.%Y')}) uyuşmuyor")
    if d > datetime.now(IST).date().replace(day=1):
        raise ValueError("dönem gelecekte olamaz")
    if surum is not None and surum not in SURUMLER:
        raise ValueError("surum on ya da nihai olmalı")
    uyar = list(o["uyarilar"])
    if o["surum"]:   # dosyadaki «Uzlaştırma Durumu» esastır; kullanıcı seçimiyle çelişirse dosya kazanır, uyarı verilir
        s, kaynak_s = o["surum"], "dosya"
        if surum and surum != o["surum"]:
            uyar.append(f"dosyadaki uzlaştırma durumu «{SURUM_ETIKET[o['surum']]}»; seçilen «{SURUM_ETIKET[surum]}» yerine dosyadaki alındı")
    elif surum:
        s, kaynak_s = surum, "kullanici"
    else:
        s, kaynak_s = "nihai", "varsayilan"; uyar.append("dosyada uzlaştırma durumu okunamadı; sürüm «nihai bildirim» varsayıldı — gerekiyorsa ön bildirim olarak yeniden yükleyin")
    yid = str(uuid.uuid4()); sha = hashlib.sha256(b).hexdigest()
    try:
        yukleyen = str(uuid.UUID(str(yukleyen))) if yukleyen else None
    except ValueError:
        yukleyen = None
    with tenant_baglami(tenant_id) as se:
        for k in o["kalemler"]:
            se.execute(text("INSERT INTO uzlastirma_bildirimi(tenant_id, plant_id, donem, surum, yukleme_id, kalem, kalem_ad, yon, tutar_tl, dosya_adi, sha256, "
                            "dosya_donem, dosya_surum, surum_kaynagi, yukleyen) VALUES (:t, :p, :d, :s, :y, :k, :ka, :yo, :tu, :da, :sha, :dd, :ds, :sk, :yu)"),
                       {"t": tenant_id, "p": plant["id"], "d": d, "s": s, "y": yid, "k": k["kod"], "ka": k["kalem_ad"][:200], "yo": k["yon"], "tu": k["tutar_tl"],
                        "da": (dosya_adi or "")[:200], "sha": sha, "dd": o["donem"], "ds": o["surum"], "sk": kaynak_s, "yu": yukleyen})
    return {"yukleme_id": yid, "donem": d.isoformat()[:7], "surum": s, "surum_kaynagi": kaynak_s, "kalem_sayisi": len(o["kalemler"]), "bicim": o["bicim"], "sha256": sha,
            "uyarilar": uyar, "taninmayan": o["taninmayan"], "dosya_adi": dosya_adi,
            "surum_dogrulama": surum_dogrulama(d, s, datetime.now(timezone.utc))}


def surum_dogrulama(donem: date, surum: str, yukleme: datetime) -> dict:
    """Sürüm etiketi ile resmî takvimin (DUY m.132/A–B: ön bildirim izleyen ayın 11'i, nihai 15'i → iş günü) tutarlılığı. EPİAŞ'ın «Uzlaştırma
    Durumu» alanı dosyadan doğrulanamadığı için resmî durum her zaman «doğrulanmadı»; yükleme takvim tarihinden ÖNCEYSE etiket takvimle çelişir."""
    from pvquant.ext.turkiye import takvim as tk
    t = {o["kod"]: o for o in tk.donem_takvimi(donem.year, donem.month)}
    on = date.fromisoformat(t["on_bildirim"]["tarih"]); nihai = date.fromisoformat(t["nihai_bildirim"]["tarih"])
    beklenen = on if surum == "on" else nihai
    y = yukleme.astimezone(IST).date()
    once = y < beklenen
    return {"durum": "takvimden_once" if once else "takvim_uyumlu", "resmi_durum": "dogrulanmadi", "beklenen_tarih": beklenen.isoformat(),
            "on_bildirim": on.isoformat(), "nihai_bildirim": nihai.isoformat(), "itiraz_son": t["itiraz_son"]["tarih"] + " 17:30", "itiraz_60": t["itiraz_60"]["tarih"],
            "aciklama": (f"{SURUM_ETIKET[surum].capitalize()} resmî takvime göre en erken {beklenen.strftime('%d.%m.%Y')} tarihinde yayımlanır; yükleme {y.strftime('%d.%m.%Y')}. "
                         "Sürüm etiketi takvimle çelişiyor; EPİAŞ'ın uzlaştırma durumu doğrulanmadı." if once else
                         f"Yükleme ({y.strftime('%d.%m.%Y')}) {SURUM_ETIKET[surum]} takvim tarihinden ({beklenen.strftime('%d.%m.%Y')}) sonra. EPİAŞ'ın uzlaştırma durumu "
                         "dosyadan doğrulanmadı; etiket dosyadaki durum alanından ya da kullanıcı seçiminden gelir."),
            "kaynak": "DUY m.132/A(1), m.132/B(1), m.133 (Takvim sayfasıyla aynı hesap); 02-01/02-02 EPİAŞ duyuru düzeni"}


def donemler(tenant_id, plant_id) -> list[dict]:
    """Yükleme tarihçesi: her yükleme ayrı satır (dönem, sürüm, zaman, dosya, kalem sayısı, sürüm kaynağı, takvim doğrulaması); dönem + sürüm başına
    en yeni yükleme «geçerli» (hesaba giren), eskiler saklı."""
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text(
            "SELECT donem, surum, yukleme_id, max(olusturma) AS zaman, max(dosya_adi) AS dosya, max(sha256) AS sha, max(surum_kaynagi) AS sk, "
            "max(dosya_surum) AS ds, count(*) AS n FROM uzlastirma_bildirimi WHERE plant_id = :p GROUP BY donem, surum, yukleme_id "
            "ORDER BY donem DESC, zaman DESC"), {"p": plant_id}).fetchall()
    gecerli: set[tuple] = set(); out = []
    for r in rows:
        key = (r.donem, r.surum); ilk = key not in gecerli; gecerli.add(key)
        out.append({"donem": r.donem.isoformat()[:7], "surum": r.surum, "surum_etiket": SURUM_ETIKET[r.surum], "yukleme_id": str(r.yukleme_id),
                    "zaman": r.zaman.astimezone(IST).isoformat(timespec="minutes"), "dosya_adi": r.dosya, "sha256": r.sha, "kalem_sayisi": int(r.n),
                    "surum_kaynagi": r.sk, "dosya_surum": r.ds, "gecerli": ilk, "surum_dogrulama": surum_dogrulama(r.donem, r.surum, r.zaman)})
    return out


def bildirim(tenant_id, plant_id, donem: date, surum: str | None = None) -> dict | None:
    """Dönemin (istenen sürümün; yoksa nihai > ön) son yüklemesindeki kalemler."""
    with tenant_baglami(tenant_id) as s:
        son = s.execute(text("SELECT yukleme_id, surum, max(olusturma) AS z FROM uzlastirma_bildirimi WHERE plant_id = :p AND donem = :d "
                             + ("AND surum = :s " if surum else "") + "GROUP BY yukleme_id, surum ORDER BY (surum = 'nihai') DESC, z DESC LIMIT 1"),
                        {"p": plant_id, "d": donem, **({"s": surum} if surum else {})}).first()
        if son is None:
            return None
        rows = s.execute(text("SELECT kalem, kalem_ad, yon, tutar_tl, dosya_adi, sha256, surum_kaynagi, dosya_surum, olusturma FROM uzlastirma_bildirimi "
                              "WHERE yukleme_id = :y ORDER BY olusturma"), {"y": son.yukleme_id}).fetchall()
    return {"yukleme_id": str(son.yukleme_id), "surum": son.surum, "surum_etiket": SURUM_ETIKET[son.surum], "zaman": son.z.astimezone(IST).isoformat(timespec="minutes"),
            "dosya_adi": rows[0].dosya_adi if rows else None, "sha256": rows[0].sha256 if rows else None, "surum_kaynagi": rows[0].surum_kaynagi if rows else None,
            "dosya_surum": rows[0].dosya_surum if rows else None, "surum_dogrulama": surum_dogrulama(donem, son.surum, son.z),
            "kalemler": [{"kod": r.kalem, "kalem_ad": r.kalem_ad, "yon": r.yon, "tutar_tl": float(r.tutar_tl)} for r in rows]}


def pvquant_kalemleri(tenant_id, plant: dict, donem: date, bugun: date | None = None, uretim: str | None = None) -> dict:
    """Dönem için PVQuant yeniden hesabı (dengesizlik_service.dokum ile aynı girdiler): EDT alacak/borç, KÜPST, YEK alacağı (lisanslı YEKDEM, kaba).
    v2.526 (P4a-2): uretim scada | sayac (verilmezse santral ayarı uzlastirma_girdi); sayaçla hesapta SCADA'lı hesapla fark da verilir (kiyas)."""
    from pvquant.services import dengesizlik_service
    b = bugun or datetime.now(IST).date()
    gun = max(14, min(365, (b - donem).days + 1))
    uretim = uretim if uretim in dengesizlik_service.URETIM_SECENEKLERI else dengesizlik_service.uretim_secimi(plant.get("params_json"))
    try:
        df, ozet = dengesizlik_service.dokum(tenant_id, plant, gun=gun, uretim="sayac") if uretim == "sayac" else dengesizlik_service.dokum(tenant_id, plant, gun=gun)
    except Exception as e:   # noqa: BLE001
        return {"kalemler": {}, "saat": 0, "hata": str(e)[:200], "uretim_kaynak": {"secim": uretim}}
    beklenen = calendar.monthrange(donem.year, donem.month)[1] * 24
    bos = {"kalemler": {}, "saat": 0, "beklenen_saat": beklenen, "guvenilirlik": {"durum": "veri_yok", "etiket": GUVENILIRLIK_ETIKET["veri_yok"],
           "nedenler": ["dönem için saatlik üretim ve program verisi yok"]}}
    if df is None or df.empty:
        return bos
    ay = donem.strftime("%Y-%m")
    maske = df["zaman"].str.startswith(ay); x = df[maske]
    if x.empty:
        return bos
    ok = x["durum"].eq("ok")
    kaynaklar = ozet.get("saat_fiyat_kaynak") if isinstance(ozet, dict) else None
    if kaynaklar is not None and len(kaynaklar) == len(df):
        senaryo_saat = int(sum(1 for k, m in zip(kaynaklar, maske.values) if m and k == "senaryo")); senaryo_kapsam = "donem"
    else:   # eski döküm: yalnız pencere düzeyinde biliniyor
        senaryo_saat = int((ozet.get("fiyat", {}) or {}).get("senaryo_saat", 0) or 0) if isinstance(ozet, dict) else 0; senaryo_kapsam = "pencere"
    bildirilen = int((x["program_kaynak"] == "bildirilen").sum()); saat = int(len(x)); hes_yok = int((~ok).sum())
    nedenler = []; durum = "gercek"
    if senaryo_saat > 0:
        durum = "senaryo"; nedenler.append(f"{senaryo_saat} saatte EPİAŞ fiyatı yerine senaryo fiyatı" + (" (hesap penceresinde)" if senaryo_kapsam == "pencere" else "") + "; sistem yönü dengede varsayıldı")
    if saat < beklenen:
        durum = durum if durum == "senaryo" else "kismi"; nedenler.append(f"dönemin {beklenen} saatinden {saat} saati için üretim ve program verisi var (son veri {x['zaman'].max()[:16]})")
    if bildirilen < saat:
        durum = durum if durum == "senaryo" else "kismi"; nedenler.append(f"{saat - bildirilen} saatte bildirilen KGÜP yok, PVQuant önerisi kullanıldı")
    if hes_yok:
        durum = durum if durum == "senaryo" else "kismi"; nedenler.append(f"{hes_yok} saat hesaplanamadı (sistem yönü ya da katsayı eksik)")
    edt_borc = float(pd.to_numeric(x["edt_borc_tl"], errors="coerce").fillna(0).sum()); edt_alacak = float(pd.to_numeric(x["edt_alacak_tl"], errors="coerce").fillna(0).sum())
    kupst_s = pd.to_numeric(x["kupst_tl"], errors="coerce")
    out = {"imbalance": {"alacak_tl": round(edt_alacak, 2), "borc_tl": round(edt_borc, 2), "not": "saatlik EDT toplamı (alacak: fazla üretim; borç: eksik üretim)"},
           "kupst": {"alacak_tl": 0.0, "borc_tl": (round(float(kupst_s.sum()), 2) if kupst_s.notna().any() and not kupst_s.isna().all() else None),
                     "not": "KÜPSM × max(taban; PTF; SMF) × n" if kupst_s.notna().any() else "KÜPST hesaplanamadı (segment/katsayı yok)",
                     "dayanak": "KÜPST yalnız borç kalemidir: DUY m.110(4) ve m.113(2) (RG 19.10.2026-33405); katsayılar Karar 14907 (RG 19.10.2026-33405)",
                     "katsayi_kaynagi": (ozet.get("katsayilar") or {}).get("kupst_kaynak")}}   # v2.535 (DK-229); v2.541: katsayı kaynağı (kural tablosu | santral ayarı)
    if "yek_fiyat_tl_mwh" in x.columns:
        yf = pd.to_numeric(x["yek_fiyat_tl_mwh"], errors="coerce"); g = pd.to_numeric(x["gerceklesen_mwh"], errors="coerce").fillna(0)
        disi = pd.to_numeric(x.get("yekdem_disi_tl", 0), errors="coerce").fillna(0)
        if yf.notna().any():
            out["res"] = {"alacak_tl": round(float((g * yf.fillna(0)).sum() - disi.sum()), 2), "borc_tl": 0.0,
                          "not": "kaba: gerçekleşen MWh × günün YEK fiyatı − m.23(6) dışı tutar; EPİAŞ YEKBED kalemleri (ÖYO/ÖYT, KB) hesaplanmaz", "kaba": True}
    sayac = _sayac_kapsami(tenant_id, plant, donem)   # v2.523 (P4a): dönemin sayaç kapsamı ve SCADA ile farkı
    # v2.526 (P4a-2): üretim kaynağı — dönem saatlerinde kaç saat sayaç (ölçülmüş / tahmini), kaç saat SCADA; sayaçla hesapta SCADA'lı hesapla fark
    uk = {"secim": uretim, "etiket": dengesizlik_service.URETIM_SECENEKLERI[uretim], "sayac_olculmus_saat": 0, "sayac_tahmini_saat": 0, "scada_saat": saat, "kiyas": None}
    suk = ozet.get("saat_uretim_kaynak") if isinstance(ozet, dict) else None
    if suk is not None and len(suk) == len(df):
        don = [k for k, m in zip(suk, maske.values) if m]
        uk["sayac_olculmus_saat"] = sum(1 for k in don if k == "sayac_olculmus"); uk["sayac_tahmini_saat"] = sum(1 for k in don if k == "sayac_tahmini")
        uk["scada_saat"] = saat - uk["sayac_olculmus_saat"] - uk["sayac_tahmini_saat"]
    if uretim == "sayac":
        sy_saat = uk["sayac_olculmus_saat"] + uk["sayac_tahmini_saat"]
        # 02.11 inceleme: yüklü sayaç saatlerinin hesaba giremeyeni (SCADA satırı yok ya da hesap penceresi dışı) sessizce kaybolmaz, sayılır
        uk["sayac_kullanilmayan_saat"] = max(0, int(sayac["yuklu"]) - sy_saat) if (sayac and sayac.get("yuklu")) else 0
        if uk["sayac_kullanilmayan_saat"]:
            nedenler.append(f"yüklü {sayac['yuklu']} sayaç saatinden {uk['sayac_kullanilmayan_saat']} saat hesaba girmedi (o saatte SCADA satırı yok; program ve fiyat satırı SCADA'dan kurulur)")
        if sy_saat == 0:
            nedenler.append("üretim girdisi «sayaç» seçili ama dönem saatlerinde sayaç verisi yok; hesap SCADA ile yapıldı")
        else:
            durum = durum if durum == "senaryo" else ("kismi" if (uk["sayac_tahmini_saat"] or uk["scada_saat"]) else durum)
            nedenler.append(f"hesap {sy_saat} saatte sayaç verisiyle ({uk['sayac_olculmus_saat']} ölçülmüş, {uk['sayac_tahmini_saat']} tahmini nitelikli)"
                            + (f", {uk['scada_saat']} saatte SCADA" if uk["scada_saat"] else "") + "; sayaç dosyasının uzlaştırmaya esas UEVM ile aynı olduğu doğrulanmaz")
            try:   # aynı dönem SCADA ile: EDT net ve KÜPST farkı (sayaç − SCADA) — sayaç farkının uzlaştırmaya yansıması
                dfs, _ = dengesizlik_service.dokum(tenant_id, plant, gun=gun)
                xs = dfs[dfs["zaman"].str.startswith(ay)] if dfs is not None and not dfs.empty else None
                if xs is not None and not xs.empty:
                    en = lambda f: float(pd.to_numeric(f["edt_alacak_tl"], errors="coerce").fillna(0).sum() - pd.to_numeric(f["edt_borc_tl"], errors="coerce").fillna(0).sum())   # noqa: E731
                    ku = lambda f: float(pd.to_numeric(f["kupst_tl"], errors="coerce").fillna(0).sum())   # noqa: E731
                    uk["kiyas"] = {"edt_net_fark_tl": round(en(x) - en(xs), 2), "kupst_fark_tl": round(ku(x) - ku(xs), 2), "scada_saat": int(len(xs)),
                                   "not": "sayaçla hesap − SCADA ile hesap (aynı dönem, aynı program ve fiyat); dengesizlik netinde artı sayaçla daha lehte, KÜPST borcunda artı daha aleyhte"}
            except Exception as e:   # noqa: BLE001 — kıyas alınamazsa hesap sonucu etkilenmez
                uk["kiyas"] = {"hata": str(e)[:120]}
    elif sayac and sayac.get("yuklu"):
        nedenler.append(f"sayaç verisi {sayac['yuklu']}/{sayac['toplam_saat']} saat ({sayac['olculmus']} ölçülmüş)" + (f"; ölçülmüş saatlerde sayaç − SCADA {sayac['olc_fark_pct']:+.1f} %" if sayac.get("olc_fark_pct") is not None else "")
                        + "; hesap SCADA ile yapıldı (Sayaç › uzlaştırma girdisi ayarıyla sayaç seçilebilir), uzlaştırmaya esas sayaç (UEVM) değildir")
    return {"kalemler": out, "saat": saat, "beklenen_saat": beklenen, "son_saat": x["zaman"].max(), "hesaplanamayan_saat": hes_yok, "bildirilen_saat": bildirilen,
            "senaryo_saat": senaryo_saat, "senaryo_kapsam": senaryo_kapsam, "kural_surumu": " | ".join(sorted(set(x["kural_surumu"].astype(str)))),
            "kupst_kaynak": (ozet.get("katsayilar") or {}).get("kupst_kaynak"), "kupst_gecersiz_kilma": bool((ozet.get("katsayilar") or {}).get("kupst_gecersiz_kilma")),   # v2.541
            "sayac": sayac, "uretim_kaynak": uk, "guvenilirlik": {"durum": durum, "etiket": GUVENILIRLIK_ETIKET[durum], "nedenler": nedenler}}


def _sayac_kapsami(tenant_id, plant: dict, donem: date) -> dict | None:
    """v2.523 (P4a): dönem için yüklü sayaç saatleri (ölçülmüş / tahmini) ve ölçülmüş saatlerde SCADA ile fark. Tablo yoksa None; hesaba girmez."""
    try:
        from pvquant.services import sayac_service
        bas = datetime.combine(donem, datetime.min.time(), tzinfo=IST); bit = datetime.combine(ay_sonu := _ay_ekle(donem), datetime.min.time(), tzinfo=IST)
        sy = sayac_service.sayac_oku(tenant_id, plant["id"], bas, bit)
        toplam = int((bit - bas).total_seconds() // 3600)
        if sy.empty:
            return {"toplam_saat": toplam, "yuklu": 0, "olculmus": 0, "tahmini": 0, "olc_fark_pct": None}
        sc = sayac_service.scada_oku(tenant_id, plant["id"], bas, bit)
        j = sayac_service._birlestir(sc, sy)
        t = int(sy["nitelik"].isin(["tahmini", "doldurulmus", "yok"]).sum())
        olc = sayac_service._kiyas(float(j["olc_scada"].sum()), float(j["olc_sayac"].sum()), int(j["olculmus"].sum())) if (not j.empty and j["olculmus"].any()) else None
        del ay_sonu
        return {"toplam_saat": toplam, "yuklu": int(len(sy)), "olculmus": int(len(sy)) - t, "tahmini": t, "olc_fark_pct": (olc["fark_pct"] if olc else None)}
    except Exception:   # noqa: BLE001 — sayaç tablosu yoksa (eski DB) mutabakat etkilenmez
        return None


ITIRAZ_DAYANAK = ("DUY m.133(1): fatura itirazı tebliğden itibaren 60 gün içinde yazılı; m.133(3)(a)–(b): ölçüm değerlerine itirazı TEİAŞ/dağıtım şirketi 15 gün içinde "
                  "sonuçlandırır, EPİAŞ bildirilen sonucu 5 iş günü içinde işler; m.133(4)(b): ölçüm dışı itirazlar 20 iş günü; m.133(5) (RG 29.12.2025-33122, "
                  "01.01.2026): 60 gün içinde yapılmayan ve başvuru tarihi itibarıyla en fazla 12 ay önceki fatura dönemine ait itirazlar, başvuruyu izleyen 3 ay "
                  "içinde sonuçlandırılır; düzeltme sonraki faturaya GDDK kalemi olarak yansır (m.133(7), m.134(1)). Lisanssız üretici: GTŞ/toplayıcı işlemine "
                  "bildirimden itibaren 3 iş günü içinde itiraz, 5 iş günü içinde inceleme (LÜY m.27).")   # v2.538 (EK-3 DK-557/DK-395, kanıt A)


def _gun_tr(iso: str) -> str:
    """YYYY-MM-DD → GG.AA.YYYY (v2.538; görünen metinde ISO tarih yok)."""
    return ".".join(reversed(iso[:10].split("-")))


def itiraz_takvimi(donem: date, segment: str | None, bugun: date | None = None) -> dict:
    """v2.538 (EK-3 DK-557/DK-395): dönemin itiraz süreleri — ön bildirime itiraz (m.132/B(1)), faturaya 60 gün (m.133(1)), geriye dönük 12 ay penceresi
    (m.133(5); «başvuru tarihi itibarıyla en fazla 12 ay önceki fatura dönemi» → bu dönem için son başvuru = dönem + 12 ay sonu, sayım yöntemi metinde yok:
    çıkarım), inceleme süreleri (ölçüm 15 gün + 5 iş günü; ölçüm dışı 20 iş günü; geriye dönük 3 ay). Lisanssızda muhatap GTŞ/toplayıcı (LÜY m.27)."""
    from pvquant.ext.turkiye import takvim as tk
    d = donem.replace(day=1); b = bugun or datetime.now(IST).date()
    t = {o["kod"]: o for o in tk.donem_takvimi(d.year, d.month)}
    import calendar
    y, m = d.year + (d.month - 1 + 12) // 12, (d.month - 1 + 12) % 12 + 1
    gd_son = date(y, m, calendar.monthrange(y, m)[1])
    lisanssiz = segment in ("lisanssiz_dagitim", "lisanssiz_iletim")
    out = {"donem": d.strftime("%Y-%m"), "on_bildirim_itiraz_son": t["itiraz_son"]["tarih"] + " 17:30", "fatura_itiraz_60_gun": t["itiraz_60"]["tarih"],
           "geriye_donuk": {"pencere_ay": 12, "son_basvuru": gd_son.isoformat(), "gecti": b > gd_son, "kalan_gun": (gd_son - b).days, "sonuc_ay": 3, "kesinlik": "cikarim",
                            "not": "Başvuru tarihi itibarıyla en fazla 12 ay önceki fatura dönemine ait itiraz başvuruları başvuruyu izleyen 3 ay içinde sonuçlandırılır (DUY m.133(5)); "
                                   "bu dönem için son başvuru günü dönem + 12 ayın son günü olarak hesaplandı (sayım yöntemi metinde yok — çıkarım). Düzeltme GDDK kalemiyle sonraki faturaya yansır."},
           "inceleme": {"olcum_teias_dagitim_gun": 15, "olcum_epias_is_gunu": 5, "olcum_disi_is_gunu": 20, "dayanak": "DUY m.133(3)(a)–(b), m.133(4)(b)"},
           "lisanssiz": ({"itiraz_is_gunu": 3, "inceleme_is_gunu": 5, "muhatap": "görevli tedarik şirketi / toplayıcı", "dayanak": "LÜY m.27",
                          "not": "Lisanssız tesis EPİAŞ uzlaştırma bildiriminin tarafı değildir; itiraz GTŞ/toplayıcının ödeme işlemine, bildirimden itibaren 3 iş günü içinde yapılır."} if lisanssiz else None),
           "dayanak": ITIRAZ_DAYANAK}
    return out


def _ay_ekle(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def mutabakat(tenant_id, plant: dict, donem, surum: str | None = None, bugun: date | None = None, uretim: str | None = None) -> dict:
    """Kalem tablosu: bildirim (alacak/borç) ↔ PVQuant; fark ve durum (uyumlu / fark / hesaplanamaz / bildirimde_yok / hesap_yok). v2.526: uretim scada | sayac."""
    d = _donem(donem)
    bil = bildirim(tenant_id, plant["id"], d, surum)
    pv = pvquant_kalemleri(tenant_id, plant, d, bugun, uretim)
    guven = pv.get("guvenilirlik") or {"durum": "veri_yok", "etiket": GUVENILIRLIK_ETIKET["veri_yok"], "nedenler": []}
    bil_k: dict[str, dict] = {}
    for k in (bil or {}).get("kalemler", []):
        e = bil_k.setdefault(k["kod"] if k["kod"] != "diger" else f"diger:{k['kalem_ad']}", {"alacak_tl": 0.0, "borc_tl": 0.0, "kalem_ad": k["kalem_ad"]})
        e["alacak_tl" if k["yon"] == "alacak" else "borc_tl"] += k["tutar_tl"]
    satirlar = []
    kodlar = [k[0] for k in KALEMLER] + [k for k in bil_k if k.startswith("diger:")]
    for kod in kodlar:
        b = bil_k.get(kod); p = pv["kalemler"].get(kod)
        if b is None and p is None:
            continue
        etiket = KALEM_ETIKET.get(kod) or (b or {}).get("kalem_ad") or kod
        hesaplanir = kod in HESAPLANIR
        satir = {"kod": kod, "etiket": etiket, "hesaplanir": hesaplanir, "kalem_ad": (b or {}).get("kalem_ad"),
                 "bildirim_alacak_tl": (round(b["alacak_tl"], 2) if b else None), "bildirim_borc_tl": (round(b["borc_tl"], 2) if b else None),
                 "pvquant_alacak_tl": (p.get("alacak_tl") if p else None), "pvquant_borc_tl": (p.get("borc_tl") if p else None),
                 "pvquant_not": (p or {}).get("not"), "kaba": bool((p or {}).get("kaba"))}
        satir["dogrulama"] = None
        if not hesaplanir:
            satir.update({"fark_tl": None, "fark_pct": None, "durum": "hesaplanamaz"})
        elif b is None:
            satir.update({"fark_tl": None, "fark_pct": None, "durum": "bildirimde_yok"})
        elif p is None or (p.get("alacak_tl") is None and p.get("borc_tl") is None) or (kod == "kupst" and p.get("borc_tl") is None):
            satir.update({"fark_tl": None, "fark_pct": None, "durum": "hesap_yok"})
        else:
            # bileşen bazlı karşılaştırma: alacak ve borç ayrı ayrı (net eşleşse bile bileşenler sapabilir); fark = PVQuant − bildirim
            ba, bb = (b["alacak_tl"] or 0.0), (b["borc_tl"] or 0.0); pa, pb = (p.get("alacak_tl") or 0.0), (p.get("borc_tl") or 0.0)
            fa, fb = pa - ba, pb - bb; net_b = ba - bb; fark = (pa - pb) - net_b; taban = abs(net_b)
            esik = lambda x: max(UYUM_TL, abs(x) * UYUM_PCT / 100)   # noqa: E731
            uyumlu = abs(fa) <= esik(ba) and abs(fb) <= esik(bb)
            durum = "senaryo" if guven["durum"] == "senaryo" else ("hesap_yok" if guven["durum"] == "veri_yok" else ("uyumlu" if uyumlu else "fark"))
            # 02.11 inceleme: «uyumlu / fark var» hükmü yalnız gerçek verilerle (tam ay, EPİAŞ fiyatı, bildirilen KGÜP) doğrulanmış sayılır;
            # kısmi kapsamda hüküm korunur ama «kısmi» nitelikli — EPİAŞ tutarı bütün ayı, PVQuant tutarı yalnız hesaplanan saatleri kapsar
            satir.update({"fark_tl": round(fark, 2), "fark_pct": (round(100 * fark / taban, 1) if taban > 0 else None),
                          "fark_alacak_tl": round(fa, 2), "fark_borc_tl": round(fb, 2), "durum": durum, "dogrulama": DOGRULAMA.get(guven["durum"]),
                          "bilesen_notu": ("net tutar eşleşiyor ama alacak ve borç bileşenleri ayrı ayrı sapıyor" if (not uyumlu and abs(fark) <= esik(net_b)) else None)})
        satirlar.append(satir)
    hes = [s for s in satirlar if s["hesaplanir"]]
    kiyas = [s for s in hes if s["durum"] in ("uyumlu", "fark", "senaryo")]
    ozet = {"bildirim_alacak_tl": round(sum((s["bildirim_alacak_tl"] or 0) for s in satirlar if s["kod"] != "summary"), 2) if bil else None,
            "bildirim_borc_tl": round(sum((s["bildirim_borc_tl"] or 0) for s in satirlar if s["kod"] != "summary"), 2) if bil else None,
            # aynı kapsam: yalnız karşılaştırılan kalemlerin bildirim ve PVQuant tutarları (toplamlar farklı kapsamla yan yana konmaz)
            "bildirim_kiyas_alacak_tl": round(sum((s["bildirim_alacak_tl"] or 0) for s in kiyas), 2) if kiyas else None,
            "bildirim_kiyas_borc_tl": round(sum((s["bildirim_borc_tl"] or 0) for s in kiyas), 2) if kiyas else None,
            "bildirim_kiyas_net_tl": round(sum(((s["bildirim_alacak_tl"] or 0) - (s["bildirim_borc_tl"] or 0)) for s in kiyas), 2) if kiyas else None,
            "pvquant_alacak_tl": round(sum((s["pvquant_alacak_tl"] or 0) for s in kiyas), 2) if kiyas else None,
            "pvquant_borc_tl": round(sum((s["pvquant_borc_tl"] or 0) for s in kiyas), 2) if kiyas else None,
            "pvquant_net_tl": round(sum(((s["pvquant_alacak_tl"] or 0) - (s["pvquant_borc_tl"] or 0)) for s in kiyas), 2) if kiyas else None,
            "fark_tl": round(sum((s["fark_tl"] or 0) for s in kiyas), 2) if kiyas else None,
            "uyumlu": sum(1 for s in hes if s["durum"] == "uyumlu"), "farkli": sum(1 for s in hes if s["durum"] == "fark"),
            "senaryo": sum(1 for s in hes if s["durum"] == "senaryo"), "kiyaslanan": len(kiyas),
            "kapsam": ", ".join(s["etiket"] for s in kiyas) or None,
            "dogrulama": DOGRULAMA.get(guven["durum"]), "kapsam_saat": int(pv.get("saat") or 0), "beklenen_saat": pv.get("beklenen_saat")}   # 02.11 inceleme
    sd = (bil or {}).get("surum_dogrulama")
    kismi_on = (f"Kapsam kısmi ({ozet['kapsam_saat']}/{ozet['beklenen_saat']} saat; {'; '.join(guven['nedenler'])}): EPİAŞ tutarı bütün ayı, PVQuant tutarı yalnız hesaplanan "
                "saatleri kapsar; fark doğrulanmış sayılmaz — eksik saatleri (SCADA/sayaç) ve bildirilen KGÜP'ü tamamlayıp yeniden bakın. " if guven["durum"] == "kismi" else "")
    from pvquant.services import saatlik_detay_service
    saatlik = saatlik_detay_service.ozet_kisa(tenant_id, plant, d, uretim, bugun)   # v2.527 (P2b-2): yüklüyse eş kapsamlı kıyas özeti
    from pvquant.services import dengesizlik_service as _dz
    itiraz = itiraz_takvimi(d, _dz.segment_bilgisi(plant.get("params_json")).get("segment"), bugun)   # v2.538 (DK-557/DK-395)
    es = ""
    if saatlik and saatlik.get("yuklu") and saatlik.get("ortak_saat") and saatlik.get("toplam") and saatlik["toplam"].get("edt_net_fark_tl") is not None:
        t = saatlik["toplam"]; es = (f"Eş kapsamlı kıyas (EPYS saatlik detayı, ortak {saatlik['ortak_saat']} saat): dengesizlik neti EPİAŞ {t['edt_net_epias_tl']:,.2f} TL, "
                                      f"PVQuant {t['edt_net_pvquant_tl']:,.2f} TL, fark {t['edt_net_fark_tl']:+,.2f} TL — ayrıntı «Saatlik detay kıyası» kartında. ").replace(",", "X").replace(".", ",").replace("X", ".")
    if ozet["farkli"]:
        eylem = kismi_on + ("Fark var: EPYS'deki saatlik detaylarla (dengesizlik uzlaştırma, KÜPST detay) ve PVQuant dökümüyle saat bazında karşılaştırın; program sürümü, sayaç (UEVM ≠ SCADA) "
                 "ve fiyat kaynağı en sık nedenlerdir. İtiraz: ön bildirime " + (_gun_tr(sd["itiraz_son"][:10]) + " " + sd["itiraz_son"][11:] if sd else "izleyen ayın 12'si 17:30") + "'a kadar (DUY m.132/B(1)), "
                 "faturaya tebliğden itibaren 60 gün yazılı (m.133(1); " + (_gun_tr(sd["itiraz_60"]) if sd else "takvim") + "); süreler «İtiraz süreleri» alanında.")   # v2.538: gün.ay.yıl
    elif ozet["senaryo"]:
        eylem = "Senaryo hesabı: EPİAŞ fiyat verisi bağlanmadan mutabakat sonucu çıkarılamaz; farklar bilgi amaçlıdır."
    elif ozet["kiyaslanan"]:
        eylem = ("Karşılaştırılan kalemler uyum ölçütü içinde" + ("; ancak kapsam kısmi, uyum tam ay verisiyle kesinleşir" if guven["durum"] == "kismi" else "; işlem gerekmez")
                 + ". Yalnız bildirimden gelen kalemleri EPYS'de kontrol edin.")
    else:
        eylem = None
    if es:   # eş kapsamlı kıyas bildirim olmasa da anlamlıdır; kapsam notundan SONRA gelir (aylık tablo kısmi, saatlik kıyas eş kapsamlı)
        eylem = (kismi_on + es + eylem[len(kismi_on):]) if (eylem and kismi_on and eylem.startswith(kismi_on)) else es + (eylem or "")
    return {"donem": d.isoformat()[:7], "donem_etiket": d.strftime("%m.%Y"), "bildirim": ({k: v for k, v in bil.items() if k != "kalemler"} if bil else None),
            "satirlar": satirlar, "ozet": ozet, "uyum": {"pct": UYUM_PCT, "tl": UYUM_TL, "not": UYUM_NOTU}, "guvenilirlik": guven, "eylem": eylem,
            "pvquant": {k: v for k, v in pv.items() if k != "kalemler"}, "saatlik_detay": saatlik, "not": NOT, "itiraz": itiraz,
            "program_notu": ("bildirilen KGÜP yüklü saat yok: hesap PVQuant önerisiyle; mutabakat için bildirilen programı yükleyin (Tahminler › bildirilen KGÜP)"
                             if pv.get("saat") and not pv.get("bildirilen_saat") else None)}


def ozet(tenant_id, plant: dict, donem=None, surum: str | None = None, bugun: date | None = None, uretim: str | None = None) -> dict:
    """Müşteri ucu: dönem listesi + seçilen dönemin (varsayılan: son yüklenen, yoksa önceki ay) mutabakatı. v2.526: uretim seçimi ve seçenekleri."""
    from pvquant.services import dengesizlik_service
    b = bugun or datetime.now(IST).date()
    liste = donemler(tenant_id, plant["id"])
    if donem is None:
        donem = liste[0]["donem"] if liste else (b.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    m = mutabakat(tenant_id, plant, donem, surum, b, uretim)
    return {"bugun": b.isoformat(), "donemler": liste, "secili": m, "surumler": [{"kod": s, "etiket": SURUM_ETIKET[s]} for s in SURUMLER],
            "uretim_ayari": dengesizlik_service.uretim_secimi(plant.get("params_json")),
            "uretim_secenekleri": [{"kod": k, "etiket": v} for k, v in dengesizlik_service.URETIM_SECENEKLERI.items()],
            "guvenilirlik_etiketleri": GUVENILIRLIK_ETIKET,
            "kalemler": [{"kod": k[0], "etiket": k[1], "hesaplanir": k[3], "epys": k[4]} for k in KALEMLER]}
