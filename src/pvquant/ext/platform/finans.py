"""v2.579 (Faz 2 F2-A, Stage 2 temeli) — Finansal Etki Merkezi sözlüğü: nitelik, bileşen, işaret eşlemesi, birim ve dönem çözümleyici.

FORMÜL YOK. Bu modül uzlaştırma, KÜPST, DSG, YEKDEM ya da gelir hesabı yapmaz; var olan servislerin ürettiği tutarları
tek işaret sözleşmesine ve tek nitelik sözlüğüne çevirmek için gereken saf tanımları taşır (saf: DB ve servis içe aktarmaz).

İşaret sözleşmesi (FEM): **artı = santral lehine (alacak), eksi = santral aleyhine (borç).** Kaynak servislerin alan adları ve
işaretleri DEĞİŞMEZ (geriye uyumluluk); `ISARET_ESLEMESI` her kaynak alanın FEM işaretine nasıl çevrildiğini belgeler ve
`fem_isareti()` bu çeviriyi yapar. Eşlemede olmayan bir alan çevrilmez (KeyError) — sessiz varsayım yok.

Nitelik sözlüğü: resmî (EPİAŞ bildirimi / resmî fiyat-kur) › hesaplanan (PVQuant yeniden hesabı, EPİAŞ fiyatıyla) › sözleşme
tahmini (tarife/sözleşme varsayımıyla) › senaryo (varsayımsal: senaryo fiyatı, yön varsayımı, karşı olgu, DSG üyeliği) › eksik
(hesaplanamadı). Bileşenler birleştirilirken EN ZAYIF nitelik kazanır.

Dönem kodları: `YYYY-MM-DD` gün, `YYYY-Wnn` ISO hafta (pazartesi başlar), `YYYY-MM` ay, `YYYY-QN` çeyrek, `YYYY` yıl.
Günler santralın yerel günüdür (v2.571 kuralı); UTC sınırlar yerel gün başından türetilir, yaz saati geçişli dilimde gün 23 ya da
25 saat olabilir. Ay/çeyrek/yıl kodları aylik_rapor_service.donem_cozumle ile aynıdır (o fonksiyon değiştirilmedi; bu modül saf kalsın diye
çözümleme burada yinelenir — iki yerin testi ortak kodlarla eş tutulur).
"""
from __future__ import annotations

from pvquant.zaman import PIYASA_TZ

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from zoneinfo import ZoneInfo

import pandas as pd

SOZLUK_SURUMU = "2026-11-11"
ISARET_KURALI = "artı = santral lehine (alacak), eksi = santral aleyhine (borç)"
IST_AD = PIYASA_TZ   # v2.599: tek tanım pvquant.zaman


# ---------------- nitelik ----------------
class Nitelik(str, Enum):
    RESMI = "resmi"
    HESAPLANAN = "hesaplanan"
    SOZLESME_TAHMINI = "sozlesme_tahmini"
    SENARYO = "senaryo"
    EKSIK = "eksik"


NITELIK_SIRA: tuple[Nitelik, ...] = (Nitelik.RESMI, Nitelik.HESAPLANAN, Nitelik.SOZLESME_TAHMINI, Nitelik.SENARYO, Nitelik.EKSIK)   # güçlüden zayıfa
NITELIK_AD = {Nitelik.RESMI: "resmî", Nitelik.HESAPLANAN: "hesaplanan", Nitelik.SOZLESME_TAHMINI: "sözleşme tahmini",
              Nitelik.SENARYO: "senaryo", Nitelik.EKSIK: "eksik"}
NITELIK_ACIKLAMA = {
    Nitelik.RESMI: "EPİAŞ uzlaştırma bildiriminden ya da resmî fiyat/kur kaydından alınan değer.",
    Nitelik.HESAPLANAN: "PVQuant'ın EPİAŞ saatlik fiyatı ve sistem yönüyle yeniden hesabı; resmî uzlaştırma sonucu değildir.",
    Nitelik.SOZLESME_TAHMINI: "Santral ayarlarındaki tarife ya da sözleşme varsayımıyla hesaplanan tahmin; fatura değildir.",
    Nitelik.SENARYO: "Varsayımsal hesap: senaryo fiyatı, varsayılan sistem yönü, karşı olgu kuralı ya da sözleşme verisi olmayan DSG üyeliği.",
    Nitelik.EKSIK: "Gerekli veri (fiyat, sistem yönü, katsayı, ölçüm ya da bildirim) olmadığından hesaplanamadı.",
}


