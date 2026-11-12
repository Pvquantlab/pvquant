"""v2.520 (P5a) — YEKDEM fiyat katmanı: iki fiyat rejimi, gün bazlı YEK fiyatı serisi, 7189 USD bandı, YEK Yön. m.23(6) saat işareti.

Rejim (işletmeye giriş tarihinden türetilir; Santral ayarları › Satış tarifesi'nde elle de seçilir):
  cetvel1 — 30.6.2021'e kadar işletmeye girenler: 5346 sayılı Kanun I sayılı Cetvel, güneş 13,3 ABD senti/kWh (II sayılı Cetvel yerli
            katkı, işletmeye girişten 5 yıl). TL karşılığı enerjinin sisteme verildiği günün TCMB döviz alış kuruyla (5346 m.3(1)(16);
            YEK Yön. m.3(1)(dd)) — kur_service günlük arşivi; tatil günü uygulaması BULUNAMADI → önceki iş günü kuru, işaretli.
  7189    — 1.7.2021–31.12.2030 arasında işletmeye girenler: 7189 sayılı CK (RG 1.5.2023-32177) Ek-1 güneş 106,00 TL kr/kWh başlangıç,
            10 yıl; yerli katkı 28,80 kr/kWh, 5 yıl; bütünleşik depolamalı 125,00 kr (yerli 38,45, 10 yıl). Ek-2: aylık güncelleme
            (%25 ÜFE, %15 TÜFE, %30 USD, %30 Avro); hesaplanan TL fiyat bir önceki ayın günlük USD alış kuru ortalamasıyla ¢/kWh'a
            çevrilip 4,95–6,05 (depolamalı 5,85–7,15) bandına kırpılır. Kapsam notu (v2.537): yalnız «bütünleşik depolamalı» türü
            fiyat/band seçiminde tanınır; 6446 m.7(10)-(11) depolamalı tesis, m.8(11) 1/5/2023 sınırı, sanal kayıt ve YEK Yön. m.8(10)/(13) dışlamaları modellenmedi. EPİAŞ her ay ilan eder (yekdem_fiyat; Ağustos–Ekim 2026 tohum,
            EPİAŞ 01.10.2026 duyurusu). PVQuant formülü yeniden hesaplamaz: ilanı kullanır, band konumunu kurla gösterir.
  31.12.2030 sonrası işletmeye giriş: fiyat kararı yok → «belirsiz».
  Süre sınırı (v2.532; 03.11.2026 doğrulama arşivi DK-287/DK-285, kanıt A): Cetvel I fiyatı son yararlanma yılının sonuna kadar (takvim.yekdem_suresi:
  Karar 5905-27 grubu / CK 2949 / kullanıcı başlangıç yılı); 7189 fiyatı işletmeye girişten 10 yıl. Sonrası fiyat yok (kaynak «sure_doldu»).
m.23(6) (YEK Yön., RG 19.10.2026-33405): acil durum/YAT talimatı verilen ya da (PTF veya SMF < V ve sistem yönü enerji fazlası) saatlerde
KGÜP'ün üstündeki üretim, PTF < YEK fiyatı (+ yerli katkı) ise YEKDEM dışında kalır; KGÜP bildirilmemişse KGÜP = 0. EPİAŞ'ın uygulaması
(ilk fatura dönemi ve EPİAŞ hesap kalemi) BULUNAMADI; dönem bazı ve DGP başlangıcındaki KGÜP sürümü metinden okunur → işaret «belirsiz» etiketlidir; talimat saatleri (veri yok) dâhil değil.
Bildirilen KGÜP dosyası yüklenmemiş saatte PVQuant önerisi program sayılır (dosya yüklenmedi ≠ EPİAŞ'a bildirilmedi); v2.532 (DK-301, kanıt A):
o saatler için mevzuat okuması (KGÜP = 0 → üretimin tamamı dışarıda) ayrıca kgup0_mwh / kgup0_tl sütunlarında ve özette verilir.
YEKDEM dışı kalan MWh için fark = YEK fiyatı − j × PTF (j = 0,980, güneş; Karar 7667): YEKDEM içinde kalsaydı YEK fiyatı alır, PTF × j
öderdi (YEK Yön. m.18/1). Hesap çekirdeği (ext/turkiye/dengesizlik.py) değişmez; bu modül yalnız fiyat ve işaret üretir.
"""
from __future__ import annotations

from pvquant.zaman import PIYASA_TZ

import json
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
# v2.535 dayanak künyeleri [YEK_YON, 5346, CK7189, CK2949, CK3453, KARAR_5905] — bu dosyadaki madde atıflarının birincil yayımı (RG tarih-sayı, karar no); metin kunye.py sicilinden üretildi,
# tests/test_kunye_bekcisi.py sicille eş tutar (kaynak: 03.11.2026 doğrulama arşivi 03_Kaynak_Envanteri).
DAYANAK_KUNYELERI = (
    'YEK Yön.: Yenilenebilir Enerji Kaynaklarının Belgelendirilmesi ve Desteklenmesine İlişkin Yönetmelik, RG 01.10.2013-28782; değişiklikler RG 29.04.2016-29698 (m.16–17 mülga), 23.08.2019-30867, 19.08.2021-31573, 29.12.2025-33122, 19.10.2026-33405 (m.23(6)); '
    '5346: 5346 sayılı Yenilenebilir Enerji Kaynaklarının Elektrik Enerjisi Üretimi Amaçlı Kullanımına İlişkin Kanun, RG 18.05.2005-25819; '
    '7189 sayılı CK: 7189 sayılı Cumhurbaşkanı Kararı (1.7.2021–31.12.2030 işletmeye girecek YEK belgeli tesisler), RG 01.05.2023-32177; düzeltme RG 04.05.2023-32180; '
    'CK 2949: 2949 sayılı Cumhurbaşkanı Kararı (1.1–30.6.2021 işletmeye girenler), RG 18.09.2020-31248; '
    'CK 3453: 3453 sayılı Cumhurbaşkanı Kararı, RG 30.01.2021-31380 (7189 ile yürürlükten kalktı); '
    "Karar 5905-27: EPDK Kurul Kararı 5905-27 (02.12.2015; YEKDEM yararlanma yılları) — EPDK listesi, RG'de yayımlanmaz"
)

