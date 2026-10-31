"""v2.518 (P3a) — Takvim servisi: santralın segmenti ve künye tarihleriyle ext/turkiye/takvim'i birleştirir.
Saf hesap takvim.py'de; burada yalnız «bugün» (İstanbul), segment ve params_json okunur."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from pvquant.ext.turkiye import takvim as tk
from pvquant.services import dengesizlik_service

IST = ZoneInfo("Europe/Istanbul")

NOT = ("Tarihler mevzuattan (DUY m.132, m.133; YEK Yönetmeliği; LÜY) ve iş günü hesabından türetilmiştir; EPİAŞ ve EPDK duyurusuyla "
       "değişebilir. «mevzuat» etiketi metinde yazılı günü, «hesaplanan» iş günü kaydırmasını ya da gün ekleme hesabını, «santral tarihi» "
       "Santral tarihleri formuna girdiğiniz tarihi gösterir; «hafta sonu» ve «tatil» uyarısı, metinde kaydırma kuralı bulunmayan bir son "
       "tarihin tatile denk geldiğini belirtir. Avans, teminat ve fatura tutarları burada hesaplanmaz; EPYS ve Takasbank bildirimleri esastır.")


def bugun_ist() -> date:
    return datetime.now(IST).date()


def ozet(plant: dict, gun: int = 90, bugun: date | None = None) -> dict:
    pj = dengesizlik_service._pj(plant.get("params_json"))
    seg = dengesizlik_service.segment_bilgisi(pj)
    b = bugun or bugun_ist()
    return {"bugun": b.isoformat(), "pencere_gun": gun, "segment": seg["segment"], "kgup_yukumlu": seg["kgup_yukumlu"],
            "yaklasan": tk.yaklasan(b, pj, seg["segment"], gun),
            "donemler": tk.donemler(b, once=1, sonra=1),
            "gunluk": [g for g in tk.gunluk_saatler() if not seg["segment"] or seg["segment"] in g["kapsam"]],
            "kunye": tk.kunye_turet(pj, b),
            "tatil_kaynak": tk.TATIL_KAYNAK, "tatil_yillari": sorted(tk.DINI_BAYRAM), "not": NOT}


def kunye_dogrula(alanlar: dict) -> dict:
    """YYYY-MM-DD ya da None; yekdem_baslangic_yili 2005–2100 ya da None. Hatalı alan ValueError(alan adı)."""
    out = {}
    for k in tk.KUNYE_TARIH_ALANLARI:
        if k not in alanlar:
            continue
        v = alanlar[k]
        if v in (None, ""):
            out[k] = None; continue
        try:
            out[k] = date.fromisoformat(str(v)[:10]).isoformat()
        except ValueError:
            raise ValueError(k)
    if "yekdem_baslangic_yili" in alanlar:
        v = alanlar["yekdem_baslangic_yili"]
        if v in (None, ""):
            out["yekdem_baslangic_yili"] = None
        else:
            try:
                y = int(v)
            except (TypeError, ValueError):
                raise ValueError("yekdem_baslangic_yili")
            if not (2005 <= y <= 2100):
                raise ValueError("yekdem_baslangic_yili")
            out["yekdem_baslangic_yili"] = y
    lb, ly = out.get("lisans_bitis"), out.get("lisans_yururluk")
    if lb and ly and lb < ly:
        raise ValueError("lisans_bitis")
    return out
