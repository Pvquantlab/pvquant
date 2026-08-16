# -*- coding: utf-8 -*-
"""denetim.py — rapor verisinin İÇ TUTARLILIK denetimi (saf modül).

Hiçbir sayfa üretilmeden ÖNCE koşar. Girdi, veri.py'nin yüklediği veri
yüzeyidir (modül ya da sözlük). Tek bir seviye="hata" bulgusu rapor
üretimini durdurur; eşik gevşetmek, alan ikame etmek, eksiği sıfırla
doldurmak YASAKTIR (görev kuralı).

Kontroller
----------
D1  Σ günlük P50 == dönem toplamı                     tolerans 0,1 MWh
D2  şelale: fizik + Σ adım == holdout                 tolerans 0,1 puan
D3  saat×gün matrisi sütun toplamı == günlük P50      tolerans 0,1 MWh
    (matris s06 ile aynı formülle, MATRIS_OLCEK_MWH üzerinden kurulur)
D4  karne satırı: skill == 1 − wmape/naif             tolerans 0,5 puan
    (v2.137: naif ÖLÇÜMdür — KARNE_NAIF; türetilmişse totoloji uyarısı)
D5  kalibrasyon saati <= pencere_gün × 14  (pencere KART İDDİASINDAN okunur)
D6  SCADA arşiv saati <= dönem_gün × 24 × 1,01  (v2.132: üst-sınır — aşım imkânsızdır)
D7  katsayı aralıkları: η_BoS ∈ [0,80–0,98] · bifacial ∈ [%0–12]
    aralık dışı → hata + "şüpheli kalibrasyon" bayrağı (denetim.json)
D8  saatlik profil tek tepeli: gündüz saatlerinde yerel minimum yok
D9  gösterilen tarihler ∈ [tahmin başı, tahmin sonu]
    (v2.131: s05 panelleri ve s14 hedefi GUN_ETIKET + AY_YIL ayından
     basılır; ay-sınırı aşan dönemde yanlış ay adı burada yakalanır)
D10 zorunlu-alan varlığı: tükettiği alan yokken gösterge/cümle üretilmez
D11 iklim: matris son satiri=zarf ortasi (LTA tam-yil ortalamasindan; kismi yil yasak)
D12 selale iyilesme yuzdesi bas/sondan yeniden uretilebilir
D13 tepe guc <= kurulu DC guc
D14 profil surekliligi: ardisik sicrama <= kurulu DC'nin %30'u (v2.136 tanim duzeltmesi)
D15 karne penceresi ∩ SCADA arsiv donemi ≠ ∅
D16 KPI durum rengi esik yonuyle tutarli + kesintisiz karti alansiz basilamaz
D17 yillik Pxx = ORT - z·SD yeniden uretilebilir (SD orneklem n-1; z sozlesmeli)
D18 karne butunlugu: 30 takvim satiri; olculdu↔null tutarli; KESINTISIZ ↔ kuyruk
R1/R2 (render, sayfalar sonrasi): doldurulmamis token yok; s02/s15 sayfa
    referanslari 1..16 icinde — render_denetle(cikti_dizin)
    (MWe → kapak {{KURULU}}, s05 {{SEBEKE}} cümlesi, kapasite faktörü)

Not (D7 özel kuralı): "Bu raporda böyle bir işaret yoktur." cümlesi
build_s09.py:163'te sabit kopyadır ve kapsam gereği DOKUNULMAZ. Koşulluluk
kapıyla sağlanır: D7 hatası raporu tümden engellediğinden bu cümle yalnız
D7'yi geçmiş raporlarda basılabilir; bayrak denetim.json'a yazılır.
"""
from dataclasses import dataclass, asdict
import datetime as _dt
import json as _json
import re as _re

# ---------------------------------------------------------------- sabitler
GUNDUZ_SAAT_TAVAN = 14    # gündüz saati üst sınırı (D5: gün × 14)
ETA_ARALIK = (0.80, 0.98)
BIF_ARALIK = (0.0, 12.0)
S05_PANEL = 8             # build_s05: ilk sekiz günün paneli (v2.131: başlık
                          # GUN_ETIKET[k] + AY_YIL ayı — veri-güdümlü)
AYLAR = ["ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz",
         "ağustos", "eylül", "ekim", "kasım", "aralık"]


@dataclass
class Bulgu:
    kod: str
    seviye: str          # "hata" | "uyari"
    mesaj: str
    beklenen: str
    bulunan: str


# ---------------------------------------------------------------- yardımcılar
def _al(veri, ad, varsayilan=None):
    """Modülden (getattr) ya da sözlükten (get) alan okur."""
    if isinstance(veri, dict):
        return veri.get(ad, varsayilan)
    return getattr(veri, ad, varsayilan)


def _tr(x, d=1):
    try:
        return ("%.*f" % (d, float(x))).replace(".", ",")
    except (TypeError, ValueError):
        return str(x)