def en_zayif(*nitelikler: Nitelik | str | None) -> Nitelik:
    """Birleşik bir değerin niteliği, girdilerinin en zayıfıdır. Boş girdi → eksik."""
    secilen = [Nitelik(n) for n in nitelikler if n is not None]
    if not secilen:
        return Nitelik.EKSIK
    return max(secilen, key=NITELIK_SIRA.index)


# ---------------- işaret eşlemesi ----------------
# kaynak alan → (çarpan, kaynak sözleşmesi). Çarpan +1: kaynakta artı zaten lehte; −1: kaynakta artı aleyhte (ters çevrilir).
ISARET_ESLEMESI: dict[str, tuple[int, str]] = {
    # ext/turkiye/dengesizlik.saatlik + dengesizlik_service.hesapla_df / dokum
    "dengesizlik.edt_neg": (-1, "ödenen EDT (negatif dengesizlik), kaynakta artı"),
    "dengesizlik.edt_borc_tl": (-1, "dökümde EDT borç sütunu, kaynakta artı"),
    "dengesizlik.edt_neg_tl": (-1, "aylık EDT(−) toplamı, kaynakta artı"),
    "dengesizlik.edtb_tl": (-1, "EDTB (m.110 ayrık toplama, 19.10.2026'dan), kaynakta artı = borç"),
    "dengesizlik.edt_poz": (+1, "alınan EDT (pozitif dengesizlik); B dalında eksi olabilir"),
    "dengesizlik.edt_alacak_tl": (+1, "dökümde EDT alacak sütunu"),
    "dengesizlik.edt_poz_tl": (+1, "aylık EDT(+) toplamı"),
    "dengesizlik.edta_tl": (+1, "EDTA (m.110 ayrık toplama), kaynakta artı = alacak"),
    "dengesizlik.edt_net": (+1, "EDT(+) − EDT(−), artı = gelir"),
    "dengesizlik.edt_net_tl": (+1, "döküm EDT net sütunu"),
    "dengesizlik.dengesizlik_maliyeti": (-1, "G×PTF referansına göre kayıp, artı = maliyet (EDT ile TOPLANMAZ)"),
    "dengesizlik.dengesizlik_tl": (-1, "aylık kayıp, artı = maliyet (EDT ile TOPLANMAZ)"),
    "dengesizlik.kupst": (-1, "KÜPST, yalnız borç"),
    "dengesizlik.kupst_tl": (-1, "KÜPST aylık / döküm, yalnız borç"),
    "dengesizlik.toplam_maliyet": (-1, "kayıp + KÜPST, artı = maliyet"),
    "dengesizlik.pvquant_tl": (-1, "kayıp + KÜPST (Doğruluk kartı), artı = maliyet"),
    "dengesizlik.toplam_tl": (-1, "döküm toplam sütunu (kayıp + KÜPST), artı = maliyet"),
    "dengesizlik.referans_fark_tl": (+1, "referans − toplam, artı = lehte (varsayımsal)"),
    "dengesizlik.kurtarilan_tl": (+1, "naif − pvquant, artı = lehte (varsayımsal)"),
    # dengesizlik.dsg_saatlik / dengesizlik_service.dsg_hesapla_df
    "dsg.edt_tek": (+1, "tek başına EDT net, artı = gelir"),
    "dsg.edt_tek_tl": (+1, "tek başına EDT net toplamı"),
    "dsg.edt_dsg": (+1, "DSG içinde EDT net (tek başınanın YERİNE geçer)"),
    "dsg.edt_dsg_tl": (+1, "DSG içinde EDT net toplamı"),
    "dsg.edt_grup_tl": (+1, "grup payı EDT net"),
    "dsg.edt_bireysel_tl": (+1, "üyede kalan EDT net"),
    "dsg.netlesme_farki": (+1, "edt_dsg − edt_tek, artı = lehte (varsayımsal)"),
    "dsg.netlesme_farki_tl": (+1, "netleşme farkı toplamı (varsayımsal)"),
    "dsg.kazanc_tl": (+1, "ayrı − net, artı = lehte (varsayımsal)"),
    "dsg.kupst_uye_tl": (-1, "üyelerin kendi KÜPST toplamı (santral KÜPST'üyle TOPLANMAZ)"),
    "dsg.ayri_tl": (-1, "tek başına toplam maliyet"),
    "dsg.net_tl": (-1, "DSG içinde toplam maliyet"),
    # mutabakat_service / saatlik_detay_service
    "mutabakat.alacak_tl": (+1, "kalem alacak"),
    "mutabakat.borc_tl": (-1, "kalem borç"),
    "mutabakat.fark_tl": (+1, "(PVQuant net) − (EPİAŞ net), artı = PVQuant hesabı daha lehte"),
    "mutabakat.kiyas.dengesizlik_fark_tl": (+1, "sayaç − SCADA dengesizlik neti, artı = lehte"),
    "mutabakat.kiyas.kupst_fark_tl": (-1, "sayaç − SCADA KÜPST borcu, artı = aleyhte"),
    "saatlik_detay.edt_net_fark_tl": (+1, "PVQuant − EPİAŞ EDT net, artı = PVQuant daha lehte"),
    "saatlik_detay.edt_poz_tl": (+1, "resmî saatlik EDT(+)"),
    "saatlik_detay.edt_neg_tl": (-1, "resmî saatlik EDT(−), kaynakta artı"),
    "saatlik_detay.kupst_tl": (-1, "resmî saatlik KÜPST"),
    # tarife / yekdem / kayıp / kullanılabilirlik / sayaç
    "tarife.gelir_tl": (+1, "üretim × tarife fiyatı"),
    "yekdem.yek_alacagi_tl": (+1, "üretim × YEK fiyatı (kaba)"),
    "yekdem.yekdem_disi_tl": (-1, "m.23(6) YEKDEM dışı üretim farkı, artı = kaybedilen gelir"),
    "yekdem.kgup0_tl": (-1, "m.23(6) alternatif okuma (yekdem_disi_tl ile TOPLANMAZ)"),
    "yekdem.m23_9_tl": (-1, "m.23(9) tatil günü farkı, artı = kaybedilen gelir"),
    "kayip.kayip_tl": (-1, "beklenen − gerçek × satış fiyatı, artı = gelir kaybı tahmini"),
    "kayip.toplam_kayip_tl": (-1, "kayıp ayrışımı toplamı, artı = gelir kaybı tahmini"),
    "kullanilabilirlik.acik_tl": (-1, "sözleşme eşiği açığı, kıyas tabanı (alacak değil)"),
    "sayac.bedel_toplam_tl": (-1, "Karar 14909 bedel göstergesi, varsayımsal"),
    "dengesizlik.teminat_tl": (-1, "teminat göstergesi (maliyet değil, bağlanan tutar)"),
}


