"""v2.521 (P1a) — olay kaydı: planlı bakım, arıza, talimat (YAL/YAT), acil durum kesmesi, şebeke kesintisi, hasar.

Tek tablo (olay; RLS kiracı), olay türüne bağlı kurallar (TUR_KURAL): EAK'yi düşürür mü (TPYS EAK.csv'de hangi gerekçe sütununa yazılır),
kullanılabilirlik hesabında istisna mı (planlı bakım, şebeke kesintisi, talimat, acil kesme: santralın elinde değil), aylık arıza sayacına
girer mi (Karar 14029/14907: UEVÇB'de ayda 30 ve üzeri arıza kaydı KÜPST n katsayısını 0,05 → 0,08 yapar; 25 ürün ön uyarısıdır, m.69/A itiyat ölçütü değildir; sayaç EPİAŞ sayımına vekildir,
TPYS Arıza ve Bakım bildirimi sayısıyla eşleşmesi doğrulanmadı).
Dayanak (GES sahibi araştırması): 01-18 (EAK gerekçe sütunları: kaynak yetersizliği, iklim/verim, mücbir, dışsal, güvenlik; arıza ve bakım
TPYS «Arıza ve Bakım bildirimleri» sayfasından ayrıca girilir — PVQuant bunu yapmaz, dosya adı ve kaydı tutar), 01-19 (Karar 14967: tesis bazında
≥30 MW, portföy bazında ≥50 MW güç değişimi olayın ortaya çıkışından en geç 1 saat içinde Dâhilî Bilgi Platformu'nda; yürürlük tarihi metinde
yok → «belirsiz»), 03-10 (ESY m.52–54: kısa planlı devre dışı 24 saat / 7 gün önceden; yıllık plan 30 Nisan), DUY m.69/A(2) (EAK'yi arıza/bakım
kaydıyla düşürmeyi itiyat etmek Kanun m.16'ya gider — «kayıt değiştirilemez/silinemez» ürün tasarımıdır; destekleyici hükümler m.69/A(2)–(3), PBD Yön. m.10(1)(ç), m.12(2)).
Talimat olayları (YAL/YAT) EAK'yi değiştirmez; BUDÜP hesabına bağlanması P2b. Silme yok: «iptal» durumu; geçmiş kayıt korunur.
02.11 üçüncü inceleme: hasar türü «mücbir sebep»i otomatik seçmez (fiziksel tür ≠ mevzuattaki gerekçe; TPYS dokümanı başka neden yoksa «kaynak
yetersizliği» der, 01-18); devre dışı güç sınırı AC tabanı (ac_limit_kw) — kWp değil; çakışma uyarısı dürüst (kayıtlar toplanır, ekipman kimliği
tutulmaz); bitişi girilmemiş olay gün sonuna kadar sayılır (program/EAK dosyası ileriye dönük); dosyadaki evre «geçersiz» (ekranla aynı).
Tahmin motoru değişmez: olay yalnız program tavanını (EAK) ve etiketleri etkiler.
"""
from __future__ import annotations

import io
import json
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import text

from pvquant.db import tenant_baglami
from pvquant.zaman import PIYASA_TZ

# v2.535 dayanak künyeleri [DUY, KARAR_14967, KARAR_14968, SEFFAFLIK] — bu dosyadaki madde atıflarının birincil yayımı (RG tarih-sayı, karar no); metin kunye.py sicilinden üretildi,
# tests/test_kunye_bekcisi.py sicille eş tutar (kaynak: 03.11.2026 doğrulama arşivi 03_Kaynak_Envanteri).
DAYANAK_KUNYELERI = (
    'DUY: Elektrik Piyasası Dengeleme ve Uzlaştırma Yönetmeliği, RG 14.04.2009-27200; değişiklikler RG 28.03.2015-29309, 30.10.2016-29873, 18.01.2018-30305, 09.08.2019-30857, 02.02.2020-31027, 19.11.2022-32018, 19.12.2023-32404, 17.12.2024-32755, 21.01.2025-32789, 29.12.2025-33122, 19.10.2026-33405, 21.10.2026-33407; '
    'Karar 14967: EPDK Kurul Kararı 14967 (dâhilî bilgi bildirimi), RG 20.10.2026-33406; '
    "Karar 14968: EPDK Kurul Kararı 14968 (Şeffaflık Platformu veri listesi, 1.1.2027'den), RG 20.10.2026-33406; öncesi Karar 10711; "
    'Şeffaflık Yön.: Enerji Piyasalarında Şeffaflığa ve Piyasa Bozucu Davranışlara İlişkin Yönetmelik, RG 14.02.2026-33168; değişiklik RG 23.05.2026-33262'
)

IST = ZoneInfo(PIYASA_TZ)
TURLER = ("planli_bakim", "ariza", "talimat_yat", "talimat_yal", "acil_kesme", "sebeke_kesintisi", "hasar", "uzaktan_acma")   # v2.523 (P4a): uzaktan açma yapılamadı
TUR_ETIKET = {"planli_bakim": "Planlı bakım", "ariza": "Arıza", "talimat_yat": "Yük atma talimatı (YAT)", "talimat_yal": "Yük alma talimatı (YAL)",
              "acil_kesme": "Acil durum kesmesi", "sebeke_kesintisi": "Şebeke kesintisi", "hasar": "Hasar",
              "uzaktan_acma": "Uzaktan açma yapılamadı"}   # v2.523 (P4a)
