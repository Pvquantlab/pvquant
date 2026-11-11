"""v2.592 (Faz 3 F3-E) — PORTFÖY REVİZYON KARAR DESTEĞİ (saf; DB yok). Otomatik KGÜP/piyasa emri YOK; yalnız dayanaklı Türkçe öneriler.

Girdi (servis derler): hedef gün (yarın / bugün kalan saatler), portföy risk özeti (F3-C `gelecek_risk`: beklenen sapma, bant, riskli saatler, etiket),
santral başına güncel tahmin ↔ program değişimi, program kaynağı (bildirilen / öneri / yok), belirsizlik durumu (F3-B), tazelik, KGÜP teslim penceresi
(`ext/turkiye/kgup.teslim_durumu`) ve gün içi revizyon penceresi, fiyat kaynağı, tahmini maruziyet oranı (son 30 günün sapma MWh başına net uzlaştırma tutarı).
Her öneri etiketli: doğrulanmış risk (ölçüm + bildirilen program + bant doğrulanmış) / tahmini risk / eksik bilgi / revizyon fırsatı geçti.
Kurallar (12): program_yok, sapma_buyuk, sapma_orta, santral_degisim, ofset, riskli_saat, fiyat_yok, maruziyet, belirsizlik, tazelik, pencere, tahmin_yok; hiçbiri
tetiklenmezse «sakin». Metinler brief örnekleriyle aynı dilde; iç terim yok."""
from __future__ import annotations

import pandas as pd

from pvquant.ext.platform import finans as fn

SURUM = "2026-11-11"
SAPMA_BUYUK_PCT = 10.0
SAPMA_ORTA_PCT = 5.0
SANTRAL_DEGISIM_PCT = 15.0
TAZELIK_UYARI_SAAT = 12.0
OLCUM_UYARI_SAAT = 6.0
MARUZIYET_ASGARI_GUN = 7
TUR_AD = {"bilgi": "bilgi", "oneri": "öneri", "eylem": "eylem"}
ETIKET_AD = {"dogrulanmis": "Doğrulanmış risk", "tahmini": "Tahmini risk", "eksik": "Eksik bilgi", "gecti": "Revizyon fırsatı geçti", "bilgi": "Bilgi"}
SAYI_SOZ = {1: "Bir", 2: "İki", 3: "Üç", 4: "Dört", 5: "Beş", 6: "Altı", 7: "Yedi", 8: "Sekiz", 9: "Dokuz", 10: "On"}


def _tr(x, n: int = 1) -> str:
    return f"{float(x):.{n}f}".replace(".", ",")


def _sayi(n: int) -> str:
    return SAYI_SOZ.get(n, str(n))


def maruziyet_orani(pv: pd.DataFrame | None, tz: str = fn.IST_AD, asgari_gun: int = MARUZIYET_ASGARI_GUN) -> dict | None:
    """Son dönem saatlik uzlaştırma çerçevesinden (sapma = EDM MWh, edt_net TL, kupst TL): günlük Σ|edt_net − kupst| / Σ|edm| → sapma MWh başına net tutar (TL/MWh)
    çeyrekleri. Gün sayısı yetersizse None (uydurulmaz). Senaryo niteliğinde (geçmiş oran geleceğe uygulanır)."""
    if pv is None or pv.empty or "edt_net" not in pv.columns or not ({"sapma", "edm"} & set(pv.columns)):
        return None
    x = pv.copy(); idx = pd.DatetimeIndex(x.index); x.index = idx.tz_localize("UTC").tz_convert(tz) if idx.tz is None else idx.tz_convert(tz)
    sapma_kol = "sapma" if "sapma" in x.columns else "edm"   # dengesizlik.saatlik çıktısı «sapma» (EDM, MWh)
    net = (x["edt_net"].astype(float) - x["kupst"].astype(float).fillna(0.0)) if "kupst" in x.columns else x["edt_net"].astype(float)
    g = pd.DataFrame({"net": net.abs(), "edm": x[sapma_kol].astype(float).abs()}).groupby(x.index.date).sum()
    g = g[g["edm"] > 1e-6]
    if len(g) < asgari_gun:
        return None
    r = g["net"] / g["edm"]
    return {"gecmis_gun": int(len(g)), "oran_tl_mwh": {"p25": round(float(r.quantile(0.25)), 1), "p50": round(float(r.quantile(0.5)), 1), "p75": round(float(r.quantile(0.75)), 1)},
            "nitelik": fn.Nitelik.SENARYO.value, "yontem": "günlük Σ|net uzlaştırma| / Σ|sapma MWh| çeyrekleri (son dönem)"}