IST = ZoneInfo(PIYASA_TZ)
REJIMLER = ("otomatik", "cetvel1", "7189")
TESIS_TIPLERI = ("gunes", "gunes_depolamali")
TESIS_ETIKET = {"gunes": "güneş", "gunes_depolamali": "bütünleşik depolamalı güneş"}
CETVEL1_CENT = 13.3                                     # 5346 I sayılı Cetvel (güneş)
CETVEL1_SON_GIRIS = date(2021, 6, 30)
CK7189_SON_GIRIS = date(2030, 12, 31)
BANT_CENT = {"gunes": (4.95, 6.05), "gunes_depolamali": (5.85, 7.15)}          # 7189 Ek-1 taban/tavan (¢/kWh)
BASLANGIC_KR = {"gunes": (106.00, 28.80), "gunes_depolamali": (125.00, 38.45)}  # 7189 Ek-1 (fiyat, yerli katkı) kr/kWh
YERLI_YIL = {"gunes": 5, "gunes_depolamali": 10}                                # yerli katkı süresi (yıl)
J = 0.980                                              # YEKDEM tolerans katsayısı, güneş (Karar 7667; YEK Yön. m.18/1)
M23_6_BASLANGIC = date(2026, 10, 19)
# v2.540 (EK-3 DK-333, kanıt A): YEK Yön. m.23(9) — RG 29.12.2025-33122 Md.7 ile eklendi (Md.8: yürürlük 1.1.2026), RG 19.10.2026-33405 Md.5 ile yürürlükten
# kaldırıldı (Md.7: yayımı tarihinde). Metin: «Pazar günleri hariç olmak üzere, 2429 sayılı Kanunda yer alan tatil günlerinde; bildirilmiş olan KGÜP'ün üzerinde
# üretim yapılarak sisteme verilmesi halinde, KGÜP'ün üzerindeki üretim miktarı YEK UEVM hesaplamalarına dâhil edilmez ve … YEK bedeli ödemesi yapılmaz.»
M23_9_BASLANGIC = date(2026, 1, 1)
M23_9_BITIS = date(2026, 10, 18)
M23_9_NOTU = ("YEK Yön. m.23(9) (RG 29.12.2025-33122 Md.7, 1.1.2026 – RG 19.10.2026-33405 Md.5 ile 19.10.2026'da kalktı): Pazar hariç 2429 sayılı Kanun tatil "
              "günlerinde bildirilen KGÜP'ün üstündeki üretim YEK UEVM'ye girmez, YEK bedeli ödenmez. İşaret yalnız 1.1–18.10.2026 arasındaki tam tatil günleri "
              "için; arife ve 28 Ekim yarım günleri sayılmadı (yorum). KGÜP bildirilmemiş tatil saatleri «kgup_yok» ile ayrı sayılır (metin «bildirilmiş olan KGÜP» "
              "der; tespit yorumu). Fark tutarı YEK fiyatı − PTF ile yaklaşık (m.23(6)'daki 0,98 çarpanı bu fıkra için metinde yok).")


def m23_9_gunu(d: date) -> bool:
    """v2.540: m.23(9) uygulanan gün — 1.1–18.10.2026 arasında, Pazar değil, 2429 sayılı Kanun tatili (takvim.resmi_tatil; yarım günler hariç)."""
    from pvquant.ext.turkiye import takvim as tk
    return M23_9_BASLANGIC <= d <= M23_9_BITIS and d.weekday() != 6 and tk.resmi_tatil(d)
BANT_TOLERANS_CENT = 0.02                              # ilan edilen fiyat band sınırına bu kadar yakınsa «sınırda» (kırpma devrede)
REJIM_ETIKET = {"cetvel1": "Cetvel I (ABD senti/kWh × günün TCMB kuru)", "7189": "7189 sayılı CK (TL, aylık EPİAŞ ilanı)", None: "belirsiz"}
KAYNAK_ETIKET = {"tcmb": "günün TCMB alış kuru", "tcmb_onceki_gun": "önceki iş gününün TCMB alış kuru; tatil ya da hafta sonu",
                 "elle": "elle girilen yedek kur", "kur_yok": "kur yok", "epias_ilan": "EPİAŞ aylık ilanı", "onceki_ay": "önceki ayın ilanı; bu ay henüz ilan edilmedi",
                 "fiyat_yok": "aylık ilan yok", "rejim_yok": "rejim belirsiz", "sure_doldu": "destek süresi doldu; YEK fiyatı yok"}
EPIAS_DUYURU_URL = ("https://www.epias.com.tr/tum-duyurular/piyasa-duyurulari/elektrik/kayit-ve-uzlastirma/01-07-2021-tarihinden-31-12-2030-tarihine-kadar-"
                    "isletmeye-girecek-yek-belgeli-yenilenebilir-enerji-kaynaklarina-dayali-elektrik-uretim-tesisleri-icin-uygulanacak-fiyatlar-hk-38/")
EPIAS_DUYURU_BASLIK = "EPİAŞ duyurusu: 01.07.2021–31.12.2030 arasında işletmeye girecek YEK belgeli tesisler için uygulanacak fiyatlar (01.10.2026)"
_TARIH_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})|(\d{4})-(\d{2})-(\d{2})")
M23_6_NOTU = ("YEK Yön. m.23(6) (RG 19.10.2026-33405, 19.10.2026'dan): PTF ya da SMF taban değerin (V) altında ve sistem yönü enerji fazlası olan saatte "
              "programın (KGÜP) üstündeki üretim, PTF o saatin YEK fiyatından (+ yerli katkı) düşükse YEKDEM dışında kalır; KGÜP bildirilmemişse "
              "mevzuat KGÜP'ü 0 sayar (bildirilen KGÜP yüklenmemiş saatlerde PVQuant önerisi program sayılır; KGÜP = 0 okuması ayrıca verilir). "
              "Acil durum ya da yük atma talimatı (YAT) verilen saatler de kapsamdadır; talimat verisi PVQuant'ta olmadığından sayılmadı. "
              "Uzlaştırma dönemi bazında ve DGP başlangıcında bildirilen KGÜP ile (metin); EPİAŞ'ın ilk fatura dönemi ve hesap kalemi doğrulanamadı: işaret bilgi amaçlıdır, uzlaştırma sonucu değildir. "
              "Fark tutarı = YEKDEM dışı MWh × (YEK fiyatı − 0,98 × PTF).")


# ---------------- yardımcılar ----------------
def _pj(x) -> dict:
    """plant satırı ({'params_json': …}) ya da doğrudan params_json (dict/str) → dict."""
    pj = x.get("params_json", x) if isinstance(x, dict) and "params_json" in x else x
    if isinstance(pj, str):
        try:
            pj = json.loads(pj)
        except ValueError:
            pj = {}
    return pj or {}