def _sayi(s):
    """Türkçe biçimli sayı metni → float. Yok/'—'/çözümlenemez → None.
    '1.487'→1487 · '0,942'→0.942 · '%7,3'→7.3 · '4.440'→4440"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s).replace("%", "").replace("\u00a0", " ").strip()
    if t in ("", "—", "–", "-"):
        return None
    if "," in t:                                   # virgül = ondalık
        t = t.replace(".", "").replace(",", ".")
    elif _re.fullmatch(r"\d{1,3}(\.\d{3})+", t) and not t.startswith("0."):
        t = t.replace(".", "")                     # nokta = binlik
    try:
        return float(t)
    except ValueError:
        return None


def _ay_no(ad):
    ad = ad.strip().lower().replace("i̇", "i")
    for i, tam in enumerate(AYLAR):
        if ad == tam or (len(ad) >= 3 and tam.startswith(ad[:3])):
            return i + 1
    return None


def _arsiv_coz(etiket):
    """'1 Şubat – 4 Ağustos 2026\\n (4.440 saat)' → (tarih1, tarih2, saat)."""
    if not etiket:
        return None
    t = " ".join(str(etiket).split())
    m = _re.search(r"(\d{1,2})\s+(\S+?)(?:\s+(\d{4}))?\s*[–—-]\s*"
                   r"(\d{1,2})\s+(\S+?)\s+(\d{4})", t)
    h = _re.search(r"\(\s*([\d.\s]+?)\s*saat\s*\)", t)
    if not (m and h):
        return None
    a1, a2 = _ay_no(m.group(2)), _ay_no(m.group(5))
    saat = _sayi(h.group(1).strip())
    if a1 is None or a2 is None or saat is None:
        return None
    y2 = int(m.group(6))
    y1 = int(m.group(3)) if m.group(3) else y2
    try:
        return (_dt.date(y1, a1, int(m.group(1))),
                _dt.date(y2, a2, int(m.group(4))), saat)
    except ValueError:
        return None


# ---------------------------------------------------------------- kontroller
def _d1(veri, ekle):
    p50, top = _al(veri, "P50_GUN") or [], _al(veri, "TOPLAM_P50_MWH")
    if not p50 or top is None:
        return ekle("D1", "uyari", "günlük seri ya da dönem toplamı yok — denetlenemedi",
                    "P50_GUN + TOPLAM_P50_MWH", "eksik")
    s = sum(p50)
    if abs(s - top) <= 0.1:
        return ekle("D1", "gecti", "Σ günlük P50 dönem toplamıyla örtüşüyor",
                    _tr(top) + " MWh (±0,1)", _tr(s) + " MWh")
    ekle("D1", "hata", "günlük P50 toplamı dönem toplamını tutmuyor",
         _tr(top) + " MWh (±0,1)", _tr(s) + " MWh")


def _d2(veri, ekle):
    bas, bit = _al(veri, "SELALE_BAS"), _al(veri, "SELALE_BIT")
    adimlar = _al(veri, "SELALE_ADIM")   # v2.134: 'or []' None işaretini yutuyordu
    deltalar = [d for (_ad, d, _k) in (adimlar or []) if d is not None]
    if adimlar is None:
        # v2.132: adım kırılımı girdide yok → motor şelaleyi BASMAZ
        # ("veri eksik" satırı) — kapanmayan bir şelale basılamıyorsa
        # D2'nin engelleyeceği bir iddia da yoktur; kayıt uyarıyla düşer.
        return ekle("D2", "uyari", "şelale adımsız — basılmaz, 'veri eksik' satırı çıkar",
                    "calibration.steps", "yok (şelale basılmadı)")
    if bas is None or bit is None or not deltalar:
        return ekle("D2", "uyari", "şelale uçları ya da adımları yok — denetlenemedi",
                    "physics_mape + steps + holdout_mape", "eksik")
    s = bas + sum(deltalar)
    if abs(s - bit) <= 0.1:
        return ekle("D2", "gecti", "şelale kapanıyor: fizik + Σ adım = holdout",
                    _tr(bit) + " puan (±0,1)", _tr(s) + " puan")
    ekle("D2", "hata",
         "şelale kapanmıyor: fizik (%s) + Σ adım (%s) ≠ holdout — arkasında "
         "adım olmayan sıçrama var" % (_tr(bas), _tr(sum(deltalar))),
         _tr(bit) + " puan (±0,1)", _tr(s) + " puan")


def _d3(veri, ekle):
    taban, p50 = _al(veri, "BASE_KW") or [], _al(veri, "P50_GUN") or []
    if not taban or not p50:
        return ekle("D3", "uyari", "saatlik taban ya da günlük seri yok — denetlenemedi",
                    "BASE_KW + P50_GUN", "eksik")
    # v2.131: ölçek türetilen MATRIS_OLCEK_MWH'den (s06 aynası). Yüzeyde
    # yoksa aynı tanımla (Σbase/1000) türetilir. Sabit-bölen kusur sınıfı
    # kurulumla yok edildi; D3 artık yüzeydeki ölçeğin taban eğrisiyle
    # tutarlılığını bekçiler (bayat/elle ölçek sürülürse yakalar).
    olcek = _al(veri, "MATRIS_OLCEK_MWH") or (sum(taban) / 1000.0)
    kotu = []
    for d, gun in enumerate(p50):
        sutun = sum(v * gun / olcek for v in taban) / 1000.0
        if abs(sutun - gun) > 0.1:
            kotu.append((d, gun, sutun))
    if not kotu:
        return ekle("D3", "gecti", "matris sütun toplamları günlük P50 ile örtüşüyor",
                    "her gün: günlük P50 (±0,1 MWh)", "%d/%d sütun uyumlu" % (len(p50), len(p50)))
    d, gun, sutun = kotu[0]
    ekle("D3", "hata",
         "saat×gün matrisi sütunları günlük değeri tutmuyor (%d gün uyumsuz; ilki: %d. gün)"
         % (len(kotu), d + 1),
         _tr(gun) + " MWh (±0,1)", _tr(sutun) + " MWh")


def _d4(veri, ekle):
    """v2.137 (Faz B1): naif ARTIK OLCUMDUR (KARNE_NAIF, skill_daily.naive_wmape).
    Ozdeslik skill = 1 - wmape/naif uc bagimsiz sayi arasinda GERCEK denetime
    donustu. Naif hala turetilmisse (eski girdi) ozdeslik totolojiktir -> uyari."""
    wm, sk = _al(veri, "KARNE_WM") or [], _al(veri, "KARNE_SK") or []
    naif = _al(veri, "KARNE_NAIF") or []
    kaynak = _al(veri, "KARNE_NAIF_KAYNAK")
    if not wm or not sk or len(wm) != len(sk) or len(naif) != len(wm):
        return ekle("D4", "uyari", "karne serileri yok ya da uzunlukları farklı — denetlenemedi",
                    "KARNE_WM ↔ KARNE_SK ↔ KARNE_NAIF", "eksik/uyumsuz")
    if kaynak != "alan":
        return ekle("D4", "uyari", "naif girdide ölçüm olarak yok, türetildi — "
                    "özdeşlik totolojik, denetim anlamsız (kök iş: naif_wmape alanı)",
                    "KARNE_NAIF_KAYNAK='alan'", str(kaynak))
    olc = _al(veri, "KARNE_OLCULDU") or [True] * len(wm)
    kotu = []
    for i, (w, s, n) in enumerate(zip(wm, sk, naif)):
        if not (olc[i] if i < len(olc) else True):
            continue          # v2.140: ölçülmemiş gün özdeşliğe girmez (D18 bekçiler)
        if w is None or s is None:
            kotu.append((i, "ölçülü satırda değer yok")); continue
        if not (0.0 < s < 1.0):
            kotu.append((i, "skill ∉ (0,1): %s" % _tr(s, 3))); continue
        if n is None or n <= 0:
            kotu.append((i, "naif ≤ 0/yok")); continue
        if abs(s - (1.0 - w / n)) > 0.005:      # 0,5 puan
            kotu.append((i, "skill=%s ≠ 1−%s/%s" % (_tr(s, 2), _tr(w), _tr(n))))
    if not kotu:
        return ekle("D4", "gecti", "her karne satırında skill = 1 − wmape/naif "
                    "(naif ölçüm)", "±0,5 puan", "%d/%d satır uyumlu" % (len(wm), len(wm)))
    i, neden = kotu[0]
    ekle("D4", "hata",
         "karne satırı ölçülmüş naifle tutarsız (%d satır; ilki: %d. satır, %s)"
         % (len(kotu), i + 1, neden),
         "skill = 1 − wmape/naif (±0,5 puan)", "satır %d" % (i + 1))


def _d5(veri, ekle):
    saat = _sayi(_al(veri, "KAT_SAAT"))
    if saat is None:
        return ekle("D5", "uyari", "kalibrasyon saati alanı yok — denetlenemedi "
                    "(kartta '—' basılması dürüst-eksiklik kuralına uygundur)",
                    "kat_saat", "eksik")
    # v2.132: pencere GÖMÜLÜ 120 değil, kartın bastığı iddiadan (KAL_PENCERE
    # ", N gün") okunur. İddia yoksa kart pencere söylemiyor demektir —
    # uydurulmuş bir pencereye karşı denetlemek alan icat etmek olurdu.
    import re as _re2
    _kp = str(_al(veri, "KAL_PENCERE") or "")
    _m = _re2.search(r"(\d+)\s*gün", _kp)
    if not _m:
        return ekle("D5", "uyari", "pencere iddiası yok — saat tavanı denetlenemedi "
                    "(kart pencere söylemiyor; kök iş: pipeline pencereyi kayda yazmalı)",
                    "KAL_PENCERE (', N gün')", repr(_kp))
    pencere_gun = int(_m.group(1))
    tavan = pencere_gun * GUNDUZ_SAAT_TAVAN
    if saat <= tavan:
        return ekle("D5", "gecti", "kalibrasyon saati %d günlük pencereye sığıyor" % pencere_gun,
                    "≤ " + _tr(tavan, 0) + " saat (%d×%d)" % (pencere_gun, GUNDUZ_SAAT_TAVAN),
                    _tr(saat, 0) + " saat")
    ekle("D5", "hata",
         "%d günlük pencerede fiziksel olarak sığmayan gündüz saati" % pencere_gun,
         "≤ " + _tr(tavan, 0) + " saat (%d×%d)" % (pencere_gun, GUNDUZ_SAAT_TAVAN),
         _tr(saat, 0) + " saat")


def _d6(veri, ekle):
    coz = _arsiv_coz(_al(veri, "ARSIV_ETIKET"))
    if coz is None:
        return ekle("D6", "uyari", "arşiv etiketi yok ya da çözümlenemedi — denetlenemedi",
                    "'G Ay – G Ay YYYY (N saat)'", repr(_al(veri, "ARSIV_ETIKET"))[:60])
    t1, t2, saat = coz
    gun = (t2 - t1).days + 1
    kapasite = gun * 24
    # v2.132 ANLAM DÜZELTİMESİ (kayıtlı, gizli gevşetme değil): eşitlik±%1
    # kusursuz arşiv varsayıyordu; gerçek arşivlerde boşluk normaldir ve
    # kapsam s10'da zaten dürüstçe raporlanır. Aritmetik-imkânsız olan tek
    # şey kapasiteyi AŞMAKtır (10 Ağu vakası buydu) → üst-sınır denetimi.
    if kapasite > 0 and saat <= kapasite * 1.01:
        return ekle("D6", "gecti", "SCADA arşiv saati dönem kapasitesine sığıyor",
                    "≤ " + _tr(kapasite, 0) + " saat (%d gün × 24, +%%1)" % gun,
                    _tr(saat, 0) + " saat")
    ekle("D6", "hata",
         "SCADA arşiv saati dönem kapasitesini AŞIYOR (%s – %s = %d gün) — "
         "aritmetik olarak imkânsız" % (t1.isoformat(), t2.isoformat(), gun),
         "≤ " + _tr(kapasite, 0) + " saat (%d gün × 24, +%%1)" % gun,
         _tr(saat, 0) + " saat")


def _d7(veri, ekle):
    eta, bif = _sayi(_al(veri, "KAT_ETA")), _sayi(_al(veri, "KAT_BIF"))
    bayrak = False
    if eta is None:
        ekle("D7", "uyari", "η_BoS alanı yok — aralık denetlenemedi", "kat_eta", "eksik")
    elif ETA_ARALIK[0] <= eta <= ETA_ARALIK[1]:
        ekle("D7", "gecti", "η_BoS fiziksel aralıkta",
             "%s–%s" % (_tr(ETA_ARALIK[0], 2), _tr(ETA_ARALIK[1], 2)), _tr(eta, 3))
    else:
        bayrak = True
        ekle("D7", "hata", "η_BoS fiziksel aralığın dışında — ŞÜPHELİ KALİBRASYON bayrağı",
             "%s–%s" % (_tr(ETA_ARALIK[0], 2), _tr(ETA_ARALIK[1], 2)), _tr(eta, 3))
    if bif is None:
        ekle("D7", "uyari", "bifacial alanı yok — aralık denetlenemedi", "kat_bif", "eksik")
    elif BIF_ARALIK[0] <= bif <= BIF_ARALIK[1]:
        ekle("D7", "gecti", "bifacial kazanç fiziksel aralıkta",
             "%%%s–%%%s" % (_tr(BIF_ARALIK[0], 0), _tr(BIF_ARALIK[1], 0)), "%" + _tr(bif))
    else:
        bayrak = True
        ekle("D7", "hata", "bifacial kazanç fiziksel aralığın dışında — ŞÜPHELİ "
             "KALİBRASYON bayrağı", "%%%s–%%%s" % (_tr(BIF_ARALIK[0], 0), _tr(BIF_ARALIK[1], 0)),
             "%" + _tr(bif))
    return bayrak


def _d8(veri, ekle):
    taban = _al(veri, "BASE_KW") or []
    if len(taban) < 3:
        return ekle("D8", "uyari", "saatlik taban yok/kısa — denetlenemedi",
                    "BASE_KW (≥3 dilim)", "eksik")
    cukur = [i for i in range(1, len(taban) - 1)
             if taban[i] < taban[i - 1] and taban[i] < taban[i + 1]]
    if not cukur:
        return ekle("D8", "gecti", "saatlik profil tek tepeli (gündüz yerel minimumu yok)",
                    "yerel minimum: 0", "0")
    i = cukur[0]
    ekle("D8", "hata",
         "saatlik profilde gündüz çukuru: güneş öğlene doğru inip tekrar çıkmaz "
         "(%02d–%02d dilimi %s kW; komşuları %s / %s kW)"
         % (5 + i, 6 + i, _tr(taban[i], 0), _tr(taban[i - 1], 0), _tr(taban[i + 1], 0)),
         "yerel minimum: 0", "%d çukur (ilki %02d–%02d)" % (len(cukur), 5 + i, 6 + i))


def _d9(veri, ekle):
    etiket = _al(veri, "GUN_ETIKET") or []
    ay_yil = str(_al(veri, "AY_YIL") or "")
    n = int(_al(veri, "GUN_SAYISI") or len(etiket) or 0)
    par = ay_yil.split()
    ay = _ay_no(par[0]) if par else None
    yil = int(par[1]) if len(par) > 1 and par[1].isdigit() else None
    if not etiket or ay is None or yil is None or n == 0:
        return ekle("D9", "uyari", "dönem tarih aralığı kurulamadı — denetlenemedi",
                    "GUN_ETIKET + AY_YIL", "eksik")
    try:
        bas = _dt.date(yil, ay, int(etiket[0]))
    except ValueError:
        return ekle("D9", "uyari", "dönem başlangıcı çözümlenemedi", "AY_YIL + GUN_ETIKET[0]",
                    "%s / %s" % (ay_yil, etiket[0]))
    gecerli = {bas + _dt.timedelta(days=i) for i in range(n)}
    # v2.131 aynası: s05 paneli GUN_ETIKET[k] + AY_YIL ayını, s14 hedefi
    # GUN_ETIKET[0] + AY_YIL ayını basar. Dönem ay sınırını aşarsa etiket
    # "01"e döner ama basılan ay adı ilk ay kalır → tarih geçerli kümeden
    # düşer ve burada yakalanır (kalan gerçek kusur sınıfı budur).
    gosterilen = [("s05 panel", etiket[k]) for k in range(min(S05_PANEL, n, len(etiket)))]
    gosterilen.append(("s14 hedef gün", etiket[0]))
    disari = []
    for yer, gun_s in gosterilen:
        try:
            t = _dt.date(bas.year, ay, int(gun_s))
        except ValueError:
            disari.append((yer, "%s/%02d geçersiz" % (gun_s, ay)))
            continue
        if t not in gecerli:
            disari.append((yer, t.isoformat()))
    if not disari:
        return ekle("D9", "gecti", "gösterilen tüm tarihler tahmin dönemi içinde",
                    "[%s, %s]" % (bas.isoformat(), max(gecerli).isoformat()),
                    "%d tarih uyumlu" % len(gosterilen))
    ekle("D9", "hata",
         "dönem dışına düşen sabit tarih metni: " + "; ".join("%s → %s" % yd for yd in disari),
         "[%s, %s]" % (bas.isoformat(), max(gecerli).isoformat()),
         "%d tarih dışarıda" % len(disari))


def _d10(veri, ekle):
    saha = dict(_al(veri, "SAHA") or [])
    kurulu = saha.get("Kurulu güç", "")
    m = _re.search(r"/\s*([0-9][\d.,]*)\s*MWe", kurulu)
    mwe = _sayi(m.group(1)) if m else None
    if mwe is not None:
        return ekle("D10", "gecti", "MWe alanı mevcut; tüketen gösterge ve cümleler basılabilir",
                    "sayısal MWe", _tr(mwe) + " MWe")
    kf = _al(veri, "KF_PCT")
    tuketici = ["kapak göstergesi {{KURULU}}", "s05 şebeke gücü cümlesi {{SEBEKE}}"]
    if kf is not None:
        tuketici.append("kapasite faktörü (%%%s — tanımı MWe ister, MWp ikamesi yasak)" % _tr(kf))
    ekle("D10", "hata",
         "MWe alanı boşken onu tüketen çıktı üretilemez: " + " · ".join(tuketici) +
         ". Eksik alan cümle ortasında '—' olarak basılamaz; gösterge tümden atlanmalı "
         "ya da alan doldurulmalıdır.",
         "sayısal MWe ('… MWp / X MWe')", repr(kurulu)[:60])


def _d11(veri, ekle):
    """Spec #3: iklim matrisinin son satiri = zarfin orta cizgisi. Ikisi de
    LTA_AY'den basilir (yapisal tek kaynak); burada LTA_AY'nin gercekten
    TAM yillarin ortalamasi oldugu ve kismi yilin ortalamaya girmedigi
    bekcilenir (bayat/elle deger + kural ihlali yakalanir)."""
    iklim = _al(veri, "IKLIM") or {}
    tam = _al(veri, "TAM_YILLAR") or []
    lta = _al(veri, "LTA_AY") or []
    if not iklim or not tam or len(lta) != 12:
        return ekle("D11", "uyari", "iklim yuzeyi eksik — denetlenemedi",
                    "IKLIM + TAM_YILLAR + LTA_AY[12]", "eksik")
    kismi = [y_ for y_ in tam if None in iklim.get(y_, [None])]
    if kismi:
        return ekle("D11", "hata", "kismi yil ortalamaya girmis (kural: yalniz tam yillar)",
                    "TAM_YILLAR'da None'suz yillar", str(kismi))
    kotu = [m for m in range(12)
            if abs(round(sum(iklim[y_][m] for y_ in tam) / len(tam)) - lta[m]) > 0.5]
    if not kotu:
        return ekle("D11", "gecti", "LTA (matris son satiri = zarf orta cizgisi) tam-yil "
                    "ortalamasindan yeniden uretilebilir", "12/12 ay (±0,5)", "12/12 uyumlu")
    ekle("D11", "hata", "LTA_AY yuzeydeki degerle yeniden hesap uyusmuyor (bayat/elle deger)",
         "ay %d: yeniden hesap" % (kotu[0] + 1), str(lta[kotu[0]]))


def _d12(veri, ekle):
    """Spec #7: selalede yazan iyilesme yuzdesi bas/sondan yeniden uretilebilir."""
    bas, bit = _al(veri, "SELALE_BAS"), _al(veri, "SELALE_BIT")
    iy = _al(veri, "IYILESME_PCT")
    if _al(veri, "SELALE_ADIM") is None:
        return ekle("D12", "gecti", "selale basilmiyor (adimsiz) — iyilesme iddiasi yok",
                    "—", "—")
    if bas is None or bit is None or iy is None or not bas:
        return ekle("D12", "uyari", "iyilesme yuzeyi eksik — denetlenemedi",
                    "SELALE_BAS/BIT + IYILESME_PCT", "eksik")
    beklenen = round((bas - bit) / bas * 100, 1)
    if abs(iy - beklenen) <= 0.1:
        return ekle("D12", "gecti", "iyilesme yuzdesi bas/sondan yeniden uretilebilir",
                    _tr(beklenen) + " (±0,1)", _tr(iy))
    ekle("D12", "hata", "iyilesme yuzdesi bas/sondan cikmiyor (bayat/elle deger)",
         _tr(beklenen) + " (±0,1)", _tr(iy))