GEREKCELER = ("kaynak_yetersizligi", "iklim_verim", "mucbir", "dissal", "guvenlik")
GEREKCE_ETIKET = {"kaynak_yetersizligi": "kaynak yetersizliği", "iklim_verim": "iklim / verim", "mucbir": "mücbir sebep", "dissal": "dışsal", "guvenlik": "güvenlik"}
# tür → EAK'yi düşürür mü, EAK.csv varsayılan gerekçe sütunu, kullanılabilirlik istisnası mı, arıza sayacına girer mi, açıklama
TUR_KURAL = {
    "planli_bakim":    {"eak_dusur": True,  "gerekce": "kaynak_yetersizligi", "istisna": True,  "sayac": False, "not": "EAK düşer; TPYS Arıza ve Bakım bildirimi ayrıca; kullanılabilirlik hesabında istisna"},
    "ariza":           {"eak_dusur": True,  "gerekce": "kaynak_yetersizligi", "istisna": False, "sayac": True,  "not": "EAK düşer; aylık arıza sayacına girer (30 ve üzeri KÜPST n 0,08); kullanılabilirlikte arıza"},
    "talimat_yat":     {"eak_dusur": False, "gerekce": None,                  "istisna": True,  "sayac": False, "not": "EAK değişmez; program sapması talimattan (BUDÜP); kullanılabilirlikte istisna; talimat miktarı (MW) kayıt içindir, hesaba girmez; uyulamadıysa gerekçe 3 iş günü (DUY m.71/A)"},
    "talimat_yal":     {"eak_dusur": False, "gerekce": None,                  "istisna": True,  "sayac": False, "not": "EAK değişmez; program sapması talimattan (BUDÜP); talimat miktarı (MW) kayıt içindir; uyulamadıysa gerekçe 3 iş günü (DUY m.71/A)"},
    "acil_kesme":      {"eak_dusur": True,  "gerekce": "dissal",              "istisna": True,  "sayac": False, "not": "Sistem İşletmecisi kesmesi: EAK dışsal gerekçeyle düşer; kullanılabilirlikte istisna; lisanssızda talimat tutarı GTŞ/toplayıcı üzerinden yansıtılır (DUY m.75(3)), yerine getirilmeyen kısma ödeme yok (LÜY Ek m.4); şebeke işletmecisinin sona erme bildirimi 15 dk içinde (LÜY m.21(8)), bildirim zamanı kaydedilir"},
    "sebeke_kesintisi": {"eak_dusur": True, "gerekce": "dissal",              "istisna": True,  "sayac": False, "not": "Şebeke kaynaklı: EAK dışsal gerekçeyle düşer; kullanılabilirlikte istisna"},
    "hasar":           {"eak_dusur": True,  "gerekce": "kaynak_yetersizligi", "istisna": False, "sayac": False, "not": "Hasar dosyası için kayıt; EAK düşer. Hasar tek başına mücbir sebep değildir: «mücbir sebep» gerekçesi yalnız mevzuattaki koşullar sağlanıyorsa seçilir"},
    "uzaktan_acma":    {"eak_dusur": False, "gerekce": None,                  "istisna": False, "sayac": False, "not": "Lisanssız tesiste acil durum talimatında uzaktan açma yapılamadı (LÜY m.21(7) SCADA bağlantısı); EAK değişmez; Sayaç sayfasındaki Karar 14909 bedel göstergesine girer (ay içinde en çok üç kat)"},   # v2.523 (P4a)
}
DURUMLAR = ("acik", "kapali", "iptal")
# v2.541 (EK-3 DK-741/DK-743, kanıt A)
BILDIRIM_SURE_DK = 15
LUY_M21_8_NOTU = ("LÜY m.21(8) (RG 19.10.2026-33405 Md.1): şebeke işletmecisi, acil durumun sona erme zamanından itibaren 15 dakika içinde acil durumun sona "
                  "erdiğini tesis sahibine telefon ve kalıcı veri saklayıcısı ile bildirir; bildirimden sonra yeniden enerjilendirme tesis sahibinin sorumluluğundadır. "
                  "Bildirim zamanı beyandır; bitişle arasındaki süre, talimat dışı üretim kaybının ayrıştırılması için kaydedilir.")
DUY_M71A_NOTU = ("DUY m.71/A(1): dengeleme güç piyasası katılımcısı talimata uymakla yükümlüdür; teknik gereklilikle yerine getiremezse MYTM/BYTM'yi ivedilikle haberdar "
                 "eder ve gerekçesini olayı takip eden en geç 3 iş günü içinde yazılı bildirir. Son gün yalnız talimata uyulamadıysa anlamlıdır (iş günü sayımı Takvim motoru).")
GEREKCE_IS_GUNU = 3
DAHILI_TESIS_KW = 30_000.0      # Karar 14967 Asgari Veriler Listesi sıra 1: tesis bazında 30 MW ve üzeri
DAHILI_PORTFOY_KW = 50_000.0    # portföy bazında 50 MW ve üzeri
DAHILI_SURE_SAAT = 1
DAHILI_YURURLUK = date(2027, 1, 1)   # v2.538 (EK-3 DK-613, kanıt A): Şeffaflık ve Piyasa Bozucu Davranışlar Yön. (RG 14.02.2026-33168) m.16 yürürlüğü RG 23.05.2026-33262 ile 1.1.2027
DAHILI_YURURLUK_ETIKET = "01.01.2027"
DAHILI_YURURLUK_NOTU = ("Yürürlük: Enerji Piyasalarında ve Çevresel Piyasalarda Şeffaflığa ve Piyasa Bozucu Davranışlara İlişkin Yönetmelik (RG 14.02.2026-33168) "
                        "m.16 ile 1.1.2027 (RG 23.05.2026-33262 ile ertelendi); Karar 14967'de ayrı yürürlük fıkrası yok, 1 saat kuralının başlangıcı "
                        "Yönetmelik yürürlüğünden çıkarımdır.")