def _tarih(v) -> date | None:
    if v is None or v == "":
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _yil_ekle(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:            # 29 Şubat
        return d.replace(year=d.year + n, day=28)


def bugun_ist() -> date:
    return datetime.now(IST).date()


# ---------------- rejim ----------------
def rejim_turet(pj: dict) -> dict:
    """tarife.rejim (cetvel1 | 7189) öncelikli; yoksa işletmeye giriş tarihinden: ≤30.6.2021 Cetvel I, 1.7.2021–31.12.2030 7189, sonrası belirsiz."""
    pj = _pj(pj); t = pj.get("tarife") or {}
    secim = t.get("rejim") or "otomatik"
    giris = _tarih(pj.get("isletmeye_giris"))
    tip = t.get("tesis_tipi") if t.get("tesis_tipi") in TESIS_TIPLERI else "gunes"
    out = {"secim": secim, "isletmeye_giris": giris.isoformat() if giris else None, "tesis_tipi": tip}
    if secim in ("cetvel1", "7189"):
        return {**out, "rejim": secim, "etiket": REJIM_ETIKET[secim], "kaynak": "Santral ayarları › Satış tarifesi'nde seçildi", "kaynak_turu": "kullanici"}
    if giris is None:
        return {**out, "rejim": None, "etiket": "belirsiz", "kaynak_turu": "yok",
                "kaynak": "işletmeye giriş tarihi girilmedi (Takvim › Santral tarihleri) ve tarifede rejim seçilmedi"}
    if giris <= CETVEL1_SON_GIRIS:
        return {**out, "rejim": "cetvel1", "etiket": REJIM_ETIKET["cetvel1"], "kaynak_turu": "hesaplanan",
                "kaynak": ("5346 sayılı Kanun m.6 ve I sayılı Cetvel: 31.12.2020'ye kadar işletmeye giren tesisler; 1.1–30.6.2021 girişliler CK 2949 "
                           "(RG 18.9.2020-31248) ile Cetvel I, 31.12.2030'a kadar (işletmeye giriş tarihinden türetildi)")}
    if giris <= CK7189_SON_GIRIS:
        return {**out, "rejim": "7189", "etiket": REJIM_ETIKET["7189"], "kaynak_turu": "hesaplanan",
                "kaynak": "7189 sayılı CK (RG 1.5.2023-32177): 1.7.2021–31.12.2030 arasında işletmeye giren tesisler (işletmeye giriş tarihinden türetildi)"}
    return {**out, "rejim": None, "etiket": "belirsiz", "kaynak_turu": "yok", "kaynak": "31.12.2030 sonrası işletmeye giriş için fiyat kararı yok"}


# ---------------- 7189 aylık fiyat (yekdem_fiyat) ----------------
def _ay(v) -> date:
    """'YYYY-MM' | 'YYYY-MM-DD' | date → ayın ilk günü."""
    if isinstance(v, date):
        return v.replace(day=1)
    s = str(v).strip()
    try:
        return date.fromisoformat(s[:10] if len(s) >= 10 else s + "-01").replace(day=1)
    except ValueError:
        raise ValueError("ay YYYY-MM biçiminde olmalı")


def fiyat_listesi(tesis_tipi: str | None = None) -> list[dict]:
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    sorgu = "SELECT ay, tesis_tipi, fiyat_kr_kwh, yerli_katki_kr_kwh, kaynak, guncelleme FROM yekdem_fiyat" + (" WHERE tesis_tipi = :t" if tesis_tipi else "") + " ORDER BY ay DESC, tesis_tipi"
    with sistem_baglami() as s:
        rows = s.execute(text(sorgu), {"t": tesis_tipi} if tesis_tipi else {}).fetchall()
    return [{"ay": r[0].isoformat()[:7], "tesis_tipi": r[1], "fiyat_kr_kwh": float(r[2]), "yerli_katki_kr_kwh": (float(r[3]) if r[3] is not None else None),
             "kaynak": r[4], "guncelleme": r[5].isoformat() if r[5] else None} for r in rows]


def aylik_fiyat(ay, tesis_tipi: str = "gunes") -> dict | None:
    a = _ay(ay).isoformat()[:7]
    return next((f for f in fiyat_listesi(tesis_tipi) if f["ay"] == a), None)


def kaynak_tarihi(kaynak: str | None) -> date | None:
    """Kaynak metnindeki ilk tarih (gg.aa.yyyy ya da yyyy-aa-gg); yoksa None."""
    m = _TARIH_RE.search(kaynak or "")
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m.group(1) else date(int(m.group(4)), int(m.group(5)), int(m.group(6)))
    except ValueError:
        return None


def kayit_durumu(f: dict, bugun: date | None = None) -> dict:
    """Kayıt güvenilirliği (şema değişmeden, kaynak metni ve kayıt zamanından): resmi (EPİAŞ duyurusu, tarihli, kayıt zamanıyla tutarlı) |
    elle (kaynak var ama EPİAŞ duyurusu olarak yazılmamış) | dogrulanmamis (kaynak yok / tarih yok / tarih gelecekte ya da kayıt zamanından sonra).
    01.11 incelemesi: sahte API'de «kaynak 02.11.2026, kayıt 01.11.2026» satırı resmî fiyat gibi görünüyordu."""
    b = bugun or bugun_ist()
    k = (f.get("kaynak") or "").strip()
    if not k:
        return {"durum": "dogrulanmamis", "neden": "kaynak belirtilmedi"}
    t = kaynak_tarihi(k)
    if t is None:
        return {"durum": "dogrulanmamis", "neden": "kaynakta duyuru tarihi yok"}
    if t > b:
        return {"durum": "dogrulanmamis", "neden": f"kaynak tarihi ({t.strftime('%d.%m.%Y')}) gelecekte"}
    g = _tarih(f.get("guncelleme"))
    if g and t > g:
        return {"durum": "dogrulanmamis", "neden": f"kaynak tarihi ({t.strftime('%d.%m.%Y')}) kayıt zamanından ({g.strftime('%d.%m.%Y')}) sonra"}
    try:
        donem = _ay(f.get("ay")) if f.get("ay") else None
    except ValueError:
        donem = None
    if donem and t.replace(day=1) < donem:   # 01.11 ikinci inceleme: 01.10.2026 duyurusu Kasım fiyatını içeremez (ilan dönem başında ya da sonra yayımlanır)
        return {"durum": "dogrulanmamis", "neden": f"kaynak tarihi ({t.strftime('%d.%m.%Y')}) geçerli dönemden ({donem.strftime('%m.%Y')}) önce; bu duyuru o dönemin fiyatını içeremez"}
    if "epia" not in k.lower().replace("ş", "s").replace("i̇", "i"):
        return {"durum": "elle", "neden": "kaynak EPİAŞ duyurusu olarak yazılmadı"}
    return {"durum": "resmi", "neden": f"EPİAŞ duyurusu {t.strftime('%d.%m.%Y')}"}


def fiyat_kaydet(ay, tesis_tipi: str, fiyat_kr_kwh, yerli_katki_kr_kwh=None, kaynak: str | None = None, bugun: date | None = None) -> dict:
    """Platform yönetimi: EPİAŞ'ın aylık ilanını girer/düzeltir (ay + tesis tipi başına tek satır, üzerine yazar). Kaynak zorunlu ve
    tarihli (duyuru tarihi bugünden sonra olamaz) — doğrulanmamış değer resmî fiyat gibi gösterilmesin."""
    from sqlalchemy import text
    from pvquant.db import sistem_baglami
    a = _ay(ay)
    if not (date(2023, 5, 1) <= a <= date(2041, 12, 1)):
        raise ValueError("ay 2023-05 ile 2041-12 arasında olmalı (7189 sayılı CK dönemi)")
    if tesis_tipi not in TESIS_TIPLERI:
        raise ValueError(f"tesis_tipi {' / '.join(TESIS_TIPLERI)} olmalı")
    try:
        f = float(fiyat_kr_kwh)
    except (TypeError, ValueError):
        raise ValueError("fiyat_kr_kwh sayı olmalı")
    if not (0 < f < 10000):
        raise ValueError("fiyat_kr_kwh 0–10.000 kuruş/kWh aralığında olmalı")
    y = None
    if yerli_katki_kr_kwh not in (None, ""):
        try:
            y = float(yerli_katki_kr_kwh)
        except (TypeError, ValueError):
            raise ValueError("yerli_katki_kr_kwh sayı olmalı")
        if not (0 <= y < 10000):
            raise ValueError("yerli_katki_kr_kwh 0–10.000 aralığında olmalı")
    k = (kaynak or "").strip()[:200] or None
    if not k:
        raise ValueError("kaynak gerekli: duyurunun adı ve tarihi (ör. «EPİAŞ duyurusu 01.10.2026»)")
    kt = kaynak_tarihi(k)
    if kt is None:
        raise ValueError("kaynakta duyuru tarihi olmalı (gg.aa.yyyy)")
    if kt > (bugun or bugun_ist()):
        raise ValueError(f"kaynak tarihi ({kt.strftime('%d.%m.%Y')}) bugünden sonra olamaz")
    if kt.replace(day=1) < a:
        raise ValueError(f"kaynak tarihi ({kt.strftime('%d.%m.%Y')}) geçerli dönemden ({a.strftime('%m.%Y')}) önce: EPİAŞ bir ayın fiyatını o ayın başında ya da sonra ilan eder, bu duyuru o dönemi içeremez")
    with sistem_baglami() as s:
        s.execute(text("INSERT INTO yekdem_fiyat(ay, tesis_tipi, fiyat_kr_kwh, yerli_katki_kr_kwh, kaynak, guncelleme) VALUES (:a, :t, :f, :y, :k, now()) "
                       "ON CONFLICT (ay, tesis_tipi) DO UPDATE SET fiyat_kr_kwh = EXCLUDED.fiyat_kr_kwh, yerli_katki_kr_kwh = EXCLUDED.yerli_katki_kr_kwh, "
                       "kaynak = EXCLUDED.kaynak, guncelleme = now()"), {"a": a, "t": tesis_tipi, "f": f, "y": y, "k": k})
    return aylik_fiyat(a, tesis_tipi) or {"ay": a.isoformat()[:7], "tesis_tipi": tesis_tipi, "fiyat_kr_kwh": f, "yerli_katki_kr_kwh": y, "kaynak": k, "guncelleme": None}


def bant_kontrol(ay, tesis_tipi: str, fiyat_kr_kwh: float, kur_ort: float | None = None, kur_ara: bool = True) -> dict:
    """7189 Ek-2 (s.6): TL fiyatın ¢/kWh karşılığı bir önceki ayın günlük USD alış kuru ortalamasıyla hesaplanır; taban/tavan dışına
    çıkan fiyat kırpılır. İlan edilen fiyat zaten kırpılmış olduğundan burada konum gösterilir: icinde | tabanda | tavanda | kur_yok."""
    a = _ay(ay); taban, tavan = BANT_CENT[tesis_tipi]
    onceki = (a - timedelta(days=1)).replace(day=1)
    kur_gun = kur_beklenen = None; kur_eksik: list = []
    if kur_ort is None and kur_ara:
        from pvquant.services import kur_service
        try:
            o = kur_service.aylik_ortalama(onceki)
        except Exception:   # noqa: BLE001 — DB yoksa band konumu gösterilmez
            o = None
        if o:
            kur_ort, kur_gun, kur_beklenen, kur_eksik = o["ortalama"], o["gun"], o.get("beklenen"), o.get("eksik_gun", [])
    out = {"taban_cent": taban, "tavan_cent": tavan, "kur_ayi": onceki.isoformat()[:7], "kur_ortalama": kur_ort,
           "kur_gun": kur_gun, "kur_beklenen": kur_beklenen, "kur_eksik_gun": kur_eksik}
    if not kur_ort:
        return {**out, "usd_cent": None, "durum": "kur_yok", "taban_kr": None, "tavan_kr": None}
    c = float(fiyat_kr_kwh) / float(kur_ort)   # kr/kWh ÷ TL/USD = ¢/kWh
    durum = "tabanda" if c <= taban + BANT_TOLERANS_CENT else "tavanda" if c >= tavan - BANT_TOLERANS_CENT else "icinde"
    return {**out, "usd_cent": round(c, 3), "durum": durum, "taban_kr": round(taban * kur_ort, 2), "tavan_kr": round(tavan * kur_ort, 2)}


# ---------------- gün bazlı fiyat serisi ----------------
_KOLONLAR = ["yek_tl_mwh", "yerli_tl_mwh", "toplam_tl_mwh", "kaynak", "kur", "kur_gunu", "ay_fiyat_kr_kwh", "usd_cent_kwh"]
# v2.538 (EK-3 DK-297, DK-323, DK-675; kanıt A): YEKDEM hesabının modellemediği kurallar — ürün yüzeyinde kapsam sınırı olarak gösterilir
KAPSAM_SINIRLARI = (
    {"kod": "y_katsayisi", "etiket": "Kapasite artışı (y katsayısı)",
     "metin": "YEK Yön. m.12(3)–(4) (RG 23.08.2019-30867): kapasite artışı yapılmış YEKDEM tesisinde YEK fiyatı, uzlaştırmaya esas veriş miktarının y katsayısıyla çarpılan "
              "payına uygulanır. PVQuant y katsayısını modellemez (y = 1 varsayar); kapasite artışı yapılmış tesiste YEK alacağı fazla hesaplanır."},
    {"kod": "kurulu_guc_asimi", "etiket": "Kabul edilmiş kurulu gücü aşan veriş",
     "metin": "YEK Yön. m.12: kabul edilmiş elektriksel kurulu gücün üstündeki veriş YEKDEM bedelinden ayrı işleme konur. PVQuant AC sınırı üstündeki saatleri ayırmaz; "
              "evirici sınırı nedeniyle güneşte seyrek beklenir (çıkarım)."},
    {"kod": "depolama", "etiket": "Bütünleşik depolama",
     "metin": "LÜY Ek m.3(2) (RG 02.04.2026-33212): depodan verilen miktar tespit edilemezse ihtiyaç fazlası enerjinin tamamı için ödeme yapılmaz; şebekeden çekilen kadar "
              "enerjinin önce depodan verildiği kabulü ve bu kısmın YEKDEM dışı (PTF) değerlenmesi PVQuant'ta modellenmedi — «bütünleşik depolamalı güneş» tipi yalnız 7189 fiyat "
              "bandını seçer, depo çıkışını ayırmaz."},
)


def _sure_doldu(pj: dict, rejim: str | None, giris: date | None, gun_dizisi: np.ndarray) -> np.ndarray:
    """v2.532: gün bazında destek süresi dolmuş mu? Cetvel I: takvim.yekdem_suresi son yılı (Karar 5905-27 / CK 2949 / kullanıcı başlangıç yılı);
    7189: işletmeye girişten 10 yıl (Ek-1). Süre türetilemiyorsa (giriş ve başlangıç yılı yok) sınır uygulanmaz."""
    hic = np.zeros(len(gun_dizisi), bool)
    if rejim == "7189":
        return (gun_dizisi >= _yil_ekle(giris, 10)) if giris else hic
    if rejim == "cetvel1":
        from pvquant.ext.turkiye import takvim as tk
        yb = pj.get("yekdem_baslangic_yili")
        try:
            y = tk.yekdem_suresi(giris, int(yb) if yb else None)
        except (TypeError, ValueError):
            y = None
        return (gun_dizisi > date(int(y["son_yil"]), 12, 31)) if y else hic
    return hic


def gunluk_fiyat_serisi(pj: dict, bas: date, bit: date) -> pd.DataFrame:
    """Gün indeksli (tz'siz Timestamp) YEK fiyatı: yek_tl_mwh, yerli_tl_mwh, toplam_tl_mwh (TL/MWh; NaN = fiyat yok), kaynak (gün başına
    kod), kur / kur_gunu (Cetvel I), ay_fiyat_kr_kwh / usd_cent_kwh. Cetvel I: ¢ × 10 × günün kuru (kur yoksa elle girilen kur; o da yoksa
    NaN). 7189: ayın ilanı × 10 (+ yerli katkı, süresi içinde); ay ilan edilmemişse önceki ayın ilanı (kaynak onceki_ay).
    v2.532: destek süresi dolan günlerde fiyat NaN, kaynak sure_doldu (_sure_doldu)."""
    pj = _pj(pj); t = pj.get("tarife") or {}; r = rejim_turet(pj)
    gunler = pd.date_range(pd.Timestamp(bas), pd.Timestamp(bit), freq="D")
    out = pd.DataFrame(index=gunler, columns=_KOLONLAR)
    for k in ("yek_tl_mwh", "yerli_tl_mwh", "toplam_tl_mwh", "kur", "ay_fiyat_kr_kwh", "usd_cent_kwh"):
        out[k] = np.nan
    out["kaynak"] = "rejim_yok"; out["kur_gunu"] = None
    giris = _tarih(pj.get("isletmeye_giris")); tip = r["tesis_tipi"]
    if len(gunler) == 0 or r["rejim"] is None:
        return out
    gun_dizisi = np.asarray([g.date() for g in gunler])
    sure_doldu = _sure_doldu(pj, r["rejim"], giris, gun_dizisi)
    if r["rejim"] == "cetvel1":
        cent = float(t.get("usd_cent_kwh") or CETVEL1_CENT)
        yerli_cent = float(t.get("yerli_katki_usd_cent") or 0.0)
        try:
            from pvquant.services import kur_service
            ks = kur_service.kur_serisi(bas, bit)
        except Exception:   # noqa: BLE001 — DB/tablo yoksa yalnız elle girilen kur
            ks = None
        kur = ks["kur"].reindex(gunler) if ks is not None else pd.Series(np.nan, index=gunler)
        kaynak = np.where(kur.notna(), np.where(ks["onceki_gun"].reindex(gunler).fillna(False).values, "tcmb_onceki_gun", "tcmb") if ks is not None else "tcmb", "kur_yok")
        elle = float(t["kur_tl_usd"]) if t.get("kur_tl_usd") else None
        if elle:
            kaynak = np.where(kur.notna(), kaynak, "elle"); kur = kur.fillna(elle)
        out["kur"] = kur.values; out["kaynak"] = kaynak
        out["kur_gunu"] = [(g.date().isoformat() if pd.notna(g) else None) for g in (ks["kur_gunu"].reindex(gunler) if ks is not None else pd.Series([pd.NaT] * len(gunler), index=gunler))]
        out["usd_cent_kwh"] = cent
        out["yek_tl_mwh"] = cent * 10.0 * kur.values
        yerli_gecerli = (gun_dizisi < _yil_ekle(giris, YERLI_YIL["gunes"])) if giris else np.ones(len(gunler), bool)
        out["yerli_tl_mwh"] = np.where(yerli_gecerli & (yerli_cent > 0), yerli_cent * 10.0 * kur.values, 0.0)
        if sure_doldu.any():   # v2.532 (DK-287): son yararlanma yılından sonra Cetvel I fiyatı yok
            out.loc[sure_doldu, ["yek_tl_mwh", "yerli_tl_mwh"]] = np.nan; out.loc[sure_doldu, "kaynak"] = "sure_doldu"
    else:   # 7189
        try:
            ilanlar = {f["ay"]: f for f in fiyat_listesi(tip)}
        except Exception:   # noqa: BLE001 — DB/tablo yoksa fiyat yok
            ilanlar = {}
        aylar = sorted(ilanlar)
        yerli_ac = bool(t.get("yerli_katki"))
        yerli_gecerli = (gun_dizisi < _yil_ekle(giris, YERLI_YIL[tip])) if giris else np.ones(len(gunler), bool)
        fiyat = np.full(len(gunler), np.nan); yerli = np.zeros(len(gunler)); kaynak = np.array(["fiyat_yok"] * len(gunler), dtype=object)
        for i, g in enumerate(gunler):
            ay = g.strftime("%Y-%m")
            if ay in ilanlar:
                f = ilanlar[ay]; kaynak[i] = "epias_ilan"
            else:
                onceki = [a for a in aylar if a < ay]
                if not onceki:
                    continue
                f = ilanlar[onceki[-1]]; kaynak[i] = "onceki_ay"
            fiyat[i] = f["fiyat_kr_kwh"]
            if yerli_ac and yerli_gecerli[i] and f.get("yerli_katki_kr_kwh"):
                yerli[i] = f["yerli_katki_kr_kwh"]
        if sure_doldu.any():   # v2.532 (DK-285/DK-287): 7189 Ek-1 YEK fiyatı işletmeye girişten 10 yıl
            fiyat[sure_doldu] = np.nan; yerli[sure_doldu] = 0.0; kaynak[sure_doldu] = "sure_doldu"
        out["ay_fiyat_kr_kwh"] = fiyat; out["kaynak"] = kaynak
        out["yek_tl_mwh"] = fiyat * 10.0                    # kr/kWh → TL/MWh
        out["yerli_tl_mwh"] = np.where(np.isnan(fiyat), np.nan, yerli * 10.0)
    out["toplam_tl_mwh"] = out["yek_tl_mwh"] + out["yerli_tl_mwh"].fillna(0.0)
    out.loc[out["yek_tl_mwh"].isna(), "toplam_tl_mwh"] = np.nan
    return out


def gun_fiyati(plant_or_pj, gun: date | None = None) -> dict | None:
    """Tek günün fiyatı (alarm, yıllık kaba gelir, panel kartı): NaN → None; rejim yoksa None."""
    g = gun or bugun_ist()
    s = gunluk_fiyat_serisi(_pj(plant_or_pj), g, g)
    if s.empty:
        return None
    r = s.iloc[0]
    def _f(v):
        return None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)
    if _f(r["toplam_tl_mwh"]) is None:
        return {"gun": g.isoformat(), "yek_tl_mwh": None, "yerli_tl_mwh": None, "toplam_tl_mwh": None, "kaynak": str(r["kaynak"]),
                "kaynak_etiket": KAYNAK_ETIKET.get(str(r["kaynak"]), str(r["kaynak"])), "kur": _f(r["kur"]), "kur_gunu": r["kur_gunu"],
                "onceki_gun": str(r["kaynak"]) == "tcmb_onceki_gun", "ay_fiyat_kr_kwh": _f(r["ay_fiyat_kr_kwh"]), "usd_cent_kwh": _f(r["usd_cent_kwh"])}
    return {"gun": g.isoformat(), "yek_tl_mwh": round(_f(r["yek_tl_mwh"]), 2), "yerli_tl_mwh": round(_f(r["yerli_tl_mwh"]) or 0.0, 2),
            "toplam_tl_mwh": round(_f(r["toplam_tl_mwh"]), 2), "kaynak": str(r["kaynak"]), "kaynak_etiket": KAYNAK_ETIKET.get(str(r["kaynak"]), str(r["kaynak"])),
            "kur": _f(r["kur"]), "kur_gunu": r["kur_gunu"], "onceki_gun": str(r["kaynak"]) == "tcmb_onceki_gun",
            "ay_fiyat_kr_kwh": _f(r["ay_fiyat_kr_kwh"]), "usd_cent_kwh": _f(r["usd_cent_kwh"])}