def oneriler(g: dict) -> list[dict]:
    """g: hedef (yarin|bugun), gun, risk, program_kaynak, santraller, tahmin_yok, belirsizlik, tazelik, olcum_yas_saat, pencere, gun_ici, fiyat, maruziyet, kapasite_kwp."""
    out: list[dict] = []
    hedef = g.get("hedef", "yarin")
    gun_sozu = "yarınki" if hedef == "yarin" else "bugünkü kalan saatlerdeki"
    risk = g.get("risk") or {}; pk = g.get("program_kaynak") or {}; santraller = g.get("santraller") or []; bel = g.get("belirsizlik") or {}
    taz = g.get("tazelik") or {}; pen = g.get("pencere") or {}; gi = g.get("gun_ici") or {}; fiyat = g.get("fiyat") or {}; mar = g.get("maruziyet")
    risk_et = risk.get("etiket") or "eksik"

    def ekle(kod, tur, etiket, metin, sayfa=None, dayanak=None):
        out.append({"kod": kod, "tur": tur, "tur_ad": TUR_AD[tur], "etiket": etiket, "etiket_ad": ETIKET_AD[etiket], "metin": metin, "sayfa": sayfa, "dayanak": dayanak})

    # 1 — program kaynağı
    if risk_et == "eksik" or (pk.get("yok") and not pk.get("bildirilen") and not pk.get("oneri")):
        ekle("program_yok", "eylem", "eksik", f"{'Yarın' if hedef == 'yarin' else 'Bugün'} için üretim programı bulunamadı; sapma ve risk hesaplanamadı. "
             "Bildirilen KGÜP dosyasını Tahminler sayfasından yükleyin.", "tahminler", {"program_kaynak": pk})
    elif not pk.get("bildirilen") and pk.get("oneri"):
        ekle("program_yok", "bilgi", "tahmini", f"{'Yarın' if hedef == 'yarin' else 'Bugün'} için bildirilen üretim programı yüklü değil; karşılaştırma PVQuant önerisine göre yapıldı. "
             "Bildirdiğiniz KGÜP'ü yüklerseniz sapma gerçek programa göre hesaplanır.", "tahminler", {"program_kaynak": pk})
    elif pk.get("yok"):
        ekle("program_yok", "bilgi", "eksik", f"{pk['yok']} saatte program yok; o saatler sapmaya girmedi.", "tahminler", {"program_kaynak": pk})
    # 2–3 — portföy sapması
    pct = risk.get("beklenen_sapma_pct")
    if pct is not None and risk_et != "eksik":
        yon = "düşük" if pct < 0 else "yüksek"
        if abs(pct) >= SAPMA_BUYUK_PCT:
            ekle("sapma_buyuk", "eylem", risk_et, f"Portföyünüzün {gun_sozu} üretim beklentisi, mevcut üretim programından %{_tr(abs(pct))} {yon}. "
                 "Programı gözden geçirmeniz önerilir; revizyon kararı sizindir.", "tahminler",
                 {"beklenen_sapma_mwh": risk.get("beklenen_sapma_mwh"), "program_mwh": risk.get("program_mwh"), "tahmin_mwh": risk.get("tahmin_mwh"), "saat": risk.get("saat")})
        elif abs(pct) >= SAPMA_ORTA_PCT:
            ekle("sapma_orta", "oneri", risk_et, f"Portföyünüzün {gun_sozu} üretim beklentisi, mevcut üretim programından %{_tr(abs(pct))} {yon}; eğilim sürerse programı gözden geçirin.",
                 "tahminler", {"beklenen_sapma_mwh": risk.get("beklenen_sapma_mwh"), "program_mwh": risk.get("program_mwh")})
    # 4 — santral değişimi
    degisen = [s for s in santraller if s.get("degisim_pct") is not None and abs(s["degisim_pct"]) >= SANTRAL_DEGISIM_PCT]
    if degisen:
        adlar = ", ".join(s["santral"] for s in degisen[:5])
        ekle("santral_degisim", "oneri", risk_et if risk_et != "eksik" else "tahmini",
             f"{_sayi(len(degisen))} santralde üretim beklentisi belirgin şekilde değişti. Programınızı kontrol etmeniz önerilir. ({adlar})", "tahminler",
             {s["santral"]: s["degisim_pct"] for s in degisen})
    # 5 — karşıt sapmalar
    fazla = [s for s in santraller if (s.get("fark_mwh") or 0) > 0 and abs(s.get("degisim_pct") or 0) >= SAPMA_ORTA_PCT]
    eksik = [s for s in santraller if (s.get("fark_mwh") or 0) < 0 and abs(s.get("degisim_pct") or 0) >= SAPMA_ORTA_PCT]
    if fazla and eksik:
        mutlak = sum(abs(s["fark_mwh"]) for s in fazla + eksik); net = abs(sum(s["fark_mwh"] for s in fazla + eksik))
        ekle("ofset", "bilgi", "bilgi", f"{_sayi(len(fazla) + len(eksik))} santralin sapmaları portföy toplamında birbirini kısmen dengeliyor "
             f"(santral sapmaları toplamı {_tr(mutlak)} MWh, portföy net sapması {_tr(net)} MWh). Mali karşılığı DSG üyeliği ve sözleşmeye bağlıdır.", None,
             {"fazla": [s["santral"] for s in fazla], "eksik": [s["santral"] for s in eksik], "netlesen_mwh": round(mutlak - net, 3)})
    # 6 — riskli saatler
    if risk.get("riskli_saat"):
        ilk = risk.get("saatler") or []
        ekle("riskli_saat", "oneri", risk_et, f"{risk['riskli_saat']} saatte program, tahmin aralığının dışında kalıyor"
             + (f" (en büyük fark {_tr(abs(ilk[0]['fark_mwh']))} MWh, {ilk[0]['ts'][11:16]} UTC)." if ilk else "."), "tahminler", {"riskli_saat": risk["riskli_saat"]})
    # 7 — fiyat
    if int(fiyat.get("senaryo_saat") or 0) and not int(fiyat.get("epias_saat") or 0):
        ekle("fiyat_yok", "bilgi", "eksik", "Finansal etki hesabı için güncel piyasa fiyatı bulunamadı.", "kurulus", {"senaryo_saat": fiyat.get("senaryo_saat")})
    elif int(fiyat.get("senaryo_saat") or 0):
        ekle("fiyat_yok", "bilgi", "tahmini", f"{fiyat['senaryo_saat']} saatte güncel piyasa fiyatı yok; finansal etki o saatlerde senaryo fiyatıyla hesaplanır.", "kurulus",
             {"senaryo_saat": fiyat.get("senaryo_saat"), "epias_saat": fiyat.get("epias_saat")})
    # 8 — maruziyet (senaryo)
    sap = risk.get("beklenen_sapma_mwh")
    if mar and sap is not None and abs(sap) > 1e-9:
        q = mar["oran_tl_mwh"]; aralik = {k: fn.bin_tl(abs(sap) * v) for k, v in q.items()}
        ekle("maruziyet", "bilgi", "tahmini", f"Beklenen {_tr(abs(sap))} MWh sapmanın tahmini uzlaştırma etkisi yaklaşık {aralik['p25']:,.0f} … {aralik['p75']:,.0f} TL "
             f"(son {mar['gecmis_gun']} günün sapma başına tutarıyla; senaryo).".replace(",", "."), "finans", {"aralik_tl": aralik, "oran_tl_mwh": q, "gecmis_gun": mar["gecmis_gun"]})
    elif mar is None and sap is not None and abs(sap) > 1e-9:
        ekle("maruziyet", "bilgi", "eksik", "Tahmini uzlaştırma etkisi için son dönem hesabı yetersiz; sapma yalnız enerji (MWh) olarak gösterildi.", "finans", None)
    # 9 — belirsizlik
    bd = bel.get("durum")
    if bd == "yetersiz_veri":
        ekle("belirsizlik", "bilgi", "eksik", "Portföy tahmin aralığı için yeterli ortak geçmiş yok; aralık ihtiyatlı varsayımla verildi, riskli saat sayısı yaklaşıktır.", None, {"durum": bd})
    elif bd == "dogrulanmadi":
        ekle("belirsizlik", "bilgi", "tahmini", "Portföy tahmin aralığı henüz geçmiş gerçekleşmelerle doğrulanmadı; riskli saatleri yaklaşık kabul edin.", None, {"durum": bd})
    # 10 — tazelik
    yas = taz.get("en_eski_yas_saat"); oy = g.get("olcum_yas_saat")
    if (yas is not None and yas > TAZELIK_UYARI_SAAT) or taz.get("farkli_yayin"):
        ekle("tazelik", "oneri", "tahmini", (f"Bazı santrallerin tahmini {_tr(yas, 0)} saatten eski." if yas is not None and yas > TAZELIK_UYARI_SAAT else "Santrallerin tahminleri farklı zamanlarda yayımlanmış.")
             + " Karar vermeden önce güncel tahmini bekleyin ya da Tahminler sayfasından yenileyin.", "tahminler", {"en_eski_yas_saat": yas, "fark_saat": taz.get("fark_saat")})
    if oy is not None and oy > OLCUM_UYARI_SAAT:
        ekle("olcum_tazelik", "bilgi", "eksik", f"Son ölçüm {_tr(oy, 0)} saat önce; bugünkü gerçekleşme bilgisi eksik, bugünkü sapma değerlendirmesi tahmine dayanır.", "veri", {"olcum_yas_saat": oy})
    # 11 — pencereler
    if hedef == "yarin":
        d = pen.get("durum")
        if d == "pencere_acik":
            ekle("pencere", "eylem", risk_et if risk_et != "eksik" else "tahmini", f"Yarının ({pen.get('hedef_gun')}) programı için bildirim penceresi açık; 15:30'a {pen.get('dakika_kaldi')} dakika kaldı. "
                 f"TEİAŞ teyidi {pen.get('teyit_saati', '17:00')[:5]}.", "tahminler", pen)
        elif d == "erken":
            ekle("pencere", "bilgi", "bilgi", f"Yarının programı için bildirim penceresi 14:00'te açılır, 15:30'da kapanır ({pen.get('dakika_kaldi')} dakika kaldı).", "tahminler", pen)
        elif d == "gecikti":
            ekle("pencere", "bilgi", "gecti", f"Yarın ({pen.get('hedef_gun')}) için program bildirim süresi (15:30) geçti; değişiklik yalnız gün içinde, teslimat saatinden "
                 "bir saat önceki kapanıştan sonraki 30 dakika içinde yapılabilir.", "tahminler", pen)
    else:
        if gi.get("acik"):
            ekle("pencere", "eylem", risk_et if risk_et != "eksik" else "tahmini", f"Bir sonraki teslimat saati {gi.get('teslimat', '')[11:16]} için gün içi düzeltme "
                 f"{gi.get('kgup_revizyon_son', '')[11:16]}'a kadar yapılabilir ({gi.get('dakika_kaldi')} dakika).", "tahminler", gi)
        elif gi:
            ekle("pencere", "bilgi", "gecti", f"Bir sonraki teslimat saati {gi.get('teslimat', '')[11:16]} için gün içi düzeltme süresi geçti; sonraki saat için "
                 f"{gi.get('sonraki_revizyon_son', '')[11:16]}'a kadar düzeltme yapılabilir.", "tahminler", gi)
    # 12 — tahmini olmayan santral
    ty = g.get("tahmin_yok") or []
    if ty:
        ekle("tahmin_yok", "eylem", "eksik", f"{_sayi(len(ty))} santralin güncel tahmini yok ({', '.join(ty[:5])}); portföy toplamı bu santraller olmadan kuruldu.", "santralim", {"santraller": ty})
    if not any(o["kod"] in ("sapma_buyuk", "sapma_orta", "santral_degisim", "riskli_saat", "tahmin_yok") for o in out) and risk_et != "eksik":
        ekle("sakin", "bilgi", risk_et, f"Portföyünüzün {gun_sozu} üretim beklentisi programla uyumlu; gözden geçirme gerektiren bir sapma görünmüyor.", None,
             {"beklenen_sapma_pct": pct})
    sira = {"eylem": 0, "oneri": 1, "bilgi": 2}
    out.sort(key=lambda o: sira[o["tur"]])
    return out


def ozet_cumlesi(g: dict, onerilen: list[dict]) -> str:
    """Portföy yöneticisinin birkaç saniyede okuyacağı tek cümle."""
    risk = g.get("risk") or {}; pct = risk.get("beklenen_sapma_pct"); hedef = g.get("hedef", "yarin")
    eylem = [o for o in onerilen if o["tur"] == "eylem"]
    if risk.get("etiket") == "eksik" or pct is None:
        return "Program bulunmadığından portföy sapması değerlendirilemedi."
    cumle = f"{'Yarın' if hedef == 'yarin' else 'Bugün'} portföy beklentisi programdan %{_tr(abs(pct))} {'düşük' if pct < 0 else 'yüksek'}"
    cumle += f"; {len(eylem)} eylem önerisi var." if eylem else "; eylem gerektiren bir durum yok."
    return cumle