def _d13(veri, ekle):
    """Spec #13: tepe guc <= kurulu DC guc."""
    taban = _al(veri, "BASE_KW") or []
    saha = dict(_al(veri, "SAHA") or [])
    m = _re.search(r"([\d.,]+)\s*MWp", saha.get("Kurulu güç", ""))
    mwp = _sayi(m.group(1)) if m else None
    if not taban or mwp is None:
        return ekle("D13", "uyari", "tepe/kurulu guc yuzeyi eksik — denetlenemedi",
                    "BASE_KW + 'X MWp'", "eksik")
    tepe, dc = max(taban), mwp * 1000.0
    if tepe <= dc:
        return ekle("D13", "gecti", "saatlik tepe kurulu DC gucu asmiyor",
                    "≤ " + _tr(dc, 0) + " kW", _tr(tepe, 0) + " kW")
    ekle("D13", "hata", "saatlik tepe kurulu DC gucun UZERINDE — fiziksel olarak imkansiz",
         "≤ " + _tr(dc, 0) + " kW", _tr(tepe, 0) + " kW")


def _d14(veri, ekle):
    """Spec #12 (sureklilik yarisi): ardisik saatler arasi sicrama KURULU DC
    gucun %30'unu asamaz. TANIM DUZELTMESI (v2.136, kayitli): ilk surumde
    esik gozlenen tepeye oranliydi; AC-kirpmali santralde tepe bastirilinca
    payda kuculur ve durust sabah rampasi yanlis-pozitif verir (canli vaka:
    3.600 kW AC sinirli santralde 1.113 kW rampasi = kirpilmis tepenin %31'i
    ama DC'nin %24,7'si). Rampayi suren isinim DC diziyle olceklenir; kirpma
    tepeyi degistirir, rampayi degistirmez → dogru payda kurulu DC.
    Kanonik azami adim DC'nin %14,6'si (genis pay)."""
    taban = _al(veri, "BASE_KW") or []
    saha = dict(_al(veri, "SAHA") or [])
    m = _re.search(r"([\d.,]+)\s*MWp", saha.get("Kurulu güç", ""))
    mwp = _sayi(m.group(1)) if m else None
    if len(taban) < 2 or mwp is None:
        return ekle("D14", "uyari", "saatlik taban ya da kurulu DC yok — denetlenemedi",
                    "BASE_KW + 'X MWp'", "eksik")
    sinir = 0.30 * mwp * 1000.0
    adim = [abs(taban[i + 1] - taban[i]) for i in range(len(taban) - 1)]
    kotu = [(i, f) for i, f in enumerate(adim) if f > sinir]
    if not kotu:
        return ekle("D14", "gecti", "profil surekli: ardisik sicrama kurulu DC'nin %30'u altinda",
                    "≤ " + _tr(sinir, 0) + " kW/saat", "azami " + _tr(max(adim), 0) + " kW")
    i, fark = kotu[0]
    ekle("D14", "hata", "profilde fiziksel olmayan sicrama (%02d–%02d → %02d–%02d)"
         % (5 + i, 6 + i, 6 + i, 7 + i),
         "≤ " + _tr(sinir, 0) + " kW/saat (kurulu DC'nin %30'u)", _tr(fark, 0) + " kW")