DAHILI_YEK_G_NOTU = ("Karar 14967 Ek sıra 17 (kanıt: RG 20.10.2026-33406 metni): YEK-G sisteminde yer alan tesislerin arıza veya plansız bakım nedeniyle emre amade "
                     "olamaması bilgisi eşiksizdir (yükümlü: üretim lisansı sahibi, toplayıcı). Fıkra 3(b): eşik öngörülmeyen veriler dâhilî bilgi tanımının "
                     "unsurlarını sağladıkları takdirde açıklanır — değerlendirme piyasa katılımcısınındır; açıklanacaksa fıkra 4(a) uyarınca en geç 1 saat içinde.")   # v2.540 (EK-3 DK-612)
DAHILI_NOTU = ("Karar 14967 (RG 20.10.2026-33406) m.4(a): arıza ve bakım dâhil kapasite kullanımı değişiklikleri, olayın ortaya çıkışından en geç 1 saat "
               "içinde Dâhilî Bilgi Platformu'nda açıklanır; eşik tesis bazında 30 MW, portföy bazında 50 MW (Ek sıra 1); YEK-G sistemindeki tesiste arıza/plansız "
               "bakım eşiksiz (Ek sıra 17, fıkra 3(b) koşuluyla). " + DAHILI_YURURLUK_NOTU +
               " Platform arayüzü doğrulanmadı. Bu geri sayım hatırlatmadır, bildirim yerine geçmez.")
TALIMAT_NOTU_LISANSSIZ = ("Acil durum talimatının (DUY m.75) tutarı m.75(3) uyarınca ilgili toplayıcıya ya da görevli tedarik şirketine, onlardan tesis "
                          "sahibine yansıtılır; talimatın yerine getirilmeyen kısmına karşılık gelen üretim için ödeme yapılmaz (LÜY Ek m.4(1), RG 19.10.2026-33405). "
                          "Yerine getirilen talimat miktarı uzlaştırmaya esas veriş miktarı ve KGÜP ile tespit edilir (DUY m.107(3), m.104(3)). PVQuant talimat "
                          "tutarını hesaplamaz; GTŞ/toplayıcı bildirimi ya da faturası esastır.")   # v2.538 (EK-3 DK-733/DK-740, kanıt A)
TALIMAT_NOTU_LISANSLI = ("YAL/YAT talimat tutarları dengeleme güç piyasası uzlaştırmasında hesaplanır (DUY m.75–78); PVQuant talimat miktarını veri olarak "
                         "almaz, talimat saatlerinde program sapması talimattan sayılır ve kullanılabilirlik istisnasına girer.")


def _tarih(v) -> datetime | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        t = v
    else:
        try:
            t = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("tarih ISO biçiminde olmalı (YYYY-MM-DDTHH:MM, Türkiye saati ya da saat dilimli)")
    if t.tzinfo is None:
        t = t.replace(tzinfo=IST)
    return t.astimezone(timezone.utc)


def dogrula(g: dict, kapasite_kw: float | None = None, bugun: datetime | None = None) -> dict:
    """Giriş doğrulaması: tür, başlangıç (gelecekte en çok 400 gün — planlı bakım ileri tarihli olabilir), bitiş > başlangıç, etkilenen kW
    0–sınır (AC sınırı varsa o, yoksa kurulu güç; `_sinir_kw`), gerekçe sütunu türün kuralına uygun, metinler ≤ 500."""
    tur = g.get("tur")
    if tur not in TURLER:
        raise ValueError(f"tur {' / '.join(TURLER)} olmalı")
    bas = _tarih(g.get("baslangic"))
    if bas is None:
        raise ValueError("baslangic gerekli")
    simdi = bugun or datetime.now(timezone.utc)
    if bas > simdi + timedelta(days=400):
        raise ValueError("baslangic 400 günden ileri olamaz")
    bit = _tarih(g.get("bitis"))
    if bit is not None and bit <= bas:
        raise ValueError("bitis başlangıçtan sonra olmalı")
    kw = g.get("etkilenen_kw")
    if kw in (None, ""):
        kw = None
    else:
        try:
            kw = float(kw)
        except (TypeError, ValueError):
            raise ValueError("etkilenen_kw sayı olmalı")
        if kw <= 0 or (kapasite_kw and kw > kapasite_kw * 1.0001):
            raise ValueError(f"Devre dışı güç 0–{kapasite_kw:,.0f} kW aralığında olmalı (santralın verebileceği en yüksek güç, AC); tesisin tamamı için boş bırakın".replace(",", ".")
                             if kapasite_kw else "Devre dışı güç 0'dan büyük olmalı")
    kural = TUR_KURAL[tur]
    ger = g.get("eak_gerekcesi") or None
    if ger is not None and ger not in GEREKCELER:
        raise ValueError(f"eak_gerekcesi {' / '.join(GEREKCELER)} olmalı")
    if not kural["eak_dusur"]:
        ger = None
    elif ger is None:
        ger = kural["gerekce"]
    for ad in ("neden", "kanit"):
        if g.get(ad) is not None and len(str(g[ad])) > 500:
            raise ValueError(f"{ad} en çok 500 karakter")
    # v2.541 (DK-741): sona erme bildirimi yalnız acil durum kesmesinde; başlangıçtan önce olamaz
    bildirim = _tarih(g.get("bildirim_zamani")) if tur == "acil_kesme" else None
    if bildirim is not None and bildirim < bas:
        raise ValueError("bildirim_zamani başlangıçtan önce olamaz")
    # v2.541 (DK-743/DK-056): talimat miktarı (MW) yalnız YAL/YAT; kayıt amaçlı
    tmw = g.get("talimat_mw") if tur in ("talimat_yat", "talimat_yal") else None
    if tmw in (None, ""):
        tmw = None
    else:
        try:
            tmw = float(tmw)
        except (TypeError, ValueError):
            raise ValueError("talimat_mw sayı olmalı (MW)")
        if tmw <= 0:
            raise ValueError("talimat_mw 0'dan büyük olmalı (MW)")
    return {"tur": tur, "baslangic": bas, "bitis": bit, "etkilenen_kw": kw, "neden": (str(g.get("neden") or "").strip() or None),
            "eak_gerekcesi": ger, "kanit": (str(g.get("kanit") or "").strip() or None), "bildirim_zamani": bildirim, "talimat_mw": tmw}