def fem_isareti(kaynak_alan: str, deger) -> float | None:
    """Kaynak alanın değerini FEM işaretine çevirir. Bilinmeyen alan → KeyError (sessiz varsayım yapılmaz); None/NaN → None."""
    carpan, _ = ISARET_ESLEMESI[kaynak_alan]
    if deger is None:
        return None
    x = float(deger)
    if math.isnan(x):
        return None
    return carpan * x


def bildirim_isareti(tutar_tl, yon: str | None) -> float | None:
    """uzlastirma_bildirimi.tutar_tl mutlak değerdir, yönü `yon` taşır (alacak | borc)."""
    if tutar_tl is None or yon not in ("alacak", "borc"):
        return None
    x = abs(float(tutar_tl))
    if math.isnan(x):
        return None
    return x if yon == "alacak" else -x


def alacak_borc(net: float | None) -> tuple[float | None, float | None]:
    """Net FEM tutarını (alacak, borç) çiftine ayırır; ikisi de artı sayıdır."""
    if net is None:
        return None, None
    return (net if net > 0 else 0.0), (-net if net < 0 else 0.0)


# ---------------- bileşen ----------------
@dataclass
class Bilesen:
    """Finansal sonucun bir satırı. `tutar_tl` FEM işaretinde net tutar; `alacak_tl`/`borc_tl` artı sayılar.
    `toplanir=False` olan satırlar (göstergeler, alternatif okumalar, bilgi satırları) toplama girmez."""
    kod: str
    ad: str
    tutar_tl: float | None = None
    alacak_tl: float | None = None
    borc_tl: float | None = None
    nitelik: Nitelik = Nitelik.EKSIK
    kaynak: str = ""
    kapsam_saat: int | None = None
    beklenen_saat: int | None = None
    kural_surumu: str | None = None
    dayanak: str | None = None
    toplanir: bool = True
    notlar: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.nitelik = Nitelik(self.nitelik)
        if self.tutar_tl is not None and (self.alacak_tl is None and self.borc_tl is None):
            self.alacak_tl, self.borc_tl = alacak_borc(self.tutar_tl)
        if self.tutar_tl is None and self.nitelik != Nitelik.EKSIK and (self.alacak_tl is not None or self.borc_tl is not None):
            self.tutar_tl = float(self.alacak_tl or 0.0) - float(self.borc_tl or 0.0)
        if self.tutar_tl is None:
            self.nitelik = Nitelik.EKSIK

    @classmethod
    def eksik(cls, kod: str, ad: str, neden: str, kaynak: str = "", toplanir: bool = True) -> Bilesen:
        return cls(kod=kod, ad=ad, nitelik=Nitelik.EKSIK, kaynak=kaynak, toplanir=toplanir, notlar=[neden])

    def kapsam_orani(self) -> float | None:
        if not self.beklenen_saat or self.kapsam_saat is None:
            return None
        return round(self.kapsam_saat / self.beklenen_saat, 4)

    def sozluk(self) -> dict:
        d = {"kod": self.kod, "ad": self.ad, "tutar_tl": _yuvarla(self.tutar_tl), "alacak_tl": _yuvarla(self.alacak_tl), "borc_tl": _yuvarla(self.borc_tl),
             "nitelik": self.nitelik.value, "nitelik_ad": NITELIK_AD[self.nitelik], "kaynak": self.kaynak, "kapsam_saat": self.kapsam_saat,
             "beklenen_saat": self.beklenen_saat, "kapsam_orani": self.kapsam_orani(), "kural_surumu": self.kural_surumu, "dayanak": self.dayanak,
             "toplanir": self.toplanir, "notlar": list(self.notlar)}
        return d