def _d15(veri, ekle):
    """Spec #21: karne penceresi ile SCADA arsiv donemi cakisir."""
    karne = _al(veri, "KARNE_TARIH") or []
    ay_yil = str(_al(veri, "AY_YIL") or "")
    coz = _arsiv_coz(_al(veri, "ARSIV_ETIKET"))
    par = ay_yil.split()
    yil = int(par[1]) if len(par) > 1 and par[1].isdigit() else None
    if not karne or coz is None or yil is None:
        return ekle("D15", "uyari", "karne/arsiv tarih yuzeyi eksik — denetlenemedi",
                    "KARNE_TARIH + ARSIV_ETIKET + AY_YIL", "eksik")
    def _koz(et):
        p = str(et).split()
        g, a = int(p[0]), _ay_no(p[1])
        return (g, a)
    try:
        (g1, a1), (g2, a2) = _koz(karne[0]), _koz(karne[-1])
        if a1 is None or a2 is None:
            raise ValueError
        y2 = yil
        y1 = yil - 1 if a1 > a2 else yil       # yil-asan karne penceresi
        kb, ks = _dt.date(y1, a1, g1), _dt.date(y2, a2, g2)
    except (ValueError, IndexError):
        return ekle("D15", "uyari", "karne tarihleri cozumlenemedi", "'GG Ay' etiketleri",
                    repr(karne[:2]))
    t1, t2, _s = coz
    if kb <= t2 and ks >= t1:
        return ekle("D15", "gecti", "karne penceresi arsiv donemiyle cakisiyor",
                    "[%s, %s] ∩ arsiv ≠ ∅" % (kb.isoformat(), ks.isoformat()),
                    "arsiv [%s, %s]" % (t1.isoformat(), t2.isoformat()))
    ekle("D15", "hata", "karne penceresi arsiv doneminin TAMAMEN disinda — karne "
         "arsivde olmayan gunleri puanlayamaz",
         "kesisim ≠ ∅", "karne [%s, %s] / arsiv [%s, %s]"
         % (kb.isoformat(), ks.isoformat(), t1.isoformat(), t2.isoformat()))