def _sinir_kw(plant: dict) -> float | None:
    """Devre dışı güç üst sınırı: AC sınırı (invertör çıkışı) varsa o, yoksa kurulu güç (kWp). Günün EAK tabanı da bu sınırdan büyük olamaz."""
    v = float(plant.get("ac_limit_kw") or 0) or float(plant.get("capacity_kwp") or 0)
    return v or None


def _satir(r) -> dict:
    d = dict(r._mapping) if hasattr(r, "_mapping") else dict(r)
    bz_dt = d.get("bildirim_zamani") if isinstance(d.get("bildirim_zamani"), datetime) else None
    bit_dt = d.get("bitis") if isinstance(d.get("bitis"), datetime) else None
    bas_dt = d.get("baslangic") if isinstance(d.get("baslangic"), datetime) else None
    for k in ("baslangic", "bitis", "olusturma", "guncelleme", "bildirim_zamani"):
        v = d.get(k)
        d[k] = v.astimezone(IST).isoformat(timespec="minutes") if isinstance(v, datetime) else None
    # v2.541 (DK-741): bildirim gecikmesi = bildirim − bitiş (dk); 15 dk aşıldı mı. (DK-743): talimatta gerekçe son günü = olayı takip eden 3 iş günü
    d["bildirim_gecikme_dk"] = int(round((bz_dt - bit_dt).total_seconds() / 60)) if (bz_dt and bit_dt) else None
    d["bildirim_15dk_asildi"] = (d["bildirim_gecikme_dk"] > BILDIRIM_SURE_DK) if d["bildirim_gecikme_dk"] is not None else None
    if d.get("tur") in ("talimat_yat", "talimat_yal") and bas_dt is not None:
        from pvquant.ext.turkiye import takvim as tk
        d["gerekce_son_gunu"] = tk.is_gunu_ekle(bas_dt.astimezone(IST).date(), GEREKCE_IS_GUNU).isoformat()
    else:
        d["gerekce_son_gunu"] = None
    d.setdefault("talimat_mw", None)
    d["id"] = str(d["id"]); d["plant_id"] = str(d["plant_id"]); d.pop("tenant_id", None)
    d["olusturan"] = str(d["olusturan"]) if d.get("olusturan") else None
    d["tur_etiket"] = TUR_ETIKET.get(d["tur"], d["tur"]); d["kural"] = TUR_KURAL.get(d["tur"])
    d["acik"] = d["durum"] == "acik"
    d["evre"] = evre(r)   # 01.11 incelemesi: gelecekteki planlı bakım «açık/kapalı» değil «planlı»
    return d


def evre(r, simdi: datetime | None = None) -> str:
    """Görünen evre (DB durumu değişmez): iptal | planli (başlangıç gelecekte) | suruyor (başladı, bitmedi) | bitti."""
    m = r._mapping if hasattr(r, "_mapping") else r
    now = simdi or datetime.now(timezone.utc)
    if m["durum"] == "iptal":
        return "iptal"
    bas = m["baslangic"] if isinstance(m["baslangic"], datetime) else datetime.fromisoformat(str(m["baslangic"]))
    bit = m.get("bitis"); bit = (bit if isinstance(bit, datetime) else datetime.fromisoformat(str(bit))) if bit else None
    if bas > now:
        return "planli"
    return "suruyor" if (bit is None or bit > now) else "bitti"


def cakisanlar(tenant_id, plant_id, bas: datetime, bit: datetime | None, haric_id=None) -> list[dict]:
    """Aynı santralda aynı zaman aralığıyla kesişen (iptal edilmemiş) olaylar — çift sayım uyarısı için; engel değildir
    (aynı anda bir arıza ve bir şebeke kesintisi gerçek olabilir)."""
    son = bit or (bas + timedelta(days=400))
    try:
        liste = aralik(tenant_id, plant_id, bas, son)
    except Exception:   # noqa: BLE001
        return []
    return [_satir(o) for o in liste if str(o["id"]) != str(haric_id or "")]


def ekle(tenant_id, plant: dict, g: dict, olusturan=None) -> dict:
    v = dogrula(g, _sinir_kw(plant))
    cakisan = cakisanlar(tenant_id, plant["id"], v["baslangic"], v["bitis"])
    durum = "acik" if v["bitis"] is None or v["bitis"] > datetime.now(timezone.utc) else "kapali"
    try:
        import uuid as _uuid
        olusturan = str(_uuid.UUID(str(olusturan))) if olusturan else None
    except ValueError:
        olusturan = None
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("INSERT INTO olay(tenant_id, plant_id, tur, baslangic, bitis, etkilenen_kw, neden, eak_gerekcesi, kanit, durum, olusturan, bildirim_zamani, talimat_mw) "
                           "VALUES (:t, :p, :tur, :b, :e, :kw, :n, :g, :k, :d, :o, :bz, :tm) RETURNING *"),
                      {"t": tenant_id, "p": plant["id"], "tur": v["tur"], "b": v["baslangic"], "e": v["bitis"], "kw": v["etkilenen_kw"], "n": v["neden"],
                       "g": v["eak_gerekcesi"], "k": v["kanit"], "d": durum, "o": olusturan, "bz": v["bildirim_zamani"], "tm": v["talimat_mw"]}).first()
    out = _satir(r)
    if cakisan:
        out["uyari"] = (f"Aynı saatlerde {len(cakisan)} kayıt daha var ({', '.join(c['tur_etiket'] for c in cakisan[:3])}). Kayıtlar toplanır: ayrı ekipmanlar için "
                        "doğrudur; aynı ekipman için ikinci kayıt kapasiteyi iki kez düşürür (toplam günün EAK tabanını aşmaz). Yanlış girdiyseniz kaydı geçersiz sayın.")
        out["cakisan"] = [c["id"] for c in cakisan]
    return out