def toplam(bilesenler: list[Bilesen]) -> dict:
    """Toplama giren (toplanir=True, eksik olmayan) satırların net toplamı; nitelik en zayıf; eksik satırlar ayrıca sayılır.
    Çift sayım bekçisi: aynı `kod` iki kez toplanmaz (ValueError)."""
    kodlar = [b.kod for b in bilesenler if b.toplanir]
    if len(kodlar) != len(set(kodlar)):
        raise ValueError("aynı bileşen kodu toplamda iki kez: " + ", ".join(sorted({k for k in kodlar if kodlar.count(k) > 1})))
    giren = [b for b in bilesenler if b.toplanir and b.nitelik != Nitelik.EKSIK and b.tutar_tl is not None]
    eksik = [b.kod for b in bilesenler if b.toplanir and (b.nitelik == Nitelik.EKSIK or b.tutar_tl is None)]
    net = sum(b.tutar_tl for b in giren) if giren else None
    nit = en_zayif(*[b.nitelik for b in giren]) if giren else Nitelik.EKSIK
    if eksik and giren:
        nit = en_zayif(nit, Nitelik.SENARYO) if nit != Nitelik.EKSIK else nit   # eksik kalemle toplam en iyi hâlde «senaryo» kadar güvenilirdir
    al, bo = alacak_borc(net)
    return {"tutar_tl": _yuvarla(net), "alacak_tl": _yuvarla(al), "borc_tl": _yuvarla(bo), "nitelik": nit.value, "nitelik_ad": NITELIK_AD[nit],
            "giren": [b.kod for b in giren], "eksik": eksik, "isaret": ISARET_KURALI}


# ---------------- birim ----------------
def kwh_mwh(kwh) -> float | None:
    return None if kwh is None or (isinstance(kwh, float) and math.isnan(kwh)) else float(kwh) / 1000.0


def mwh_kwh(mwh) -> float | None:
    return None if mwh is None or (isinstance(mwh, float) and math.isnan(mwh)) else float(mwh) * 1000.0


def tl_per_mwh(tl, mwh, asgari_mwh: float = 1e-6) -> float | None:
    """Birim tutar; payda ≈ 0 ise None (sonsuz/uydurma yok)."""
    if tl is None or mwh is None:
        return None
    try:
        t, m = float(tl), float(mwh)
    except (TypeError, ValueError):
        return None
    if math.isnan(t) or math.isnan(m) or abs(m) < asgari_mwh:
        return None
    return t / m


def bin_tl(x) -> float | None:
    """Sunum için bin TL'ye yuvarlama (ileri maruziyet gibi veri kalitesini aşmayan hassasiyet)."""
    return None if x is None else round(float(x) / 1000.0) * 1000.0


def _yuvarla(x, nd: int = 2) -> float | None:
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) else round(x, nd)