def saatlik_yek_fiyati(pj: dict, idx: pd.DatetimeIndex) -> pd.Series:
    """Saat indeksi (UTC) → o saatin (İstanbul günü) toplam YEK fiyatı (TL/MWh)."""
    if len(idx) == 0:
        return pd.Series(dtype=float, index=idx)
    ist = idx.tz_convert(IST) if idx.tz is not None else idx.tz_localize("UTC").tz_convert(IST)
    gunler = pd.DatetimeIndex(ist.date)
    s = gunluk_fiyat_serisi(pj, gunler.min().date(), gunler.max().date())
    return pd.Series(s["toplam_tl_mwh"].reindex(gunler).astype(float).values, index=idx)


# ---------------- m.23(6) ----------------
def m23_6_isaretle(pv: pd.DataFrame, yek_tl_mwh: pd.Series) -> pd.DataFrame:
    """pv: dengesizlik_service.saatlik_hesap çıktısı (UTC indeks; ptf, smf, yon, kgup, gerceklesen). yek_tl_mwh: saat başına YEK fiyatı.
    Dönüş (pv indeksinde): yek_fiyat_tl_mwh, m23_6 (evet | hayir | ptf_yek_ustu | fiyat_yok | kapsam_disi), yekdem_disi_mwh, yekdem_disi_tl;
    v2.540 (DK-333): m23_9 (evet | kgup_yok | hayir | kapsam_disi), m23_9_mwh, m23_9_tl — 1.1–18.10.2026 tatil günlerinde bildirilen KGÜP üstü üretim;
    v2.532 (DK-301): kgup0_mwh / kgup0_tl = bildirilen KGÜP yüklenmemiş saatlerde (program_kaynak ≠ bildirilen) mevzuat okuması — KGÜP = 0, o saatin
    üretiminin tamamı dışarıda (bildirilen saatlerde ve pv'de program_kaynak yoksa 0)."""
    from pvquant.ext.turkiye import kurallar as kr
    if pv is None or pv.empty:
        return pd.DataFrame(columns=["yek_fiyat_tl_mwh", "m23_6", "yekdem_disi_mwh", "yekdem_disi_tl", "kgup0_mwh", "kgup0_tl", "m23_9", "m23_9_mwh", "m23_9_tl"])
    gunler = pv.index.tz_convert(IST).date
    v = pd.Series([kr.v_degeri(d) for d in gunler], index=pv.index, dtype=float)
    yek = yek_tl_mwh.reindex(pv.index).astype(float)
    yururluk = pd.Series([d >= M23_6_BASLANGIC for d in gunler], index=pv.index)
    ptf = pv["ptf"].astype(float); smf = pv["smf"].astype(float)
    dusuk = v.notna() & ((ptf < v) | (smf < v))
    fazla_yon = pv["yon"].astype(str) == "fazla"
    ustu = (pv["gerceklesen"].astype(float) - pv["kgup"].astype(float)).clip(lower=0.0)
    aday = yururluk & dusuk & fazla_yon & (ustu > 1e-9)
    disi = aday & yek.notna() & (ptf < yek)
    mwh = ustu.where(disi, 0.0)
    tl = (mwh * (yek - J * ptf)).where(disi, 0.0)
    isaret = np.where(~yururluk, "kapsam_disi", np.where(disi, "evet", np.where(aday & yek.isna(), "fiyat_yok", np.where(aday, "ptf_yek_ustu", "hayir"))))
    ger = pv["gerceklesen"].astype(float).clip(lower=0.0)
    bildirilmemis = (pv["program_kaynak"].astype(str) != "bildirilen") if "program_kaynak" in pv else pd.Series(False, index=pv.index)
    disi0 = yururluk & dusuk & fazla_yon & bildirilmemis & (ger > 1e-9) & yek.notna() & (ptf < yek)
    mwh0 = ger.where(disi0, 0.0); tl0 = (mwh0 * (yek - J * ptf)).where(disi0, 0.0)
    # v2.540 (DK-333): m.23(9) tatil günü işareti — bildirilen KGÜP üstü üretim (1.1–18.10.2026, Pazar hariç tam tatil günleri)
    tatil = pd.Series([m23_9_gunu(d) for d in gunler], index=pv.index)
    evet9 = tatil & ~bildirilmemis & (ustu > 1e-9)
    kgup_yok9 = tatil & bildirilmemis & (ger > 1e-9)
    isaret9 = np.where(~tatil, "kapsam_disi", np.where(evet9, "evet", np.where(kgup_yok9, "kgup_yok", "hayir")))
    mwh9 = ustu.where(evet9, 0.0); tl9 = (mwh9 * (yek.fillna(0.0) - ptf)).where(evet9, 0.0)
    return pd.DataFrame({"yek_fiyat_tl_mwh": yek.values, "m23_6": isaret, "yekdem_disi_mwh": mwh.values, "yekdem_disi_tl": tl.values,
                         "kgup0_mwh": mwh0.values, "kgup0_tl": tl0.values, "m23_9": isaret9, "m23_9_mwh": mwh9.values, "m23_9_tl": tl9.values}, index=pv.index)


