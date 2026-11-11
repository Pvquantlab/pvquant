"""v2.591 (Faz 3 F3-D) — SÖZLEŞMESEL MALİYET DAĞILIMI ve ÜÇ PERSPEKTİF (saf; DB yok; uzlaştırma formülü yok).

Üç perspektif ayrı tutulur, karıştırılmaz:
1. Bağımsız santral: üyenin tek başına EDT'si (dsg_saatlik `edt_tek`) ve KÜPST'ü (santral/UEVÇB bazında; DSG'de netleşmez, dağılıma girmez).
2. DSG içi: grubun netleşen EDM'si → `edt_grup`; eşiği aşan bireysel kısım `edt_bireysel`; Σ bağımsız − DSG içi = netleşme farkı (açıklanır).
3. Sözleşmesel dağılım: grubun EDT'sinin üyelere paylaşımı — anahtar SÖZLEŞMEDEN gelir, mevzuat sabitlemez:
   sapma (|grup payı| MWh), esit (1/n), uretim (üretim MWh), sabit_pay (sözleşme oranları, Σ = 1, bütün üyeleri kapsamalı), ozel (sabit pay ya da
   eşit + yönetim ücreti (dönem, TL) + MWh başına hizmet ücreti). Bireysel EDT üyede kalır; KÜPST ayrı satır.
Etiket: sözleşme `dogrulandi` ve belgeli ise «Sözleşmeye dayalı dağılım», aksi **«Varsayımsal maliyet dağılımı»** (zorunlu). Nitelik: hesaplanan / senaryo.
İşaret: artı = üye lehine (alacak), eksi = aleyhine (borç) — FEM sözleşmesi (`finans.ISARET_KURALI`); dsg_saatlik'in EDT işareti de artı = gelir.
Σ üye payı = grup tutarı (test); ücretler ayrıca gösterilir ve üye toplamına girer, grup toplamına girmez (DSG yöneticisine ödenir)."""
from __future__ import annotations

from pvquant.ext.platform import finans as fn

SURUM = "2026-11-11"
YONTEMLER = ("sapma", "esit", "uretim", "sabit_pay", "ozel")
YONTEM_AD = {"sapma": "sapma payına göre", "esit": "eşit", "uretim": "üretime göre", "sabit_pay": "sözleşmedeki sabit paylarla", "ozel": "sözleşmedeki özel kurallarla"}
ETIKET_SOZLESME = "Sözleşmeye dayalı dağılım"
ETIKET_VARSAYIMSAL = "Varsayımsal maliyet dağılımı"
NOT_VARSAYIMSAL = ("Dağılım anahtarı doğrulanmış bir sözleşme belgesine dayanmıyor; gösterilen paylar varsayımsal bir hesaptır, DSG iç faturası değildir.")
NOT_SOZLESME = "Dağılım, doğrulanmış sözleşme belgesindeki anahtara göredir; tutarlar yine PVQuant'ın yeniden hesabıdır, EPİAŞ ya da DSG faturası değildir."
NOT_KUPST = "KÜPST santral (UEVÇB) başına hesaplanır, DSG içinde netleşmez ve dağılıma girmez; ayrı satırda gösterilir."


def _r(v, n=2):
    return None if v is None else round(float(v), n)


def sozlesme_etiketi(sozlesme: dict | None) -> tuple[str, fn.Nitelik, str]:
    """(etiket, nitelik, not): yalnız dogrulandi + belge → sözleşmeye dayalı / hesaplanan; aksi varsayımsal / senaryo."""
    if sozlesme and sozlesme.get("dogrulama") == "dogrulandi" and sozlesme.get("belge_adi"):
        return ETIKET_SOZLESME, fn.Nitelik.HESAPLANAN, NOT_SOZLESME
    return ETIKET_VARSAYIMSAL, fn.Nitelik.SENARYO, NOT_VARSAYIMSAL


def agirliklar(uyeler: dict[str, dict], yontem: str, parametreler: dict | None = None) -> tuple[dict[str, float], list[str]]:
    """Üye → pay (Σ = 1) ve notlar. uyeler[ad]: {grup_payi_mwh, uretim_mwh, sapma_mwh}. Toplam ağırlık 0 ise eşit pay (not düşülür).
    sabit_pay/ozel: parametreler.paylar bütün üyeleri kapsamalı ve Σ ≈ 1; aksi hata (ValueError) — sessizce eşitlenmez."""
    if yontem not in YONTEMLER:
        raise ValueError("yontem " + "|".join(YONTEMLER))
    adlar = list(uyeler); n = len(adlar); notlar: list[str] = []
    if n == 0:
        return {}, ["üye yok"]
    prm = parametreler or {}
    if yontem in ("sabit_pay", "ozel") and prm.get("paylar"):
        paylar = {str(k): float(v) for k, v in prm["paylar"].items()}
        eksik = [a for a in adlar if a not in paylar]
        if eksik:
            raise ValueError("sözleşme payları şu üyeleri kapsamıyor: " + ", ".join(eksik))
        top = sum(paylar[a] for a in adlar)
        if abs(top - 1.0) > 1e-6:
            raise ValueError("sözleşme paylarının toplamı 1 olmalı")
        return {a: paylar[a] for a in adlar}, notlar
    if yontem == "sabit_pay":
        raise ValueError("sabit pay yöntemi için sözleşme payları gerekli")
    if yontem in ("esit", "ozel"):
        if yontem == "ozel":
            notlar.append("özel kuralda pay tablosu yok; eşit pay varsayıldı")
        return {a: 1.0 / n for a in adlar}, notlar
    kol = "grup_payi_mwh" if yontem == "sapma" else "uretim_mwh"
    w = {a: max(float(uyeler[a].get(kol) or 0.0), 0.0) for a in adlar}
    top = sum(w.values())
    if top <= 1e-12:
        notlar.append(f"{YONTEM_AD[yontem]} ağırlıkların toplamı sıfır; eşit pay uygulandı")
        return {a: 1.0 / n for a in adlar}, notlar
    return {a: w[a] / top for a in adlar}, notlar