def _d16(veri, ekle):
    """Spec #18: esikli KPI'larda deger↔esik yonu ile basilan durum tutarli;
    ayrica KESINTISIZ karti tukettigi alan yokken basilamaz (kural 4)."""
    esik = _al(veri, "KPI_ESIK") or {}
    uclu = [("WMAPE120", _al(veri, "WMAPE120_PCT"), _al(veri, "DURUM_WMAPE120")),
            ("HOLDOUT", _al(veri, "SELALE_BIT"), _al(veri, "DURUM_HOLDOUT")),
            ("KAPSAMA", _al(veri, "KAPSAMA_PCT"), _al(veri, "DURUM_KAPSAMA"))]
    for ad, deger, durum in uclu:
        if ad not in esik or deger is None or durum is None:
            ekle("D16", "uyari", "%s: esik/deger/durum yuzeyi eksik — denetlenemedi" % ad,
                 "KPI_ESIK + deger + DURUM_*", "eksik")
            continue
        e, yon = esik[ad]
        bekle = "ok" if ((deger < e) if yon == "alt" else (deger > e)) else "watch"
        if durum == bekle:
            ekle("D16", "gecti", "%s durumu esik yonuyle tutarli" % ad,
                 "%s (deger %s, esik %s/%s)" % (bekle, _tr(deger), _tr(e), yon), durum)
        else:
            ekle("D16", "hata", "%s durum rengi esik yonuyle CELISIYOR" % ad,
                 bekle, "%s (deger %s, esik %s)" % (durum, _tr(deger), _tr(e)))
    kes = _al(veri, "KESINTISIZ_GUN")
    if kes is None:
        ekle("D16", "hata", "'Kesintisiz dogrulama' karti tukettigi alan yokken basilamaz "
             "(uninterrupted_days doldurulmali ya da kart dusurulmeli)",
             "sayisal gun", "yok")
    else:
        ekle("D16", "gecti", "kesintisiz dogrulama karti sayisal alandan besleniyor",
             "sayisal gun", _tr(kes, 0) + " gün")