def dokum_ek(pj: dict, pv: pd.DataFrame) -> pd.DataFrame:
    """Saatlik döküme eklenen YEKDEM sütunları (lisanslı YEKDEM + tarife yekdem)."""
    return m23_6_isaretle(pv, saatlik_yek_fiyati(_pj(pj), pv.index))


def m23_6_ozeti(pv: pd.DataFrame, ek: pd.DataFrame, gun: int) -> dict:
    evet = ek["m23_6"] == "evet"; aday = ek["m23_6"].isin(["evet", "ptf_yek_ustu", "fiyat_yok"])
    bildirilmemis = int((evet & (pv["program_kaynak"].astype(str) != "bildirilen")).sum()) if "program_kaynak" in pv else 0
    saatler = ek.index[evet]
    out = {"baslangic": M23_6_BASLANGIC.isoformat(), "etiket": "belirsiz", "pencere_gun": gun, "saat": int(evet.sum()), "aday_saat": int(aday.sum()),
            "fiyat_yok_saat": int((ek["m23_6"] == "fiyat_yok").sum()), "kapsam_saat": int((ek["m23_6"] != "kapsam_disi").sum()),
            "yekdem_disi_mwh": round(float(ek["yekdem_disi_mwh"].sum()), 3), "yekdem_disi_tl": round(float(ek["yekdem_disi_tl"].sum()), 2),
            "bildirilmemis_saat": bildirilmemis,
            "kgup0_saat": int((ek["kgup0_mwh"] > 1e-9).sum()) if "kgup0_mwh" in ek else 0,   # v2.532 (DK-301): KGÜP = 0 okuması
            "kgup0_mwh": round(float(ek["kgup0_mwh"].sum()), 3) if "kgup0_mwh" in ek else 0.0,
            "kgup0_tl": round(float(ek["kgup0_tl"].sum()), 2) if "kgup0_tl" in ek else 0.0,
            "ilk_saat": saatler.min().tz_convert(IST).strftime("%Y-%m-%d %H:%M") if len(saatler) else None,
            "son_saat": saatler.max().tz_convert(IST).strftime("%Y-%m-%d %H:%M") if len(saatler) else None, "not": M23_6_NOTU}
    if "m23_9" in ek.columns:   # v2.540 (DK-333): m.23(9) tatil günü özeti
        e9 = ek["m23_9"] == "evet"; ky9 = ek["m23_9"] == "kgup_yok"; kapsam9 = ek["m23_9"] != "kapsam_disi"
        s9 = ek.index[e9]
        out["m23_9"] = {"baslangic": M23_9_BASLANGIC.isoformat(), "bitis": M23_9_BITIS.isoformat(), "kapsam_saat": int(kapsam9.sum()), "saat": int(e9.sum()),
                        "kgup_yok_saat": int(ky9.sum()), "mwh": round(float(ek.loc[e9, "m23_9_mwh"].sum()), 3), "tl": round(float(ek.loc[e9, "m23_9_tl"].sum()), 2),
                        "ilk_saat": (s9[0].tz_convert(IST).strftime("%Y-%m-%d %H:%M") if len(s9) else None), "son_saat": (s9[-1].tz_convert(IST).strftime("%Y-%m-%d %H:%M") if len(s9) else None),
                        "etiket": "belirsiz", "not": M23_9_NOTU}
    return out