# ---------------- dönem ----------------
AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
_GUN_RE = re.compile(r"^(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
_HAFTA_RE = re.compile(r"^(20\d{2})-W(0[1-9]|[1-4]\d|5[0-3])$")
_AY_RE = re.compile(r"^(20\d{2})-(0[1-9]|1[0-2])$")
_CEYREK_RE = re.compile(r"^(20\d{2})-Q([1-4])$")
_YIL_RE = re.compile(r"^(20\d{2})$")
DONEM_TURLERI = ("gun", "hafta", "ay", "ceyrek", "yil")
DONEM_TUR_AD = {"gun": "gün", "hafta": "hafta", "ay": "ay", "ceyrek": "çeyrek", "yil": "yıl"}


def yerel_gun_baslangici_utc(d: date, tz: str = IST_AD) -> datetime:
    """Yerel günün başı (santral dilimi) → UTC."""
    return datetime.combine(d, datetime.min.time(), tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)


def donem_cozumle(s: str | None, bugun: date | None = None, tz: str = IST_AD) -> dict:
    """Dönem kodu → {tur, kod, bas, bit (hariç), bas_utc, bit_utc, etiket, kirpildi, gun, saat}.
    Verilmezse son tam ay. Gelecek dönem ValueError; süren dönem bugüne (bugün dâhil) kırpılır. Saat sayısı yerel dilimden hesaplanır
    (yaz saati geçişli dilimde 23/25 saatlik gün). Tutarsız tarih (30 Şubat) ValueError."""
    b = bugun or datetime.now(ZoneInfo(tz)).date()
    if not s:
        ilk = b.replace(day=1)
        s = (ilk - timedelta(days=1)).strftime("%Y-%m")
    s = str(s).strip().upper()
    if m := _GUN_RE.match(s):
        try:
            bas = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError as e:
            raise ValueError("geçersiz gün") from e
        bit = bas + timedelta(days=1); tur = "gun"; etiket = f"{bas.day} {AYLAR[bas.month - 1]} {bas.year}"
    elif m := _HAFTA_RE.match(s):
        y, h = int(m.group(1)), int(m.group(2))
        try:
            bas = date.fromisocalendar(y, h, 1)
        except ValueError as e:
            raise ValueError("geçersiz ISO haftası") from e
        bit = bas + timedelta(days=7); tur = "hafta"; son = bit - timedelta(days=1)
        etiket = (f"{y} {h}. hafta ({bas.day}–{son.day} {AYLAR[son.month - 1]})" if bas.month == son.month
                  else f"{y} {h}. hafta ({bas.day} {AYLAR[bas.month - 1]} – {son.day} {AYLAR[son.month - 1]})")
    elif m := _AY_RE.match(s):
        y, a = int(m.group(1)), int(m.group(2)); bas = date(y, a, 1); bit = date(y + (a == 12), a % 12 + 1, 1); tur = "ay"; etiket = f"{AYLAR[a - 1]} {y}"
    elif m := _CEYREK_RE.match(s):
        y, q = int(m.group(1)), int(m.group(2)); bas = date(y, 3 * q - 2, 1); bit = date(y + (q == 4), (3 * q) % 12 + 1, 1); tur = "ceyrek"; etiket = f"{y} {q}. çeyrek"
    elif m := _YIL_RE.match(s):
        y = int(m.group(1)); bas = date(y, 1, 1); bit = date(y + 1, 1, 1); tur = "yil"; etiket = f"{y} yılı"
    else:
        raise ValueError("donem YYYY-MM-DD, YYYY-Wnn, YYYY-MM, YYYY-QN ya da YYYY olmalı")
    if bas > b:
        raise ValueError("gelecek dönem için finansal etki hesaplanmaz")
    kirpildi = bit > b + timedelta(days=1)
    if kirpildi:
        bit = b + timedelta(days=1)
    bas_utc, bit_utc = yerel_gun_baslangici_utc(bas, tz), yerel_gun_baslangici_utc(bit, tz)
    return {"tur": tur, "kod": s, "bas": bas, "bit": bit, "bas_utc": bas_utc, "bit_utc": bit_utc,
            "etiket": etiket + (" (süren dönem, bugüne kadar)" if kirpildi else ""), "kirpildi": kirpildi,
            "gun": (bit - bas).days, "saat": round((bit_utc - bas_utc).total_seconds() / 3600), "tz": tz}


def saat_kumesi(donem: dict) -> pd.DatetimeIndex:
    """Dönemin UTC saat başı kümesi [bas_utc, bit_utc). Bütün bileşenler aynı kümeden kurulur (KPI tutarlılığı)."""
    return pd.date_range(donem["bas_utc"], donem["bit_utc"], freq="h", inclusive="left", tz="UTC")


def donem_kodu(d: date, tur: str) -> str:
    """Bir tarihin ait olduğu dönemin kodu (gece işi ve geçmiş sürümler için)."""
    if tur == "gun":
        return d.isoformat()
    if tur == "hafta":
        y, h, _ = d.isocalendar(); return f"{y}-W{h:02d}"
    if tur == "ay":
        return d.strftime("%Y-%m")
    if tur == "ceyrek":
        return f"{d.year}-Q{(d.month - 1) // 3 + 1}"
    if tur == "yil":
        return str(d.year)
    raise ValueError("bilinmeyen dönem türü")