def guncelle(tenant_id, plant: dict, olay_id, g: dict) -> dict | None:
    """Bitiş (olayı kapatma), neden, kanıt, etkilenen kW, gerekçe ve iptal; tür ve başlangıç değişmez (yeni olay açılır)."""
    with tenant_baglami(tenant_id) as s:
        r = s.execute(text("SELECT * FROM olay WHERE id = :i AND plant_id = :p"), {"i": olay_id, "p": plant["id"]}).first()
        if r is None:
            return None
        m = dict(r._mapping)
        birlesik = {"tur": m["tur"], "baslangic": m["baslangic"], "bitis": g.get("bitis", m["bitis"]), "etkilenen_kw": g.get("etkilenen_kw", m["etkilenen_kw"]),
                    "neden": g.get("neden", m["neden"]), "eak_gerekcesi": g.get("eak_gerekcesi", m["eak_gerekcesi"]), "kanit": g.get("kanit", m["kanit"]),
                    "bildirim_zamani": g.get("bildirim_zamani", m.get("bildirim_zamani")), "talimat_mw": g.get("talimat_mw", m.get("talimat_mw"))}   # v2.541
        v = dogrula(birlesik, _sinir_kw(plant))
        durum = g.get("durum") or m["durum"]
        if durum not in DURUMLAR:
            raise ValueError("durum acik / kapali / iptal olmalı")
        if durum != "iptal":
            durum = "acik" if v["bitis"] is None or v["bitis"] > datetime.now(timezone.utc) else "kapali"
        r2 = s.execute(text("UPDATE olay SET bitis=:e, etkilenen_kw=:kw, neden=:n, eak_gerekcesi=:g, kanit=:k, durum=:d, bildirim_zamani=:bz, talimat_mw=:tm, guncelleme=now() "
                            "WHERE id=:i AND plant_id=:p RETURNING *"),
                       {"e": v["bitis"], "kw": v["etkilenen_kw"], "n": v["neden"], "g": v["eak_gerekcesi"], "k": v["kanit"], "d": durum, "i": olay_id, "p": plant["id"],
                        "bz": v["bildirim_zamani"], "tm": v["talimat_mw"]}).first()
    return _satir(r2)


def listele(tenant_id, plant_id, gun: int = 90, iptal_dahil: bool = False) -> list[dict]:
    """Son `gun` günde başlayan ya da hâlâ açık olaylar (en yeni önce); iptal edilenler istenirse."""
    bas = datetime.now(timezone.utc) - timedelta(days=gun)
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text("SELECT * FROM olay WHERE plant_id = :p AND (baslangic >= :b OR durum = 'acik' OR bitis >= :b) "
                              + ("" if iptal_dahil else "AND durum <> 'iptal' ") + "ORDER BY baslangic DESC, olusturma DESC LIMIT 500"),
                         {"p": plant_id, "b": bas}).fetchall()
    return [_satir(r) for r in rows]


def aralik(tenant_id, plant_id, bas: datetime, bit: datetime, turler=None) -> list[dict]:
    """[bas, bit) ile kesişen iptal edilmemiş olaylar (açık olay = bitiş yok)."""
    with tenant_baglami(tenant_id) as s:
        rows = s.execute(text("SELECT * FROM olay WHERE plant_id = :p AND durum <> 'iptal' AND baslangic < :bit AND (bitis IS NULL OR bitis > :bas) "
                              + ("AND tur = ANY(:t) " if turler else "") + "ORDER BY baslangic"),
                         {"p": plant_id, "bas": bas, "bit": bit, **({"t": list(turler)} if turler else {})}).fetchall()
    return [dict(r._mapping) for r in rows]