# ---------------- özetler ----------------
def _aylar_7189(tip: str, bugun: date, geri_ay: int = 12) -> list[dict]:
    """Panel tablosu: son geri_ay ay içindeki kayıtlı ilanlar (band konumuyla) + içinde bulunulan ay (ilan yoksa «henüz ilan edilmedi»).
    Kayıt başlangıcından önceki aylar listelenmez — «ilan yok» EPİAŞ ilan etmedi anlamına gelmesin."""
    try:
        ilanlar = {f["ay"]: f for f in fiyat_listesi(tip)}
    except Exception:   # noqa: BLE001
        return []
    bu_ay = bugun.replace(day=1)
    y, m = bu_ay.year, bu_ay.month - geri_ay
    while m < 1:
        m += 12; y -= 1
    alt = date(y, m, 1)
    aylar = sorted({a for a in ilanlar if alt.isoformat()[:7] <= a <= bu_ay.isoformat()[:7]} | {bu_ay.isoformat()[:7]})
    out = []
    for a in aylar:
        f = ilanlar.get(a)
        if f is None:
            out.append({"ay": a, "fiyat_kr_kwh": None, "yerli_katki_kr_kwh": None, "kaynak": None, "bant": None, "durum": "ilan_yok"})
            continue
        out.append({**f, "bant": bant_kontrol(_ay(a), tip, f["fiyat_kr_kwh"]), "durum": "ilan"})
    return out


