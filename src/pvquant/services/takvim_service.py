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


UYUM_NOT = ("«İşlem gerekli» santralin yapacağı adımdır; «takip edilmeli» başkasının (EPİAŞ, EPDK, TEİAŞ, şebeke işletmecisi) adımıdır; «doğrulama gerekli» koşulu "
            "PVQuant'ta kayıtlı olmayan (bağlantı türü, DSG türü, mekanik güç, YEKDEM süresi) satırdır. "
            "Uyum takvimi 12 ay ileriye bakar: lisans ve bildirim yükümlülükleri (ilerleme raporu, lisans bedeli taksitleri, BDB-02, TEİAŞ bakım planı), "
            "santral tarihlerinden türeyenler (İSG periyodik kontrol, ortaklık değişikliği, izin iptali, lisanssız 10 yıl) ve olay kaydındaki planlı bakımların "
            "bildirim son anı. «Aykırılıkta» sütunu ilgili maddeyi ve ihtar süresini söyler; bent eşlemesi Kurul takdirine bağlı olduğundan «çıkarım» etiketlidir, "
            "tutar yazılmaz (yıllık tebliğle değişir). Toplayıcı lisansının kendi takvimi (Mart/Temmuz/Kasım taksitleri, fiyat bildirimi), piyasadan alım sınırı "
            "(Karar 14626) ve YEK-G kaydı burada yok.")


def _bakim_satirlari(tenant_id, plant: dict, b: date) -> list[dict]:
    """v2.524 (P3b): olay kaydındaki planlı bakımlar (planlı evre) → TEİAŞ bildirim son anı (ESY m.54 kuralı); iletime bağlı tesis için."""
    if not tenant_id:
        return []
    try:
        from pvquant.services import olay_service
        olaylar = [o for o in olay_service.listele(tenant_id, plant["id"], 400) if o["tur"] == "planli_bakim" and o["evre"] == "planli"]
    except Exception:   # noqa: BLE001 — olay tablosu yoksa takvim düşmez
        return []
    out = []
    for o in olaylar[:20]:
        bas = datetime.fromisoformat(o["baslangic"]); bit = datetime.fromisoformat(o["bitis"]) if o.get("bitis") else None
        bb = tk.bakim_bildirim(bas, bit)
        son = datetime.fromisoformat(bb["son_an"]).astimezone(IST) if bb["son_an"] else None
        out.append({"olay_id": o["id"], "baslangic": o["baslangic"], "bitis": o.get("bitis"), "etkilenen_kw": o.get("etkilenen_kw"), "sure_saat": bb["sure_saat"],
                    "kural": bb["kural"], "son_an": son.isoformat() if son else None, "gecti": bool(son and son.date() < b), "kaynak": bb["kaynak"]})
    return out


def ozet(plant: dict, gun: int = 90, bugun: date | None = None, tenant_id=None) -> dict:
    pj = dengesizlik_service._pj(plant.get("params_json"))
    seg = dengesizlik_service.segment_bilgisi(pj)
    b = bugun or bugun_ist()
    kap = plant.get("capacity_kwp")
    uyum = [o for o in tk.yaklasan(b, pj, seg["segment"], 365, kap) if o["kod"] in tk.UYUM_KODLAR]   # v2.524 (P3b): 12 ay, dönem adımları hariç
    return {"bugun": b.isoformat(), "pencere_gun": gun, "segment": seg["segment"], "kgup_yukumlu": seg["kgup_yukumlu"],
            "yaklasan": tk.yaklasan(b, pj, seg["segment"], gun, kap),
            "yaklasan_piyasa": [o for o in tk.yaklasan(b, pj, seg["segment"], gun, kap) if o["kod"] not in tk.UYUM_KODLAR],   # sayfa: uyum tarihleri yalnız Uyum kartında (tekrar yok)
            "islem_etiketleri": tk.ISLEM_ETIKET, "uyum": uyum, "bakim": _bakim_satirlari(tenant_id, plant, b), "uyum_not": UYUM_NOT, "bakim_kaynak": tk.BAKIM_BILDIRIM_KAYNAK,
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