def saatlik_etki(tenant_id, plant: dict, gun: date) -> dict:
    """Günün 24 saati (Türkiye) için olay kaynaklı kapasite düşümü: saat → {toplam_kw, gerekce → kw, olaylar, oran}. Saat içinde kısmen süren
    olay o saatin düşümünü süreyle orantılı etkiler (09:40'ta başlayan olay 9. saatte 20/60; TPYS EAK saatliktir, program MWh/saat olduğu için
    ortalama kullanılabilir güç). Devre dışı güç boşsa tesisin tamamı = günün EAK tabanı (AC sınırı / EAK alanı / kurulu güç; kWp değil).
    Aynı saatte birden çok olay toplanır, EAK tabanını aşmaz; ekipman kimliği tutulmadığından aynı ekipmanı anlatan iki kayıt iki kez düşer (uyarı
    verilir, kullanıcı geçersiz sayar). Bitişi girilmemiş olay gün sonuna kadar sayılır (program ve EAK dosyası ileriye dönük). Yalnız eak_dusur
    türleri; iptal edilenler yok."""
    try:
        from pvquant.services import kgup_service
        taban_kw = float(kgup_service.eak_etkin(plant, gun)["eak_mw"]) * 1000.0
    except Exception:   # noqa: BLE001
        taban_kw = float(plant.get("capacity_kwp") or 0)
    g0 = datetime.combine(gun, datetime.min.time(), IST); g1 = g0 + timedelta(days=1)
    try:
        olaylar = aralik(tenant_id, plant["id"], g0.astimezone(timezone.utc), g1.astimezone(timezone.utc),
                         [t for t, k in TUR_KURAL.items() if k["eak_dusur"]])
    except Exception:   # noqa: BLE001 — tablo yoksa (göç öncesi) olay etkisi yok
        olaylar = []
    saatler: dict[int, dict] = {}
    for o in olaylar:
        kw = float(o["etkilenen_kw"]) if o["etkilenen_kw"] is not None else taban_kw
        ger = o["eak_gerekcesi"] or TUR_KURAL[o["tur"]]["gerekce"] or "kaynak_yetersizligi"
        ob = o["baslangic"].astimezone(IST); oe = (o["bitis"] or g1).astimezone(IST)
        for h in range(24):
            s0 = g0 + timedelta(hours=h); s1 = s0 + timedelta(hours=1)
            kesisim = (min(oe, s1) - max(ob, s0)).total_seconds() / 3600.0
            if kesisim <= 0:
                continue
            oran = min(1.0, kesisim)
            d = saatler.setdefault(h, {"toplam_kw": 0.0, "gerekce": {}, "olaylar": [], "oran": 0.0})
            d["toplam_kw"] = min(taban_kw, d["toplam_kw"] + kw * oran) if taban_kw else d["toplam_kw"] + kw * oran
            d["gerekce"][ger] = d["gerekce"].get(ger, 0.0) + kw * oran
            d["olaylar"].append(str(o["id"])); d["oran"] = max(d["oran"], oran)
    for d in saatler.values():
        d["toplam_kw"] = round(d["toplam_kw"], 1); d["gerekce"] = {k: round(v, 1) for k, v in d["gerekce"].items()}
    return {"gun": gun.isoformat(), "saatler": saatler, "olay_sayisi": len(olaylar), "taban_kw": round(taban_kw, 1),
            "kaynak": "olay kaydı (planlı bakım, arıza, acil kesme, şebeke kesintisi, hasar); kısmi saat süreyle orantılı; sınır günün EAK tabanı"}


def istisna_saatleri(tenant_id, plant_id, bas: datetime, bit: datetime) -> set:
    """Kullanılabilirlik hesabından düşülecek saatler (UTC saat başı): istisna türlerindeki olayların kapsadığı saatler."""
    try:
        olaylar = aralik(tenant_id, plant_id, bas, bit, [t for t, k in TUR_KURAL.items() if k["istisna"]])
    except Exception:   # noqa: BLE001
        return set()
    out = set()
    for o in olaylar:
        t = o["baslangic"].astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
        son = (o["bitis"] or bit).astimezone(timezone.utc)
        while t < son and t < bit:
            if t >= bas:
                out.add(t)
            t += timedelta(hours=1)
    return out


def ariza_sayisi(tenant_id, plant_id, ay: date | None = None) -> int:
    """Ayda başlayan, iptal edilmemiş arıza olayları (Karar 14907: UEVÇB'de ayda 30 ve üzeri → n 0,08)."""
    a0 = (ay or datetime.now(IST).date()).replace(day=1)
    a1 = (a0 + timedelta(days=32)).replace(day=1)
    try:
        with tenant_baglami(tenant_id) as s:
            n = s.execute(text("SELECT count(*) FROM olay WHERE plant_id = :p AND tur = 'ariza' AND durum <> 'iptal' AND baslangic >= :a AND baslangic < :b"),
                          {"p": plant_id, "a": datetime.combine(a0, datetime.min.time(), IST), "b": datetime.combine(a1, datetime.min.time(), IST)}).scalar()
        return int(n or 0)
    except Exception:   # noqa: BLE001
        return 0


def ariza_sayisi_etkin(tenant_id, plant: dict, ay: date | None = None) -> dict:
    """KÜPST n ve alarm için kullanılan aylık arıza sayısı: olay kaydındaki arıza sayısı ile Santral ayarlarındaki elle girilen sayının büyüğü
    (elle giriş yedek; olay kaydı tutulmaya başlanınca onu geçer). Kaynak söylenir."""
    pj = plant.get("params_json") or {}
    if isinstance(pj, str):
        pj = json.loads(pj)
    elle = int(pj.get("ariza_sayisi_ay") or 0)
    olay = ariza_sayisi(tenant_id, plant["id"], ay)
    return {"sayi": max(elle, olay), "olay": olay, "elle": elle, "kaynak": "olay kaydı" if olay >= elle and olay > 0 else ("elle giriş" if elle > 0 else "yok")}