def ozet(tenant_id, plant: dict, gun: int = 90, bugun: date | None = None) -> dict:
    """Müşteri ucu: rejim, bugünün fiyatı, kur arşivi durumu, 7189 ayları (band konumuyla), m.23(6) özeti (yalnız lisanslı YEKDEM + tarife yekdem)."""
    from pvquant.services import dengesizlik_service
    pj = _pj(plant); t = pj.get("tarife") or {}; b = bugun or bugun_ist()
    seg = dengesizlik_service.segment_bilgisi(pj).get("segment")
    r = rejim_turet(pj)
    uygulanir = seg == "lisansli_yekdem"; tarife_yekdem = t.get("tip") == "yekdem"
    try:
        from pvquant.services import kur_service
        kur = kur_service.durum(b)
    except Exception:   # noqa: BLE001
        kur = None
    fiyat = gun_fiyati(pj, b) if r["rejim"] else None
    aylar = _aylar_7189(r["tesis_tipi"], b) if r["rejim"] == "7189" else []
    m23 = None
    if uygulanir and tarife_yekdem and r["rejim"]:
        pv = dengesizlik_service.saatlik_pv(tenant_id, plant, gun)
        if pv is not None and not pv.empty:
            m23 = m23_6_ozeti(pv, dokum_ek(pj, pv), gun)
    notlar = []
    if not uygulanir:
        notlar.append("Santral segmenti lisanslı YEKDEM değil; YEKDEM fiyatı yalnız tarife gelir hesabında kullanılır, m.23(6) işareti üretilmez.")
    if uygulanir and not tarife_yekdem:
        notlar.append("Satış tarifesi YEKDEM olarak seçilmemiş; Santral ayarları › Satış tarifesi'nden seçilince fiyat serisi ve m.23(6) işareti üretilir.")
    if r["rejim"] == "cetvel1":
        notlar.append("Cetvel I fiyatı enerjinin sisteme verildiği günün TCMB döviz alış kuruyla TL'ye çevrilir; tatil ve hafta sonu için önceki iş günü kuru taşınır (EPİAŞ uygulaması doğrulanmadı).")
    if r["rejim"] == "7189":
        notlar.append("7189 fiyatı EPİAŞ'ın aylık ilanıdır; ilan edilmemiş ay için önceki ayın fiyatı taşınır ve işaretlenir. USD sınır kontrolü bir önceki ayın ortalama TCMB USD alış kuruyla yapılır.")
    return {"bugun": b.isoformat(), "pencere_gun": gun, "segment": seg, "uygulanir": uygulanir, "tarife_yekdem": tarife_yekdem, "rejim": r, "fiyat": fiyat,
            "kur": kur, "aylar": aylar, "m23_6": m23, "not": " ".join(notlar) or None, "kapsam_sinirlari": list(KAPSAM_SINIRLARI) if uygulanir else [],
            "sabitler": {"cetvel1_cent": CETVEL1_CENT, "bant_cent": BANT_CENT[r["tesis_tipi"]], "baslangic_kr": BASLANGIC_KR[r["tesis_tipi"]], "yerli_yil": YERLI_YIL[r["tesis_tipi"]], "j": J}}


