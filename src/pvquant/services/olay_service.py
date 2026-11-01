"""v2.521 (P1a) — olay kaydı: planlı bakım, arıza, talimat (YAL/YAT), acil durum kesmesi, şebeke kesintisi, hasar.

Tek tablo (olay; RLS kiracı), olay türüne bağlı kurallar (TUR_KURAL): EAK'yi düşürür mü (TPYS EAK.csv'de hangi gerekçe sütununa yazılır),
kullanılabilirlik hesabında istisna mı (planlı bakım, şebeke kesintisi, talimat, acil kesme: santralın elinde değil), aylık arıza sayacına
girer mi (Karar 14029/14907: UEVÇB'de ayda 30 ve üzeri arıza kaydı KÜPST n katsayısını 0,05 → 0,08 yapar; alarm eşiği 25).
Dayanak (GES sahibi araştırması): 01-18 (EAK gerekçe sütunları: kaynak yetersizliği, iklim/verim, mücbir, dışsal, güvenlik; arıza ve bakım
TPYS «Arıza ve Bakım bildirimleri» sayfasından ayrıca girilir — PVQuant bunu yapmaz, dosya adı ve kaydı tutar), 01-19 (Karar 14967: tesis bazında
≥30 MW, portföy bazında ≥50 MW güç değişimi olayın ortaya çıkışından en geç 1 saat içinde Dâhilî Bilgi Platformu'nda; yürürlük tarihi metinde
yok → «belirsiz»), 03-10 (ESY m.52–54: kısa planlı devre dışı 24 saat / 7 gün önceden; yıllık plan 30 Nisan), DUY m.69/A (EAK'yi arıza/bakım
kaydıyla düşürmeyi itiyat etmek Kanun m.16'ya gider — kayıt gerekçeli ve değiştirilemez tutulur).
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

IST = ZoneInfo("Europe/Istanbul")
TURLER = ("planli_bakim", "ariza", "talimat_yat", "talimat_yal", "acil_kesme", "sebeke_kesintisi", "hasar")
TUR_ETIKET = {"planli_bakim": "Planlı bakım", "ariza": "Arıza", "talimat_yat": "Yük atma talimatı (YAT)", "talimat_yal": "Yük alma talimatı (YAL)",
              "acil_kesme": "Acil durum kesmesi", "sebeke_kesintisi": "Şebeke kesintisi", "hasar": "Hasar"}
GEREKCELER = ("kaynak_yetersizligi", "iklim_verim", "mucbir", "dissal", "guvenlik")
GEREKCE_ETIKET = {"kaynak_yetersizligi": "kaynak yetersizliği", "iklim_verim": "iklim / verim", "mucbir": "mücbir sebep", "dissal": "dışsal", "guvenlik": "güvenlik"}
# tür → EAK'yi düşürür mü, EAK.csv varsayılan gerekçe sütunu, kullanılabilirlik istisnası mı, arıza sayacına girer mi, açıklama
TUR_KURAL = {
    "planli_bakim":    {"eak_dusur": True,  "gerekce": "kaynak_yetersizligi", "istisna": True,  "sayac": False, "not": "EAK düşer; TPYS Arıza ve Bakım bildirimi ayrıca; kullanılabilirlik hesabında istisna"},
    "ariza":           {"eak_dusur": True,  "gerekce": "kaynak_yetersizligi", "istisna": False, "sayac": True,  "not": "EAK düşer; aylık arıza sayacına girer (30 ve üzeri KÜPST n 0,08); kullanılabilirlikte arıza"},
    "talimat_yat":     {"eak_dusur": False, "gerekce": None,                  "istisna": True,  "sayac": False, "not": "EAK değişmez; program sapması talimattan (BUDÜP, P2b); kullanılabilirlikte istisna"},
    "talimat_yal":     {"eak_dusur": False, "gerekce": None,                  "istisna": True,  "sayac": False, "not": "EAK değişmez; program sapması talimattan (BUDÜP, P2b)"},
    "acil_kesme":      {"eak_dusur": True,  "gerekce": "dissal",              "istisna": True,  "sayac": False, "not": "Sistem İşletmecisi kesmesi: EAK dışsal gerekçeyle düşer; kullanılabilirlikte istisna"},
    "sebeke_kesintisi": {"eak_dusur": True, "gerekce": "dissal",              "istisna": True,  "sayac": False, "not": "Şebeke kaynaklı: EAK dışsal gerekçeyle düşer; kullanılabilirlikte istisna"},
    "hasar":           {"eak_dusur": True,  "gerekce": "kaynak_yetersizligi", "istisna": False, "sayac": False, "not": "Hasar dosyası için kayıt; EAK düşer. Hasar tek başına mücbir sebep değildir: «mücbir sebep» gerekçesi yalnız mevzuattaki koşullar sağlanıyorsa seçilir"},
}
DURUMLAR = ("acik", "kapali", "iptal")
DAHILI_TESIS_KW = 30_000.0      # Karar 14967 Asgari Veriler Listesi sıra 1: tesis bazında 30 MW ve üzeri
DAHILI_PORTFOY_KW = 50_000.0    # portföy bazında 50 MW ve üzeri
DAHILI_SURE_SAAT = 1
DAHILI_NOTU = ("Karar 14967 (RG 20.10.2026-33406) m.4(a): arıza ve bakım dâhil kapasite kullanımı değişiklikleri, olayın ortaya çıkışından en geç 1 saat "
               "içinde Dâhilî Bilgi Platformu'nda açıklanır; eşik tesis bazında 30 MW, portföy bazında 50 MW. Yürürlük tarihi karar metninde yok "
               "(belirsiz); platform arayüzü doğrulanmadı. Bu geri sayım hatırlatmadır, bildirim yerine geçmez.")


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
    return {"tur": tur, "baslangic": bas, "bitis": bit, "etkilenen_kw": kw, "neden": (str(g.get("neden") or "").strip() or None),
            "eak_gerekcesi": ger, "kanit": (str(g.get("kanit") or "").strip() or None)}


def _sinir_kw(plant: dict) -> float | None:
    """Devre dışı güç üst sınırı: AC sınırı (invertör çıkışı) varsa o, yoksa kurulu güç (kWp). Günün EAK tabanı da bu sınırdan büyük olamaz."""
    v = float(plant.get("ac_limit_kw") or 0) or float(plant.get("capacity_kwp") or 0)
    return v or None


def _satir(r) -> dict:
    d = dict(r._mapping) if hasattr(r, "_mapping") else dict(r)
    for k in ("baslangic", "bitis", "olusturma", "guncelleme"):
        v = d.get(k)
        d[k] = v.astimezone(IST).isoformat(timespec="minutes") if isinstance(v, datetime) else None
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
        r = s.execute(text("INSERT INTO olay(tenant_id, plant_id, tur, baslangic, bitis, etkilenen_kw, neden, eak_gerekcesi, kanit, durum, olusturan) "
                           "VALUES (:t, :p, :tur, :b, :e, :kw, :n, :g, :k, :d, :o) RETURNING *"),
                      {"t": tenant_id, "p": plant["id"], "tur": v["tur"], "b": v["baslangic"], "e": v["bitis"], "kw": v["etkilenen_kw"], "n": v["neden"],
                       "g": v["eak_gerekcesi"], "k": v["kanit"], "d": durum, "o": olusturan}).first()
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
                    "neden": g.get("neden", m["neden"]), "eak_gerekcesi": g.get("eak_gerekcesi", m["eak_gerekcesi"]), "kanit": g.get("kanit", m["kanit"])}
        v = dogrula(birlesik, _sinir_kw(plant))
        durum = g.get("durum") or m["durum"]
        if durum not in DURUMLAR:
            raise ValueError("durum acik / kapali / iptal olmalı")
        if durum != "iptal":
            durum = "acik" if v["bitis"] is None or v["bitis"] > datetime.now(timezone.utc) else "kapali"
        r2 = s.execute(text("UPDATE olay SET bitis=:e, etkilenen_kw=:kw, neden=:n, eak_gerekcesi=:g, kanit=:k, durum=:d, guncelleme=now() "
                            "WHERE id=:i AND plant_id=:p RETURNING *"),
                       {"e": v["bitis"], "kw": v["etkilenen_kw"], "n": v["neden"], "g": v["eak_gerekcesi"], "k": v["kanit"], "d": durum, "i": olay_id, "p": plant["id"]}).first()
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


def dahili_bilgi(olay: dict, kapasite_kw: float, portfoy_kw: float | None = None, simdi: datetime | None = None) -> dict | None:
    """Karar 14967 1 saat kuralı: etkilenen güç (boşsa kurulu güç) tesis eşiğinde ya da portföy açık olay toplamı portföy eşiğinde ise
    son açıklama saati ve kalan süre; eşik altındaysa None. Yürürlük «belirsiz»."""
    if olay.get("tur") not in ("planli_bakim", "ariza", "acil_kesme", "sebeke_kesintisi", "hasar"):
        return None
    kw = float(olay["etkilenen_kw"]) if olay.get("etkilenen_kw") else float(kapasite_kw or 0)
    tesis = kw >= DAHILI_TESIS_KW; portfoy = portfoy_kw is not None and portfoy_kw >= DAHILI_PORTFOY_KW
    if not (tesis or portfoy):
        return None
    bas = olay["baslangic"] if isinstance(olay["baslangic"], datetime) else datetime.fromisoformat(olay["baslangic"])
    son = bas + timedelta(hours=DAHILI_SURE_SAAT); now = simdi or datetime.now(timezone.utc)
    return {"esik": "tesis 30 MW" if tesis else "portföy 50 MW", "etkilenen_kw": kw, "son_saat": son.astimezone(IST).isoformat(timespec="minutes"),
            "kalan_dk": int((son - now).total_seconds() // 60), "gecti": now > son, "yururluk": "belirsiz", "not": DAHILI_NOTU}


def ozet(tenant_id, plant: dict, gun: int = 90, bugun: date | None = None) -> dict:
    """Müşteri ucu: olay listesi, açık olaylar, bu ayın arıza sayacı (eşik 30, uyarı 25), bugünkü EAK etkisi, dâhilî bilgi hatırlatmaları."""
    b = bugun or datetime.now(IST).date()
    olaylar = listele(tenant_id, plant["id"], gun)
    acik = [o for o in olaylar if o["evre"] == "suruyor"]
    planli = [o for o in olaylar if o["evre"] == "planli"]
    kap = _sinir_kw(plant) or 0.0   # tesisin tamamı = AC sınırı (varsa); kWp değil
    portfoy_kw = sum((float(o["etkilenen_kw"]) if o["etkilenen_kw"] else kap) for o in acik)
    dahili = []
    for o in acik:
        d = dahili_bilgi(o, kap, portfoy_kw if len(acik) > 1 else None)
        if d:
            dahili.append({"olay_id": o["id"], "tur": o["tur_etiket"], **d})
    sayac = ariza_sayisi_etkin(tenant_id, plant, b)
    etki = saatlik_etki(tenant_id, plant, b)
    return {"bugun": b.isoformat(), "pencere_gun": gun, "olaylar": olaylar, "acik": len(acik), "planli": len(planli), "ariza_sayaci": {**sayac, "esik": 30, "uyari": 25, "ay": b.strftime("%Y-%m")},
            "eak_bugun": {"saat_sayisi": len(etki["saatler"]), "en_cok_kw": max((v["toplam_kw"] for v in etki["saatler"].values()), default=0.0),
                          "taban_kw": etki["taban_kw"], "kismi_saat": sum(1 for v in etki["saatler"].values() if v["oran"] < 1.0),
                          "suren": sum(1 for o in acik if o["kural"]["eak_dusur"] and not o["bitis"])},   # bitişi girilmemiş: gün sonuna kadar sayılır
            "dahili_bilgi": dahili, "turler": [{"kod": t, "etiket": TUR_ETIKET[t], **TUR_KURAL[t]} for t in TURLER],
            "gerekceler": [{"kod": g, "etiket": GEREKCE_ETIKET[g]} for g in GEREKCELER],
            "not": "Olay kaydı santralın kendi kaydıdır; TPYS Arıza ve Bakım bildirimi, Dâhilî Bilgi Platformu açıklaması ve TEİAŞ bildirimleri ayrıca yapılır.",
            "aciklama": {"kapasite": "Planlı bakım, arıza, acil kesme, şebeke kesintisi ve hasar o saatlerde verilebilecek gücü (EAK) ve programın tavanını düşürür; saat içinde kısmen süren olay "
                                     "süreyle orantılı düşer; bitişi girilmemiş olay gün sonuna kadar sayılır. Birden çok olay toplanır (ayrı ekipmanlar için doğrudur; aynı ekipmanı "
                                     "anlatan iki kayıt iki kez düşer, kayıt ekipman ayrımı tutmaz), toplam günün EAK tabanını (AC sınırı ya da EAK alanı) aşmaz. Talimatlar (YAL/YAT) kapasiteyi değiştirmez.",
                         "sayac": "Yalnız «arıza» türü aylık sayaca girer. Ayda 30 ve üzeri arıza kaydı KGÜP sapma tutarı katsayısını 0,05'ten 0,08'e çıkarır (Karar 14907); 25'te uyarı alarmı.",
                         "kullanilabilirlik": "Planlı bakım, talimat, acil kesme ve şebeke kesintisi saatleri kullanılabilirlik hesabından düşülür (santralın elinde değil); arıza ve hasar arıza sayılır.",
                         "islem": "«Bitir» olayın bittiğini işler, kayıt hesaplarda kalır. «Geçersiz say» yanlış kaydı hesaplardan çıkarır; kayıt silinmez, dosyada «geçersiz» olarak görünür. "
                                  "Başlangıç ve tür değiştirilemez; yanlışsa kaydı geçersiz sayıp yenisini açın. Her ekleme ve değişiklik denetim izinde tutulur.",
                         "gerekce": "EAK gerekçesi TPYS EAK dosyasındaki sütundur; tür için varsayılan önerilir, kayıt girilirken değiştirilebilir. «Mücbir sebep» yalnız mevzuattaki koşullar "
                                    "sağlanıyorsa seçilir; hasar tek başına mücbir sebep değildir."}}


def csv_metni(olaylar: list[dict], plant_ad: str) -> str:
    """Hasar / sigorta dosyası: olay listesi (UTF-8 BOM, ; ayraç, Türkçe saat)."""
    kol = ["santral", "tur", "baslangic", "bitis", "sure_saat", "etkilenen_kw", "neden", "eak_gerekcesi", "kanit", "evre", "olusturma"]
    satirlar = []
    for o in olaylar:
        b = datetime.fromisoformat(o["baslangic"]); e = datetime.fromisoformat(o["bitis"]) if o["bitis"] else None
        satirlar.append({"santral": plant_ad, "tur": o["tur_etiket"], "baslangic": o["baslangic"], "bitis": o["bitis"] or "",
                         "sure_saat": round((e - b).total_seconds() / 3600, 2) if e else "", "etkilenen_kw": o["etkilenen_kw"] if o["etkilenen_kw"] is not None else "",
                         "neden": o["neden"] or "", "eak_gerekcesi": GEREKCE_ETIKET.get(o["eak_gerekcesi"] or "", ""), "kanit": o["kanit"] or "",
                         "evre": {"planli": "planlı", "suruyor": "sürüyor", "bitti": "bitti", "iptal": "geçersiz"}[o.get("evre") or evre(o)], "olusturma": o["olusturma"]})
    buf = io.StringIO()
    pd.DataFrame(satirlar, columns=kol).to_csv(buf, sep=";", decimal=",", index=False, lineterminator="\n")
    return "﻿" + buf.getvalue()