def dagit(grup_tutar_tl: float | None, uyeler: dict[str, dict], yontem: str = "sapma", parametreler: dict | None = None, sozlesme: dict | None = None) -> dict:
    """Grubun EDT'sini (artı = lehte) üyelere paylaştırır; bireysel EDT ve KÜPST üyede kalır. uyeler[ad]: {edt_bireysel_tl, kupst_tl, grup_payi_mwh,
    uretim_mwh, sapma_mwh, edt_tek_tl}. parametreler: paylar {ad: oran}, yonetim_ucreti_tl (dönem; paylarla ya da eşit bölünür), ucret_tl_mwh (× üretim).
    Döner: satırlar, toplamlar, etiket, nitelik, kontrol (Σ grup payı = grup tutarı)."""
    etiket, nitelik, not_ = sozlesme_etiketi(sozlesme)
    prm = parametreler or {}
    adlar = list(uyeler)
    if grup_tutar_tl is None or not adlar:
        return {"yontem": yontem, "yontem_ad": YONTEM_AD.get(yontem, yontem), "etiket": etiket, "nitelik": fn.Nitelik.EKSIK.value, "satirlar": [], "toplam": None,
                "notlar": [not_, "Grup tutarı ya da üye yok; dağılım hesaplanamadı."], "kontrol": None}
    try:
        pay, notlar = agirliklar(uyeler, yontem, prm)
    except ValueError as e:
        return {"yontem": yontem, "yontem_ad": YONTEM_AD.get(yontem, yontem), "etiket": etiket, "nitelik": fn.Nitelik.EKSIK.value, "satirlar": [], "toplam": None,
                "notlar": [not_, f"Dağılım hesaplanamadı: {e}."], "kontrol": None, "hata": str(e)}
    yonetim = float(prm.get("yonetim_ucreti_tl") or 0.0); ucret_mwh = float(prm.get("ucret_tl_mwh") or 0.0)
    ucret_pay = pay
    if prm.get("ucret_paylari"):
        try:
            ucret_pay, _ = agirliklar(uyeler, "sabit_pay", {"paylar": prm["ucret_paylari"]})
        except ValueError as e:
            notlar.append(f"ücret payları geçersiz ({e}); dağılım paylarıyla bölündü")
    satirlar = []
    for a in adlar:
        u = uyeler[a]
        grup_payi = float(grup_tutar_tl) * pay[a]
        bireysel = float(u.get("edt_bireysel_tl") or 0.0)
        ucret = -(yonetim * ucret_pay[a] + ucret_mwh * max(float(u.get("uretim_mwh") or 0.0), 0.0))
        kupst = u.get("kupst_tl")
        satirlar.append({"santral": a, "pay_pct": _r(pay[a] * 100, 1), "grup_payi_tl": _r(grup_payi), "edt_bireysel_tl": _r(bireysel), "ucret_tl": _r(ucret),
                         "dsg_ici_tl": _r(grup_payi + bireysel), "toplam_tl": _r(grup_payi + bireysel + ucret),
                         "kupst_tl": _r(-abs(float(kupst))) if kupst is not None else None, "kupst_dahil_degil": True,
                         "edt_tek_tl": _r(u.get("edt_tek_tl")), "netlesme_farki_tl": _r((grup_payi + bireysel) - float(u["edt_tek_tl"])) if u.get("edt_tek_tl") is not None else None,
                         "uretim_mwh": _r(u.get("uretim_mwh"), 3), "grup_payi_mwh": _r(u.get("grup_payi_mwh"), 3)})
    top_grup = sum(s["grup_payi_tl"] for s in satirlar); top_ucret = sum(s["ucret_tl"] for s in satirlar)
    kontrol = abs(top_grup - float(grup_tutar_tl)) < 0.01 * max(1.0, abs(float(grup_tutar_tl)) / 100)
    if not kontrol:
        notlar.append("Σ üye payı grup tutarına eşit çıkmadı (yuvarlama dışı).")
    return {"yontem": yontem, "yontem_ad": YONTEM_AD[yontem], "etiket": etiket, "nitelik": nitelik.value, "satirlar": satirlar,
            "toplam": {"grup_tl": _r(grup_tutar_tl), "grup_payi_tl": _r(top_grup), "edt_bireysel_tl": _r(sum(s["edt_bireysel_tl"] for s in satirlar)),
                       "ucret_tl": _r(top_ucret), "dsg_ici_tl": _r(sum(s["dsg_ici_tl"] for s in satirlar)), "toplam_tl": _r(sum(s["toplam_tl"] for s in satirlar)),
                       "yonetim_ucreti_tl": _r(yonetim), "ucret_tl_mwh": _r(ucret_mwh)},
            "notlar": [not_, NOT_KUPST, *notlar], "kontrol": bool(kontrol), "sozlesme": {k: sozlesme.get(k) for k in ("id", "dogrulama", "belge_adi", "gecerli_bas", "gecerli_bit")} if sozlesme else None,
            "isaret": fn.ISARET_KURALI}