def yonetim_ozeti(bugun: date | None = None) -> dict:
    """Platform kartı: tüm ilanlar (band konumuyla), kur arşivi durumu, sabitler."""
    from pvquant.services import kur_service
    b = bugun or bugun_ist()
    fiyatlar = fiyat_listesi()
    onbellek: dict = {}
    for f in fiyatlar:
        ay = _ay(f["ay"]); onceki = (ay - timedelta(days=1)).replace(day=1)
        if onceki not in onbellek:
            o = kur_service.aylik_ortalama(onceki); onbellek[onceki] = o["ortalama"] if o else None
        f["bant"] = bant_kontrol(ay, f["tesis_tipi"], f["fiyat_kr_kwh"], kur_ort=onbellek[onceki], kur_ara=False)
        f["kayit"] = kayit_durumu(f, b)
    bu_ay = b.replace(day=1).isoformat()[:7]
    bekleyen = [{"ay": bu_ay, "tesis_tipi": t} for t in TESIS_TIPLERI if not any(f["ay"] == bu_ay and f["tesis_tipi"] == t for f in fiyatlar)]
    return {"bugun": b.isoformat(), "fiyatlar": fiyatlar, "bekleyen": bekleyen, "tesis_tipleri": list(TESIS_TIPLERI), "tesis_etiket": TESIS_ETIKET, "bant_cent": BANT_CENT,
            "baslangic_kr": BASLANGIC_KR, "kur": kur_service.durum(b), "kaynak_notu": "EPİAŞ aylık YEKDEM fiyat duyurusu (7189 sayılı CK Ek-2); kur TCMB",
            "kaynaklar": {"epias_url": EPIAS_DUYURU_URL, "epias_baslik": EPIAS_DUYURU_BASLIK, "tcmb_url": kur_service.TCMB_SAYFA,
                          "mevzuat": "7189 sayılı Cumhurbaşkanı Kararı (RG 1.5.2023-32177) Ek-1 fiyat ve sınırlar, Ek-2 aylık güncelleme"}}