def _d17(veri, ekle):
    """Spec #5 (v2.139): yillik Pxx, aciklanan sigma ve z ile yeniden
    uretilebilir. Yuzeydeki YIL_ORT/SD/CV/PXX_YIL, IKLIM'den bagimsizca
    yeniden hesaplanip karsilastirilir — bayat/elle deger ve formul kaymasi
    (orn. n-1 orneklem boleninin populasyona donmesi) yakalanir."""
    iklim = _al(veri, "IKLIM") or {}
    tam = _al(veri, "TAM_YILLAR") or []
    ort, sd = _al(veri, "YIL_ORT"), _al(veri, "YIL_SD")
    cv, pxx = _al(veri, "YIL_CV_PCT"), _al(veri, "PXX_YIL") or {}
    z = _al(veri, "Z_YIL") or {}
    if len(tam) < 2 or ort is None or sd is None or cv is None or not pxx:
        return ekle("D17", "uyari", "yillik istatistik yuzeyi eksik — denetlenemedi",
                    "IKLIM + YIL_ORT/SD/CV + PXX_YIL", "eksik")
    if abs(z.get(75, 0) - 0.6745) > 1e-9 or abs(z.get(90, 0) - 1.2816) > 1e-9:
        return ekle("D17", "hata", "z tablosu sozlesmeden sapmis",
                    "P75→0,6745 · P90→1,2816", str(z))
    import math as _m
    yil = [sum(iklim[y_]) for y_ in tam]
    b_ort = sum(yil) / len(yil)
    b_sd = _m.sqrt(sum((v - b_ort) ** 2 for v in yil) / (len(yil) - 1))
    b_cv = b_sd / b_ort * 100
    kotu = []
    if abs(b_ort - ort) > 0.01: kotu.append("ORT: %s≠%s" % (_tr(ort, 0), _tr(b_ort, 0)))
    if abs(b_sd - sd) > 0.01: kotu.append("SD: %s≠%s" % (_tr(sd, 1), _tr(b_sd, 1)))
    if abs(b_cv - cv) > 0.01: kotu.append("CV: %s≠%s" % (_tr(cv, 2), _tr(b_cv, 2)))
    for p, zk in ((75, 0.6745), (90, 1.2816)):
        b = b_ort - zk * b_sd
        if p in pxx and abs(pxx[p] - b) > 0.01:
            kotu.append("P%d: %s≠%s" % (p, _tr(pxx[p], 0), _tr(b, 0)))
    if not kotu:
        return ekle("D17", "gecti", "yillik Pxx sigma ve z'den yeniden uretilebilir "
                    "(SD orneklem, n-1)", "ORT/SD/CV/P75/P90 (±0,01)",
                    "P90=" + _tr(pxx.get(90), 0) + " MWh")
    ekle("D17", "hata", "yillik istatistik yeniden hesapla uyusmuyor (bayat/elle deger "
         "ya da formul kaymasi)", "yeniden hesap (±0,01)", "; ".join(kotu))