def dahili_bilgi(olay: dict, kapasite_kw: float, portfoy_kw: float | None = None, simdi: datetime | None = None, yek_g: bool = False) -> dict | None:
    """Karar 14967 1 saat kuralı: etkilenen güç (boşsa kurulu güç) tesis eşiğinde ya da portföy açık olay toplamı portföy eşiğinde ise
    son açıklama saati ve kalan süre; eşik altındaysa None. v2.538 (DK-613): yürürlük 01.01.2027 (çıkarım); olay başlangıcı bu tarihten
    önceyse `basladi` False ve hatırlatma bilgi amaçlıdır (zorunlu süre henüz yok)."""
    if olay.get("tur") not in ("planli_bakim", "ariza", "acil_kesme", "sebeke_kesintisi", "hasar"):
        return None
    kw = float(olay["etkilenen_kw"]) if olay.get("etkilenen_kw") else float(kapasite_kw or 0)
    tesis = kw >= DAHILI_TESIS_KW; portfoy = portfoy_kw is not None and portfoy_kw >= DAHILI_PORTFOY_KW
    yek_g_sira17 = bool(yek_g) and olay.get("tur") == "ariza" and not (tesis or portfoy)   # v2.540 (DK-612): eşik altı arıza, YEK-G kayıtlı tesis
    if not (tesis or portfoy or yek_g_sira17):
        return None
    bas = olay["baslangic"] if isinstance(olay["baslangic"], datetime) else datetime.fromisoformat(olay["baslangic"])
    son = bas + timedelta(hours=DAHILI_SURE_SAAT); now = simdi or datetime.now(timezone.utc)
    basladi = bas.astimezone(IST).date() >= DAHILI_YURURLUK
    return {"esik": "tesis 30 MW" if tesis else ("portföy 50 MW" if portfoy else "YEK-G sıra 17 (eşik yok)"), "etkilenen_kw": kw, "son_saat": son.astimezone(IST).isoformat(timespec="minutes"),
            "kalan_dk": int((son - now).total_seconds() // 60), "gecti": now > son, "yururluk": DAHILI_YURURLUK_ETIKET, "basladi": basladi,
            "kosul": (DAHILI_YEK_G_NOTU if yek_g_sira17 else None),
            "yururluk_notu": DAHILI_YURURLUK_NOTU if basladi else ("Yükümlülük 01.01.2027'de başlar (çıkarım): bu olay için zorunlu 1 saatlik süre henüz yok; "
                                                                   "hatırlatma bilgi amaçlıdır. " + DAHILI_YURURLUK_NOTU),
            "not": DAHILI_NOTU}


def ozet(tenant_id, plant: dict, gun: int = 90, bugun: date | None = None) -> dict:
    """Müşteri ucu: olay listesi, açık olaylar, bu ayın arıza sayacı (eşik 30, uyarı 25), bugünkü EAK etkisi, dâhilî bilgi hatırlatmaları."""
    b = bugun or datetime.now(IST).date()
    olaylar = listele(tenant_id, plant["id"], gun)
    acik = [o for o in olaylar if o["evre"] == "suruyor"]
    planli = [o for o in olaylar if o["evre"] == "planli"]
    kap = _sinir_kw(plant) or 0.0   # tesisin tamamı = AC sınırı (varsa); kWp değil
    portfoy_kw = sum((float(o["etkilenen_kw"]) if o["etkilenen_kw"] else kap) for o in acik)
    pj0 = plant.get("params_json") or {}
    if isinstance(pj0, str):
        pj0 = json.loads(pj0)
    yek_g = bool(pj0.get("yek_g_kayitli"))   # v2.540 (DK-612): beyan
    dahili = []
    for o in acik:
        d = dahili_bilgi(o, kap, portfoy_kw if len(acik) > 1 else None, yek_g=yek_g)
        if d:
            dahili.append({"olay_id": o["id"], "tur": o["tur_etiket"], **d})
    sayac = ariza_sayisi_etkin(tenant_id, plant, b)
    etki = saatlik_etki(tenant_id, plant, b)
    from pvquant.services import dengesizlik_service
    seg = dengesizlik_service.segment_bilgisi(plant.get("params_json")).get("segment")   # v2.538 (DK-733/DK-740): talimat notu segmente göre
    lisanssiz = seg in ("lisanssiz_dagitim", "lisanssiz_iletim")
    kn = _kupst_n(seg, b)   # v2.600 (F4-F): eşik ve katsayılar kural sicilinden; 25 ürün ön uyarısı (mevzuat eşiği değil)
    return {"bugun": b.isoformat(), "pencere_gun": gun, "olaylar": olaylar, "acik": len(acik), "planli": len(planli), "ariza_sayaci": {**sayac, "esik": kn["ariza_esigi"] or 30, "uyari": 25, "ay": b.strftime("%Y-%m"), **kn},
            "eak_bugun": {"saat_sayisi": len(etki["saatler"]), "en_cok_kw": max((v["toplam_kw"] for v in etki["saatler"].values()), default=0.0),
                          "taban_kw": etki["taban_kw"], "kismi_saat": sum(1 for v in etki["saatler"].values() if v["oran"] < 1.0),
                          "suren": sum(1 for o in acik if o["kural"]["eak_dusur"] and not o["bitis"])},   # bitişi girilmemiş: gün sonuna kadar sayılır
            "dahili_bilgi": dahili, "dahili_yururluk": {"tarih": DAHILI_YURURLUK.isoformat(), "etiket": DAHILI_YURURLUK_ETIKET, "basladi": b >= DAHILI_YURURLUK, "not": DAHILI_YURURLUK_NOTU},
            "yek_g_kayitli": yek_g, "yek_g_notu": DAHILI_YEK_G_NOTU,
            "segment": seg, "turler": [{"kod": t, "etiket": TUR_ETIKET[t], **TUR_KURAL[t]} for t in TURLER],
            "gerekceler": [{"kod": g, "etiket": GEREKCE_ETIKET[g]} for g in GEREKCELER],
            "not": "Olay kaydı santralın kendi kaydıdır; TPYS Arıza ve Bakım bildirimi, Dâhilî Bilgi Platformu açıklaması ve TEİAŞ bildirimleri ayrıca yapılır.",
            "aciklama": {"kapasite": "Planlı bakım, arıza, acil kesme, şebeke kesintisi ve hasar o saatlerde verilebilecek gücü (EAK) ve programın tavanını düşürür; saat içinde kısmen süren olay "
                                     "süreyle orantılı düşer; bitişi girilmemiş olay gün sonuna kadar sayılır. Birden çok olay toplanır (ayrı ekipmanlar için doğrudur; aynı ekipmanı "
                                     "anlatan iki kayıt iki kez düşer, kayıt ekipman ayrımı tutmaz), toplam günün EAK tabanını (AC sınırı ya da EAK alanı) aşmaz. Talimatlar (YAL/YAT) kapasiteyi değiştirmez. Şebeke kesintisi ve hasarın EAK'yi düşürmesi tanımdan çıkarım, acil kesme varsayımdır (TEİAŞ teyidine kadar); tür → gerekçe eşlemesi ürün varsayılanıdır.",
                         "sayac": _sayac_metni(kn),
                         "kullanilabilirlik": "Planlı bakım, talimat, acil kesme ve şebeke kesintisi saatleri kullanılabilirlik hesabından düşülür (santralın elinde değil); arıza ve hasar arıza sayılır.",
                         "islem": "«Bitir» olayın bittiğini işler, kayıt hesaplarda kalır. «Geçersiz say» yanlış kaydı hesaplardan çıkarır; kayıt silinmez, dosyada «geçersiz» olarak görünür. "
                                  "Başlangıç ve tür değiştirilemez; yanlışsa kaydı geçersiz sayıp yenisini açın. Her ekleme ve değişiklik denetim izinde tutulur.",
                         "gerekce": "EAK gerekçesi TPYS EAK dosyasındaki sütundur; tür için varsayılan önerilir, kayıt girilirken değiştirilebilir. «Mücbir sebep» yalnız mevzuattaki koşullar (Lisans Yön. m.35(2)–(3)) "
                                    "sağlanıyorsa seçilir; EAK sütunu ile EPDK'ya m.35 başvurusu ayrı süreçlerdir; hasar tek başına mücbir sebep değildir.",
                         "talimat": TALIMAT_NOTU_LISANSSIZ if lisanssiz else TALIMAT_NOTU_LISANSLI,
                         "bildirim": LUY_M21_8_NOTU + " " + DUY_M71A_NOTU}}   # v2.541 (DK-741/DK-743)


def csv_metni(olaylar: list[dict], plant_ad: str) -> str:
    """Hasar / sigorta dosyası: olay listesi (UTF-8 BOM, ; ayraç, Türkçe saat)."""
    kol = ["santral", "tur", "baslangic", "bitis", "sure_saat", "etkilenen_kw", "neden", "eak_gerekcesi", "kanit", "evre", "olusturma",
           "bildirim_zamani", "bildirim_gecikme_dk", "talimat_mw", "gerekce_son_gunu"]   # v2.541
    satirlar = []
    for o in olaylar:
        b = datetime.fromisoformat(o["baslangic"]); e = datetime.fromisoformat(o["bitis"]) if o["bitis"] else None
        satirlar.append({"santral": plant_ad, "tur": o["tur_etiket"], "baslangic": o["baslangic"], "bitis": o["bitis"] or "",
                         "sure_saat": round((e - b).total_seconds() / 3600, 2) if e else "", "etkilenen_kw": o["etkilenen_kw"] if o["etkilenen_kw"] is not None else "",
                         "neden": o["neden"] or "", "eak_gerekcesi": GEREKCE_ETIKET.get(o["eak_gerekcesi"] or "", ""), "kanit": o["kanit"] or "",
                         "evre": {"planli": "planlı", "suruyor": "sürüyor", "bitti": "bitti", "iptal": "geçersiz"}[o.get("evre") or evre(o)], "olusturma": o["olusturma"],
                         "bildirim_zamani": o.get("bildirim_zamani") or "", "bildirim_gecikme_dk": o.get("bildirim_gecikme_dk") if o.get("bildirim_gecikme_dk") is not None else "",
                         "talimat_mw": o.get("talimat_mw") if o.get("talimat_mw") is not None else "", "gerekce_son_gunu": o.get("gerekce_son_gunu") or ""})
    buf = io.StringIO()
    pd.DataFrame(satirlar, columns=kol).to_csv(buf, sep=";", decimal=",", index=False, lineterminator="\n")
    return "﻿" + buf.getvalue()


def _kupst_n(segment: str | None, gun) -> dict:
    """v2.600 (F4-F): arıza eşiği ve KÜPST n katsayıları kural sicilinden (ekran sabiti değil). `karar`: dayanaktaki karar numarası
    («Karar 14907»); yoksa None. n_ariza None → bu segmentte arıza sayacı katsayıyı değiştirmez."""
    import re as _re
    from pvquant.ext.turkiye import kurallar as kr
    k = kr.kupst_kurali(gun, segment)
    m = _re.search(r"Karar \d{4,5}", k.dayanak or "")
    return {"n": k.n, "n_ariza": k.n_ariza, "ariza_esigi": k.ariza_esigi, "kural_surumu": k.surum, "karar": m.group(0) if m else None}


def _tr(x) -> str:
    return f"{x:.2f}".replace(".", ",")


def _sayac_metni(kn: dict) -> str:
    """Olay özeti «sayaç» açıklaması: katsayılar ve eşik sicilden; kural yoksa sayı basılmaz (dürüstlük anayasası)."""
    if kn["n_ariza"] is None or kn["ariza_esigi"] is None:
        return ("Yalnız «arıza» türü aylık sayaca girer. Bu segmentte arıza sayısı KGÜP sapma tutarı katsayısını değiştirmez"
                f"{' (' + kn['karar'] + ')' if kn['karar'] else ''}; 25'te ürün ön uyarısı (mevzuat eşiği değil). Sayaç EPİAŞ sayımına vekildir.")
    return (f"Yalnız «arıza» türü aylık sayaca girer. Ayda {kn['ariza_esigi']} ve üzeri arıza kaydı KGÜP sapma tutarı katsayısını {_tr(kn['n'])}'ten "
            f"{_tr(kn['n_ariza'])}'e çıkarır{' (' + kn['karar'] + ')' if kn['karar'] else ''}; 25'te ürün ön uyarısı (mevzuat eşiği değil). Sayaç EPİAŞ sayımına vekildir.")