def perspektifler(dsg: dict, dagilim: dict, uyelik_dogrulama: dict[str, str] | None = None, fiyat_senaryo_saat: int = 0) -> dict:
    """Üç perspektifi tek sözlükte, nitelikleriyle. dsg: dsg_hesapla_df çıktısı (uyeler, edt_tek_tl, edt_dsg_tl, edt_grup_tl, edt_bireysel_tl, kupst_uye_tl, esik…).
    DSG içi niteliği: bütün üyelikler `dogrulandi` ve fiyat senaryo saati 0 ise hesaplanan; aksi senaryo (en zayıf kazanır)."""
    uy = dsg.get("uyeler") or {}
    dog = uyelik_dogrulama or {}
    hepsi_dogrulandi = bool(uy) and all(dog.get(a) == "dogrulandi" for a in uy)
    dsg_nitelik = fn.Nitelik.HESAPLANAN if hepsi_dogrulandi and fiyat_senaryo_saat == 0 else fn.Nitelik.SENARYO
    bagimsiz = [{"santral": a, "edt_tek_tl": _r(v.get("edt_tek_tl")), "kupst_tl": _r(-abs(float(v["kupst_tl"]))) if v.get("kupst_tl") is not None else None,
                 "sapma_mwh": _r(v.get("sapma_mwh"), 3), "uyelik_dogrulama": dog.get(a, "beyan")} for a, v in uy.items()]
    top_tek = dsg.get("edt_tek_tl"); top_dsg = dsg.get("edt_dsg_tl")
    fark = None if top_tek is None or top_dsg is None else _r(float(top_dsg) - float(top_tek))
    aciklama = None
    if fark is not None:
        aciklama = ("Üyelerin tek başına dengesizlik tutarlarının toplamı ile DSG içi tutar arasındaki fark, eşik içinde kalan karşıt sapmaların grup içinde "
                    "netleşmesinden gelir; eşiği aşan kısım üyede bireysel kalır. " + ("Fark DSG lehine." if fark > 0 else "Fark DSG aleyhine." if fark < 0 else "Fark yok."))
    return {"bagimsiz": {"nitelik": fn.Nitelik.HESAPLANAN.value if fiyat_senaryo_saat == 0 else fn.Nitelik.SENARYO.value, "satirlar": bagimsiz,
                         "toplam_edt_tl": _r(top_tek), "toplam_kupst_tl": _r(-abs(float(dsg["kupst_uye_tl"]))) if dsg.get("kupst_uye_tl") is not None else None,
                         "aciklama": "Her santralin kendi programı ve ölçümüyle, DSG olmasaydı taşıyacağı dengesizlik tutarı; KÜPST santral bazında."},
            "dsg_ici": {"nitelik": dsg_nitelik.value, "edt_dsg_tl": _r(top_dsg), "edt_grup_tl": _r(dsg.get("edt_grup_tl")), "edt_bireysel_tl": _r(dsg.get("edt_bireysel_tl")),
                        "netlesme_farki_tl": fark, "esik": dsg.get("esik"), "esik_kaynak": dsg.get("esik_kaynak"), "sapma_net_mwh": dsg.get("sapma_net_mwh"), "sapma_ayri_mwh": dsg.get("sapma_ayri_mwh"),
                        "uyelik_hepsi_dogrulandi": hepsi_dogrulandi, "aciklama": aciklama},
            "sozlesmesel": dagilim,
            "ozet": {"bagimsiz_toplam_tl": _r(top_tek), "dsg_ici_tl": _r(top_dsg), "netlesme_farki_tl": fark, "sozlesmesel_toplam_tl": (dagilim.get("toplam") or {}).get("toplam_tl"),
                     "etiket": dagilim.get("etiket"), "nitelik": fn.en_zayif(dsg_nitelik, fn.Nitelik(dagilim["nitelik"])).value if dagilim.get("nitelik") else dsg_nitelik.value},
            "surum": SURUM}