def _d18(veri, ekle):
    """v2.140 (karar a): karne butunlugu — 30 takvim satiri; olculdu=false
    ise TUM degerler null (olculmemis gune sayi basilamaz, kural 3);
    olculdu=true ise tum degerler dolu; en az bir olculu gun; ve KESINTISIZ
    kartiyla capraz tutarlilik: karne kuyrugundaki ardisik-olculu gun sayisi
    t < 30 ise KESINTISIZ tam t olmalidir (ilk kesinti karnede gorunur),
    t = 30 ise KESINTISIZ >= 30."""
    wm, sk = _al(veri, "KARNE_WM") or [], _al(veri, "KARNE_SK") or []
    naif = _al(veri, "KARNE_NAIF") or []
    olc = _al(veri, "KARNE_OLCULDU")
    if olc is None or not wm:
        return ekle("D18", "uyari", "olculdu yuzeyi yok — denetlenemedi",
                    "KARNE_OLCULDU", "eksik")
    if not (len(wm) == len(sk) == len(naif) == len(olc) == 30):
        return ekle("D18", "hata", "karne 30 takvim satiri degil",
                    "30/30/30/30", "%d/%d/%d/%d" % (len(wm), len(sk), len(naif), len(olc)))
    for i, o in enumerate(olc):
        uclu = (wm[i], sk[i], naif[i])
        if not o and any(x is not None for x in uclu):
            return ekle("D18", "hata", "ölçülmemiş güne sayı basılmış (%d. satır) "
                        "— eksik '—' ile gösterilir, kısmi sayıyla değil", "hepsi null",
                        str(uclu))
        if o and any(x is None for x in uclu):
            return ekle("D18", "hata", "ölçülü günde değer boş (%d. satır)" % (i + 1),
                        "wm+sk+naif dolu", str(uclu))
    if not any(olc):
        return ekle("D18", "hata", "karnede tek ölçülü gün yok", "≥1", "0")
    h72 = _al(veri, "KARNE_H72") or []
    if len(h72) == 30:
        for j, kv in enumerate(h72):          # v2.143: tam 30 satır — ölçülmemişin 24-72'si olamaz
            if not olc[j] and kv is not None:
                return ekle("D18", "hata", "ölçülmemiş güne 24-72 hatası basılmış "
                            "(%d. satır) — gerçekleşeni olmayan günün hatası "
                            "var olamaz" % (j + 1), "null", str(kv))
    t = 0
    for o in reversed(olc):
        if o: t += 1
        else: break
    kes = _al(veri, "KESINTISIZ_GUN")
    if kes is None:
        return ekle("D18", "uyari", "KESINTISIZ yok — çapraz denetlenemedi (D16 zaten hata verir)",
                    "sayısal gün", "yok")
    if (t < 30 and int(kes) != t) or (t == 30 and int(kes) < 30):
        return ekle("D18", "hata", "kesintisiz-doğrulama karti karne kuyruğuyla çelişiyor",
                    ("= %d (ilk kesinti karnede)" % t) if t < 30 else "≥ 30",
                    _tr(kes, 0) + " gün")
    ekle("D18", "gecti", "karne bütünlüğü: %d/30 ölçülü, kuyruk %d gün, "
         "KESINTISIZ tutarlı" % (sum(olc), t), "yapı + çapraz", _tr(kes, 0) + " gün")


# ------------------------------------------------- render denetimi (v2.135)
def render_denetle(cikti_dizin):
    """Sayfalar uretildikten SONRA, birlesim/yayimdan ONCE kosar:
    (a) hicbir sayfada doldurulmamis '{{' kalmadi;
    (b) s02 icindekiler + s15 'Nerede' sayfa referanslari 1..16 icinde.
    -> list[Bulgu] (bos = temiz)."""
    import glob as _glob, os as _os
    bulgular = []
    sayfalar = sorted(_glob.glob(_os.path.join(cikti_dizin, "*_s??_*.html")))
    if len(sayfalar) != 16:
        bulgular.append(Bulgu("R1", "hata", "16 sayfa bulunamadi",
                              "16 html", str(len(sayfalar))))
        return bulgular
    for yol in sayfalar:
        icerik = open(yol, encoding="utf-8").read()
        if "{{" in icerik:
            i = icerik.index("{{")
            bulgular.append(Bulgu("R1", "hata",
                                  "doldurulmamis token: %s" % _os.path.basename(yol),
                                  "'{{' yok", icerik[i:i + 40]))
    for etiket, desen in (("s02", "*_s02_*"), ("s15", "*_s15_*")):
        es = _glob.glob(_os.path.join(cikti_dizin, desen + ".html"))
        if not es:
            continue
        icerik = open(es[0], encoding="utf-8").read()
        disari = [n for n in (int(x) for x in _re.findall(r"[Ss]ayfa\s+(\d+)", icerik))
                  if not (1 <= n <= 16)]
        if disari:
            bulgular.append(Bulgu("R2", "hata",
                                  "%s var olmayan sayfaya isaret ediyor" % etiket,
                                  "1..16", str(sorted(set(disari)))))
    return bulgular


# ---------------------------------------------------------------- API
def denetle_tam(veri):
    """Tüm kontrolleri koşar. → (kayitlar, bulgular, suphe_bayragi)
    kayitlar: geçen+geçmeyen tüm sonuçlar (denetim.json için);
    bulgular: yalnız hata/uyari (denetle() sözleşmesi)."""
    kayitlar = []

    def ekle(kod, durum, mesaj, beklenen, bulunan):
        kayitlar.append({"kod": kod, "durum": durum, "mesaj": mesaj,
                         "beklenen": str(beklenen), "bulunan": str(bulunan)})

    _d1(veri, ekle); _d2(veri, ekle); _d3(veri, ekle); _d4(veri, ekle)
    _d5(veri, ekle); _d6(veri, ekle)
    bayrak = bool(_d7(veri, ekle))
    _d8(veri, ekle); _d9(veri, ekle); _d10(veri, ekle)
    _d11(veri, ekle); _d12(veri, ekle); _d13(veri, ekle)
    _d14(veri, ekle); _d15(veri, ekle); _d16(veri, ekle)
    _d17(veri, ekle); _d18(veri, ekle)

    bulgular = [Bulgu(k["kod"], k["durum"], k["mesaj"], k["beklenen"], k["bulunan"])
                for k in kayitlar if k["durum"] in ("hata", "uyari")]
    return kayitlar, bulgular, bayrak


def denetle(veri):
    """Sözleşme: veri yüzeyi (modül ya da sözlük) → list[Bulgu].
    Boş liste = tüm kontroller geçti."""
    _kayitlar, bulgular, _bayrak = denetle_tam(veri)
    return bulgular


def json_yaz(kayitlar, bayrak, yol):
    """denetim.json: geçen/geçmeyen ayrımı + her kontrolün kodu,
    beklenen ve bulunan değerleri."""
    gecenler = [k for k in kayitlar if k["durum"] == "gecti"]
    kalanlar = [{"kod": k["kod"], "seviye": k["durum"], "mesaj": k["mesaj"],
                 "beklenen": k["beklenen"], "bulunan": k["bulunan"]}
                for k in kayitlar if k["durum"] != "gecti"]
    govde = {
        "zaman": _dt.datetime.now().isoformat(timespec="seconds"),
        "suphe_bayragi": bayrak,
        "ozet": {"gecti": len(gecenler),
                 "hata": sum(1 for k in kalanlar if k["seviye"] == "hata"),
                 "uyari": sum(1 for k in kalanlar if k["seviye"] == "uyari")},
        "gecenler": [{"kod": k["kod"], "mesaj": k["mesaj"],
                      "beklenen": k["beklenen"], "bulunan": k["bulunan"]}
                     for k in gecenler],
        "bulgular": kalanlar,
    }
    with open(yol, "w", encoding="utf-8") as f:
        _json.dump(govde, f, ensure_ascii=False, indent=2)
    return govde
